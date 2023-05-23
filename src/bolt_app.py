import json
import logging
import os
from logging import Logger
from typing import Callable, Optional

from slack_bolt.async_app import AsyncAck, AsyncApp, AsyncRespond
from slack_sdk.models.blocks import InputBlock, PlainTextInputElement, PlainTextObject
from slack_sdk.models.views import View
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.web.async_client import AsyncWebClient

from blocks_machine import build_most_recently_released, build_search_results
from data_engine import DataEngine

data_engine = DataEngine(os.environ["POSTGRES_URL"])
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


async def process_request(respond, body):
    title = body["text"]
    respond(f"Completed! (task: {title})")


async def open_search(
    body: dict,
    ack: AsyncAck,
    respond: AsyncRespond,
    client: AsyncWebClient,
    logger: Logger,
) -> None:
    await ack()
    res = await client.views_open(
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


@app.action("track-product")
async def track_product(
    ack: AsyncAck, body: dict, client: AsyncWebClient, logger: Logger
):
    await ack()
    product_variant = body["actions"][0].get("value")
    product_id, variant_id = product_variant.split("/")

    logger.info("Tracking product: " + product_id)

    product_id, variant_id = int(product_id), int(variant_id)
    data_engine.track_product(product_id, True)

    results = data_engine.search_products(
        body["view"]["state"]["values"]["search-query"]["search-query"]["value"]
    )
    data_engine.set_view_data(body["view"]["id"], results)

    res = await client.views_update(
        trigger_id=body["trigger_id"],
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"],
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
                *build_search_results(results),
            ],
        ),
    )


@app.action("untrack-product")
async def track_product(
    ack: AsyncAck, body: dict, client: AsyncWebClient, logger: Logger
):
    await ack()
    product_variant = body["actions"][0].get("value")
    product_id, variant_id = product_variant.split("/")

    logger.info("Untracking product: " + product_id)

    product_id, variant_id = int(product_id), int(variant_id)
    data_engine.track_product(product_id, False)

    results = data_engine.search_products(
        body["view"]["state"]["values"]["search-query"]["search-query"]["value"]
    )
    data_engine.set_view_data(body["view"]["id"], results)

    res = await client.views_update(
        trigger_id=body["trigger_id"],
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"],
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
                *build_search_results(results),
            ],
        ),
    )


@app.action("search-query")
async def perform_search(
    ack: AsyncAck, body: dict, client: AsyncWebClient, logger: Logger
):
    await ack()
    search_term = body["actions"][0].get("value")
    logger.info(f"Searching for: {search_term}")

    results = data_engine.search_products(search_term)
    data_engine.set_view_data(body["view"]["id"], results)
    blocks = build_search_results(results)

    await client.views_update(
        trigger_id=body["trigger_id"],
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"],
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


app.action("a")(process_request)

app.shortcut("product_updates")(open_search)
app.shortcut("product_search")(open_search)


async def push_home_view(client, event, logger):
    logger.info("Pushing home view")
    new_items = data_engine.get_new_products()
    blocks = build_most_recently_released(new_items)
    try:
        await client.views_publish(
            user_id=event["user"],
            view=View(
                type="home",
                blocks=blocks,
            ),
        )
    except Exception as e:
        logger.error(print(e))


app.event("app_home_opened")(push_home_view)
