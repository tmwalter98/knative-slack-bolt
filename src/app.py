import json
import logging
import os

from aiohttp import web
from cloudevents.http import from_http
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.errors import SlackApiError

from blocks_machine import build_notification_block
from bot_app import app
from data_engine import DataEngine

logging.basicConfig(level=logging.INFO)

data_engine = DataEngine(os.environ["POSTGRES_URL"])


async def healthcheck(_req: web.Request) -> web.Response:
    """Returns OK if app is active."""
    if socket_mode_client is not None and socket_mode_client.is_connected():
        return web.Response(status=200, text="OK")
    return web.Response(status=503, text="The Socket Mode client is inactive")


async def cloudevent(_req: web.Request) -> web.Response:
    def unmarshaller(v):
        if isinstance(v, bytes):
            return v.decode("utf-8")

    bytestr_data = await _req.read()
    # event = from_http(_req.headers, bytearray(bytestr_data), data_unmarshaller=unmarshaller)
    event = from_http(_req.headers, bytestr_data, data_unmarshaller=unmarshaller)
    event_data = json.loads(event.data)

    channel_id = "C03K73L2CQL"
    notification_id = event_data["payload"]["after"]["id"]
    try:
        app.logger.info(f"Received notification ID: {notification_id}")
        (
            variant_change,
            variant,
            product,
        ) = await data_engine.get_notification_related_objects(notification_id)

        featured_image = (
            variant.featured_image.get("src", False)
            if variant.featured_image and variant.featured_image.get("src", False)
            else await data_engine.get_featured_image(product.id, variant.id)
        )

        notable_changes = await data_engine.get_notable_changes(variant_change)
        app.logger.error(
            f"Change set: {' '.join([f'{k}: {v}' for k, v in notable_changes.items()])}"
        )

        message_title_components = [product.title]
        message_title_components.append(
            variant.title if variant.title != "Default Title" else None
        )

        message_title_updates = []
        if "available" in notable_changes:
            availability = "available" if variant.available else "unavailable"
            message_title_updates.append(f"now {availability}!")
        if "price" in notable_changes:
            d_price = (
                "drop"
                if notable_changes["price"][0] > notable_changes["price"][1]
                else "increase"
            )
            message_title_updates.append(f"price {d_price}!")
        message_title_components.append(
            " with ".join(message_title_updates) if len(message_title_updates) else None
        )
        message_title = " ".join(list(filter(None.__ne__, message_title_components)))

        # Call the chat.postMessage method using the WebClient
        result = await app.client.chat_postMessage(
            channel=channel_id,
            text=message_title,
            blocks=build_notification_block(
                product, variant, message_title, featured_image, notable_changes
            ),
        )

        await data_engine.mark_notification_delivered(
            notification_id, result.status_code == 200
        )

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
