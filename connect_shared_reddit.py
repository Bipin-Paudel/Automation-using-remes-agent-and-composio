import os

from composio import Composio
from composio_openai_agents import OpenAIAgentsProvider
from dotenv import load_dotenv


def main() -> None:
    load_dotenv(dotenv_path=".env")


    shared_user_id = os.getenv("COMPOSIO_SHARED_USER_ID", "").strip()
    if not shared_user_id:
        raise RuntimeError(
            "COMPOSIO_SHARED_USER_ID is missing in .env. "
            "Set it first, for example: COMPOSIO_SHARED_USER_ID=skinpal_reddit_shared"
        )

    composio = Composio(provider=OpenAIAgentsProvider())
    session = composio.create(user_id=shared_user_id, toolkits=["reddit"])
    request = session.authorize("reddit")

    print(f"Shared Composio user: {shared_user_id}")
    print("Open this URL and complete the Reddit connection:")
    print(request.redirect_url)
    print()
    print("Waiting for the Reddit connection to complete...")

    account = request.wait_for_connection(timeout=300)
    print("Connected successfully.")
    print(f"Connected account ID: {account.id}")
    print(f"Status: {account.status}")


if __name__ == "__main__":
    main()
