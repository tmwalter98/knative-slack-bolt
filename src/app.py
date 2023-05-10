import json
import logging
import os

from aiohttp import web
from cloudevents.http import from_http
from slack_sdk.errors import SlackApiError

from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from bot_app import app

logging.basicConfig(level=logging.DEBUG)


async def healthcheck(_req: web.Request) -> web.Response:
    """Returns OK if app is active."""
    if socket_mode_client is not None and socket_mode_client.is_connected():
        return web.Response(status=200, text="OK")
    return web.Response(status=503, text="The Socket Mode client is inactive")


async def cloudevent(_req: web.Request) -> web.Response:
    def unmarshaller(x):
        return str(x)

    bytestr_data = await _req.read()
    event = from_http(
        _req.headers, bytearray(bytestr_data), data_unmarshaller=unmarshaller
    )

    channel_id = "C03K73L2CQL"
    try:
        # Call the chat.postMessage method using the WebClient
        result = await app.client.chat_postMessage(
            channel=channel_id, text=json.dumps(event, indent=4, default=str)
        )
        app.logger.info(result)

    except SlackApiError as e:
        app.logger.error(f"Error posting message: {e}")

    return web.Response(status=200, text=json.dumps(event, indent=4, default=str))


web_app = app.web_app()
web_app.add_routes(
    [
        web.get("/healthz", healthcheck),
        web.post("/cloudevents", cloudevent),
    ]
)

#
# Start the app
#

if __name__ == "__main__":

    async def start_socket_mode(_web_app: web.Application):
        handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        await handler.connect_async()
        global socket_mode_client
        socket_mode_client = handler.client

    async def shutdown_socket_mode(_web_app: web.Application):
        await socket_mode_client.close()

    web_app.on_startup.append(start_socket_mode)
    web_app.on_shutdown.append(shutdown_socket_mode)
    web.run_app(app=web_app, port=int(os.environ.get("PORT", 8080)))
