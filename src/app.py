import logging
import os

from bolt_app import KnativeSlackBolt

logging.basicConfig(level=logging.INFO)


def main():
    app = KnativeSlackBolt(
        slack_bot_token=os.environ["SLACK_BOT_TOKEN"],
        slack_app_token=os.environ["SLACK_APP_TOKEN"],
        postgres_url=os.environ["POSTGRES_URL"],
        channel_id=os.environ["CHANNEL_ID"],
    )
    app.run_app(port=os.environ.get("PORT", 8080))


if __name__ == "__main__":
    main()
