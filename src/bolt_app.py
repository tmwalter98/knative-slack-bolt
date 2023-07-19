from logging import Logger
from typing import Optional

from aiohttp import web
from path_dict import PathDict
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncAck, AsyncApp
from slack_sdk.errors import SlackApiError
from slack_sdk.models.blocks import InputBlock, PlainTextInputElement, PlainTextObject
from slack_sdk.models.views import View
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.web.async_client import AsyncSlackResponse, AsyncWebClient

from blocks_machine import (
    build_most_recently_released,
    build_notification_block,
    build_search_results,
)
from data_engine import DataEngine
from utilities.middleware import cloudevent_handler, healthcheck_handler, log_request

socket_mode_client: Optional[SocketModeClient] = None


class KnativeSlackBolt(AsyncApp):
    def __init__(
        self,
        slack_bot_token: str,
        slack_app_token: str,
        postgres_url: str,
        channel_id: str,
        **kwargs,
    ):
        self.slack_bot_token = slack_bot_token
        self.slack_app_token = slack_app_token
        self.channel_id = channel_id

        super().__init__(token=self.slack_bot_token, **kwargs)

        self.data_engine = DataEngine(postgres_url)
        self.app = None
        self.socket_mode_handler: AsyncSocketModeHandler = None

    def register_handlers(self):
        """Register all of the handlers for the app."""
        self.middleware(log_request)

        self.shortcut("product-search")(self.open_search)
        self.command("/product-search")(self.open_search)

        self.action("track-product")((self.perform_search))
        self.action("untrack-product")(self.perform_search)
        self.action("search-query")(self.perform_search)

        self.event("app_home_opened")(self.push_home_view)

    def run_app(self, port: int = 8080):
        """
        Runs the application on the specified port.

        Args:
            port (int, optional): The port number to run the application on. Defaults to 8080.

        Returns:
            None

        Raises:
            N/A
        """
        self.register_handlers()
        self.app: web.Application = self.web_app()
        self.app["slack_app"] = self

        self.app.add_routes(
            [
                web.get("/healthz", healthcheck_handler),
                web.post("/cloudevents", cloudevent_handler),
            ]
        )

        async def start_socket_mode(web_app: web.Application):
            self.socket_mode_handler = AsyncSocketModeHandler(
                self, self.slack_app_token
            )
            await self.socket_mode_handler.connect_async()
            global socket_mode_client
            socket_mode_client = self.socket_mode_handler.client

        async def shutdown_socket_mode(web_app: web.Application):
            await self.socket_mode_handler.client.close()

        self.app.on_startup.append(start_socket_mode)
        self.app.on_shutdown.append(shutdown_socket_mode)
        web.run_app(app=self.app, port=port)

    async def open_search(
        self,
        body: dict,
        ack: AsyncAck,
        client: AsyncWebClient,
        logger: Logger,
    ) -> None:
        """Open the product search modal.

        Args:
            body (dict): The body of the request.
            ack (AsyncAck): The ack function.
            client (AsyncWebClient): The Slack client.
            logger (Logger): The logger.
        """
        await ack()
        res: AsyncSlackResponse = await client.views_open(
            trigger_id=body["trigger_id"],
            view=View(
                type="modal",
                callback_id="view-id",
                title=PlainTextObject(text="Inventory Search"),
                submit=PlainTextObject(text="Done"),
                blocks=[
                    InputBlock(
                        element=PlainTextInputElement(action_id="search-query"),
                        label=PlainTextObject(text="Search items"),
                        dispatch_action=True,
                        others={"hint": "Hint"},
                        block_id="search-query",
                        action_id="search-query",
                    )
                ],
            ),
        )
        logger.debug("views.open: %s", res.data)

    async def perform_search(
        self, ack: AsyncAck, body: dict, client: AsyncWebClient, logger: Logger
    ):
        """Search for products and update the view with the results

        Args:
            ack (AsyncAck): The ack function.
            body (dict): The body of the request.
            client (AsyncWebClient): The Slack client.
        """
        await ack()

        # Process request body
        body_dict = PathDict(body)
        action_id = body_dict["actions", 0, "action_id"]
        action_value = body_dict["actions", 0, "value"]

        if action_id in ["track-product", "untrack-product"]:
            product_id, variant_id = map(int, action_value.split("/"))
            track = action_id == "track-product"
            self.data_engine.track_product(product_id, track)
            logger.info(body_dict["actions", 0, "action_id"] + ": " + str(product_id))
        elif action_id == "search-query":
            logger.info(f"Searching for: {action_value}")

        search_query = body_dict[
            "view", "state", "values", "search-query", "search-query", "value"
        ]

        results = self.data_engine.search_products(search_query)
        self.data_engine.set_view_data(body_dict["view", "id"], results)
        blocks = build_search_results(results)

        await client.views_update(
            trigger_id=body_dict["trigger_id"],
            view_id=body_dict["view", "id"],
            # String that represents view state to protect against race conditions
            hash=body_dict["view", "hash"],
            view=View(
                type="modal",
                callback_id="view-id",
                title=PlainTextObject(text="Product Search"),
                blocks=[
                    InputBlock(
                        element=PlainTextInputElement(action_id="search-query"),
                        label=PlainTextObject(text="Search"),
                        dispatch_action=True,
                        others={"hint": "Hint"},
                        block_id="search-query",
                        action_id="search-query",
                    ),
                    *blocks,
                ],
            ),
        )

    async def push_home_view(self, event: dict, client: AsyncWebClient, logger: Logger):
        """Push the updated home view to the user.

        Args:
            event (dict): The event that triggered the home view to be opened.
            client (AsyncWebClient): The Slack client.
            logger (Logger): The logger.
        """

        logger.info("Pushing home view")
        new_items = self.data_engine.get_new_products()
        blocks = build_most_recently_released(new_items)
        try:
            await client.views_publish(
                user_id=event["user"],
                view=View(
                    type="home",
                    blocks=blocks,
                ),
            )
        except Exception as exc:
            raise exc

    async def handle_cloudevent_notifications(self, notification_id: str):
        try:
            self.logger.info(f"Received notification ID: {notification_id}")

            notification_related_objects = (
                await self.data_engine.get_notification_related_objects(notification_id)
            )
            variant_change, variant, product = notification_related_objects

            featured_image = (
                variant.featured_image.get("src", False)
                if variant.featured_image and variant.featured_image.get("src", False)
                else await self.data_engine.get_featured_image(product.id, variant.id)
            )

            notable_changes = await self.data_engine.get_notable_changes(variant_change)
            self.logger.error(
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
                " with ".join(message_title_updates) if message_title_updates else None
            )
            message_title = " ".join(
                list(filter(None.__ne__, message_title_components))
            )

            # Call the chat.postMessage method using the WebClient
            result = await self.client.chat_postMessage(
                channel=self.channel_id,
                text=message_title,
                blocks=build_notification_block(
                    product, variant, message_title, featured_image, notable_changes
                ),
            )

            await self.data_engine.mark_notification_delivered(
                notification_id, result.status_code == 200
            )

        except SlackApiError as exc:
            raise exc
        return result.status_code