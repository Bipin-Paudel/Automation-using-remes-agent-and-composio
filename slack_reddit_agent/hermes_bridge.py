import asyncio
import json
import re
from dataclasses import dataclass

from .config import HERMES_ENABLED, HERMES_MODEL, HERMES_PROVIDER, HERMES_TIMEOUT_SECONDS
from .formatting import sanitize_agent_message


@dataclass(slots=True)
class HermesRouteDecision:
    """Structured routing result returned by the Hermes-first orchestrator."""

    route: str
    reply: str = ""
    handoff_prompt: str = ""
    reason: str = ""


def clean_hermes_output(output: str) -> str:
    """Strip Hermes CLI chrome and return only the useful assistant text."""
    ansi_pattern = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    cleaned = ansi_pattern.sub("", output or "")
    lines = [line.rstrip() for line in cleaned.splitlines()]

    filtered: list[str] = []
    skip_next_resume_line = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if skip_next_resume_line:
            if stripped.startswith("hermes --resume"):
                continue
            skip_next_resume_line = False

        if stripped.startswith(("╭", "╰", "│")):
            continue
        if stripped.startswith("Resume this session with:"):
            skip_next_resume_line = True
            continue
        if stripped.startswith(("Session:", "Duration:", "Messages:", "session_id:")):
            continue
        filtered.append(stripped)

    return sanitize_agent_message("\n".join(filtered).strip())


def _extract_json_payload(text: str) -> str:
    """Extract a JSON object from raw Hermes output."""
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fenced_match:
        return fenced_match.group(1).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1].strip()

    raise ValueError("Hermes orchestration output did not contain a JSON object.")


def parse_hermes_route_decision(output: str) -> HermesRouteDecision:
    """Parse and validate the structured Hermes orchestration response."""
    payload = json.loads(_extract_json_payload(output))
    raw_route = str(payload.get("route") or "").strip().lower()
    route_aliases = {
        "respond": "respond",
        "reply": "respond",
        "direct": "respond",
        "answer": "respond",
        "reddit": "reddit",
        "composio": "reddit",
        "handoff": "reddit",
        "route_to_reddit": "reddit",
    }
    route = route_aliases.get(raw_route)
    if not route:
        raise ValueError(f"Unsupported Hermes route: {raw_route or 'missing'}")

    reply = sanitize_agent_message(str(payload.get("reply") or "").strip())
    handoff_prompt = sanitize_agent_message(
        str(payload.get("handoff_prompt") or "").strip()
    )
    reason = sanitize_agent_message(str(payload.get("reason") or "").strip())

    if route == "respond" and not reply:
        raise ValueError("Hermes returned route=respond without a reply.")

    if route == "reddit" and not handoff_prompt:
        raise ValueError("Hermes returned route=reddit without a handoff_prompt.")

    return HermesRouteDecision(
        route=route,
        reply=reply,
        handoff_prompt=handoff_prompt,
        reason=reason,
    )


async def run_hermes_task(task: str) -> str:
    """Run Hermes locally in single-query mode and return cleaned output."""
    if not HERMES_ENABLED:
        raise RuntimeError(
            "Hermes integration is disabled. Set HERMES_ENABLED=true to use Hermes routing."
        )

    command = ["uv", "run", "hermes", "chat", "-Q", "--source", "tool"]
    if HERMES_MODEL:
        command.extend(["-m", HERMES_MODEL])
    if HERMES_PROVIDER:
        command.extend(["--provider", HERMES_PROVIDER])
    command.extend(["-q", task])

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=HERMES_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise RuntimeError(
            f"Hermes did not finish within {HERMES_TIMEOUT_SECONDS} seconds."
        )

    stdout_text = stdout.decode("utf-8", errors="replace")
    stderr_text = stderr.decode("utf-8", errors="replace").strip()
    cleaned = clean_hermes_output(stdout_text)

    if process.returncode != 0:
        raise RuntimeError(
            stderr_text or cleaned or f"Hermes exited with status {process.returncode}."
        )

    return cleaned or "No response generated."


async def run_hermes_orchestrator(task: str) -> HermesRouteDecision:
    """Run Hermes as the first-pass Slack orchestrator and parse its decision."""
    return parse_hermes_route_decision(await run_hermes_task(task))
