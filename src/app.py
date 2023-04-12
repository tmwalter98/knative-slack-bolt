from bot_app import app
import json
from aiohttp import web
import logging
import os
from typing import Callable, Optional
from cloudevents.http import from_http

from slack_sdk.socket_mode.aiohttp import SocketModeClient

from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

logging.basicConfig(level=logging.DEBUG)

#
# Web app for hosting the healthcheck endpoint for k8s etc.
#


async def healthcheck(_req: web.Request) -> web.Response:
    """Returns OK if app is active."""
    if socket_mode_client is not None and socket_mode_client.is_connected():
        return web.Response(status=200, text="OK")
    return web.Response(status=503, text="The Socket Mode client is inactive")


async def cloudevent(_req: web.Request) -> web.Response:
    event = from_http(_req.headers, _req.content)
    print(
        f"Found {event['id']} from {event['source']} with type ",
        f"{event['type']} and specversion {event['specversion']}",
    )


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
    web.run_app(app=web_app, port=8080)
