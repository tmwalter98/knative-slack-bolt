import logging
import os
from logging import Logger
from typing import Callable

from slack_bolt import Ack, App, BoltResponse, Respond
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.models.blocks import (
    ButtonElement,
    InputBlock,
    MarkdownTextObject,
    Option,
    OptionGroup,
    PlainTextInputElement,
    PlainTextObject,
    SectionBlock,
)
from slack_sdk.models.views import View

from blocks_machine import build_search_results

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from data_engine import DataEngine

data_engine = DataEngine(
    "postgresql://postgres:AHZbSY464pjKjyDc@db.cywqiexxljjfurcgaghs.supabase.co/postgres"
)
app = App(token=os.environ["SLACK_BOT_TOKEN"])


@app.middleware  # or app.use(log_request)
def log_request(
    logger: Logger, body: dict, next: Callable[[], BoltResponse]
) -> BoltResponse:
    logger.debug(body)
    return next()


@app.action("text")
def handle_some_action(ack, body, logger):
    ack()
    logger.info(body)


@app.command("/hello-bolt-python")
def handle_command(
    body: dict, ack: Ack, respond: Respond, client: WebClient, logger: Logger
) -> None:
    ack()

    respond(
        blocks=[
            SectionBlock(
                block_id="b",
                text=MarkdownTextObject(
                    text="You can add a button alongside text in your message. "
                ),
                accessory=ButtonElement(
                    action_id="a",
                    text=PlainTextObject(text="Button"),
                    value="click_me_123",
                ),
            ),
        ]
    )

    res = client.views_open(
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
def track_product(ack: Ack, body: dict, client: WebClient):
    ack()
    product_id = body["actions"][0].get("value")
    logger.info("Tracking product: " + product_id)
    data_engine.track_product(product_id, True)

    results = data_engine.search_products(
        body["view"]["state"]["values"]["search-query"]["search-query"]["value"]
    )
    data_engine.set_view_data(body["view"]["id"], results)

    res = client.views_update(
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
def track_product(ack: Ack, body: dict, client: WebClient):
    ack()
    product_id = body["actions"][0].get("value")
    logger.info("Untracking product: " + product_id)
    data_engine.track_product(product_id, False)

    results = data_engine.search_products(
        body["view"]["state"]["values"]["search-query"]["search-query"]["value"]
    )
    data_engine.set_view_data(body["view"]["id"], results)

    res = client.views_update(
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
def perform_search(ack: Ack, body: dict, client: WebClient):
    ack()
    search_term = body["actions"][0].get("value")
    logger.info(f"Searching for: {search_term}")

    ack()

    results = data_engine.search_products(search_term)
    data_engine.set_view_data(body["view"]["id"], results)
    blocks = build_search_results(results)

    res = client.views_update(
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


@app.options("es_a")
def show_options(ack: Ack) -> None:
    ack(options=[Option(text=PlainTextObject(text="Maru"), value="maru")])


@app.options("mes_a")
def show_multi_options(ack: Ack) -> None:
    ack(
        option_groups=[
            OptionGroup(
                label=PlainTextObject(text="Group 1"),
                options=[
                    Option(text=PlainTextObject(text="Option 1"), value="1-1"),
                    Option(text=PlainTextObject(text="Option 2"), value="1-2"),
                ],
            ),
            OptionGroup(
                label=PlainTextObject(text="Group 2"),
                options=[
                    Option(text=PlainTextObject(text="Option 1"), value="2-1"),
                ],
            ),
        ]
    )


@app.view("view-id")
def view_submission(ack: Ack, body: dict, logger: Logger) -> None:
    ack()
    logger.info(body["view"]["state"]["values"])


@app.shortcut("product_search")
def launch_product_search(ack, shortcut, client):
    ack()
    # Call the views_open method using the built-in WebClient
    client.views_open(
        trigger_id=shortcut["trigger_id"],
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
                )
            ],
        ),
    )


if __name__ == "__main__":
    # Create an app-level token with connections:write scope
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"], logger=logger)
    handler.start()
