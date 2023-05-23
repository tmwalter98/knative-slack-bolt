import json
import logging
from typing import TYPE_CHECKING, Any, Awaitable

from aiohttp import web
from cloudevents.http import from_http
from path_dict import PathDict
from slack_bolt import BoltResponse
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

if TYPE_CHECKING:
    from bolt_app import KnativeSlackBolt


async def log_request(
    logger: logging.Logger, body: dict, next: Awaitable[BoltResponse]
) -> BoltResponse:
    """Log the incoming request."""

    logger.debug(json.dumps(body, indent=4, default=str))
    return await next()


async def healthcheck_handler(req: web.Request) -> web.Response:
    """Returns OK if app is ready with the socket mode client connected.

    Args:
        req (web.Request): The incoming request.

    Returns:
        web.Response: The response.
    """
    app: KnativeSlackBolt = req.app["slack_app"]
    client: AsyncSocketModeHandler = app.socket_mode_handler.client
    if client is not None and client.is_connected():
        return web.Response(status=200, text="OK")
    return web.Response(status=503, text="The Socket Mode client is inactive")


async def cloudevent_handler(req: web.Request) -> web.Response:
    """Handle incoming CloudEvents.  This is expecting a Cloud Event produced by the Knative Source for Apache Kafka."""

    def unmarshaller(value: Any) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    # Process request body
    bytestr_data = await req.read()
    event = from_http(req.headers, bytestr_data, data_unmarshaller=unmarshaller)
    event_data = PathDict(json.loads(event.data))
    notification_id = event_data["payload", "after", "id"]

    app: KnativeSlackBolt = req.app["slack_app"]
    status_code = await app.handle_cloudevent_notifications(notification_id)

    return web.Response(
        status=status_code, text=json.dumps(event, indent=4, default=str)
    )
