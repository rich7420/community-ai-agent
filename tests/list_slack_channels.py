from dotenv import load_dotenv
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def main():
    load_dotenv()
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        print("Missing SLACK_BOT_TOKEN")
        return 1
    client = WebClient(token=token)
    try:
        resp = client.conversations_list(limit=200, types="public_channel")
        for ch in resp.get("channels", []):
            print(f"{ch['id']}\t{ch['name']}")
        return 0
    except SlackApiError as e:
        print(f"Slack error: {e.response['error']}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
