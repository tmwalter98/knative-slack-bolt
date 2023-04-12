import json
from aiohttp import web
import logging
import os
from typing import Awaitable, Callable, Optional
from cloudevents.http import from_http

from slack_sdk.socket_mode.aiohttp import SocketModeClient

from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

logging.basicConfig(level=logging.DEBUG)

#
# Socket Mode Bolt app
#


# Install the Slack app and get xoxb- token in advance
app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])
socket_mode_client: Optional[SocketModeClient] = None


@app.middleware
async def log_request(logger: logging.Logger, body: dict, next: Callable):
    logger.debug(json.dumps(body, indent=4, default=str))
    return await next()


@app.event("app_mention")
async def event_test(event, say):
    await say(f"Hi there, <@{event['user']}>!")


@app.shortcut("product_search")
async def show_product_updates(
    ack: Callable[[], Awaitable[None]],
    body: dict,
    client: AsyncWebClient,
):
    await ack()
    try:
        await client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "title": {"type": "plain_text", "text": "Product Updates"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Here are the latest product updates:",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Product 1*\nNew feature added!",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Product 2*\nPrice decreased by 10%!",
                        },
                    },
                    {"type": "divider"},
                ],
            },
        )
    except SlackApiError as e:
        print(f"Error opening modal: {e}")
