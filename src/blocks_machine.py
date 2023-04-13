from typing import Any, Dict, List
import humanize
import datetime as datetime
import pytz

from slack_sdk.models.blocks import (
    ActionsBlock,
    Block,
    ButtonElement,
    ContextBlock,
    DividerBlock,
    ImageElement,
    MarkdownTextObject,
    PlainTextObject,
    SectionBlock,
    TextObject,
)


def cast_timestamp_utc(timestamp: datetime) -> datetime:
    # Check if the timestamp is offset-naive
    if timestamp.tzinfo is None:
        return pytz.UTC.localize(timestamp)
    return timestamp.astimezone(pytz.UTC)


def build_search_results(results: List[Dict[str, Any]]) -> List[Block]:
    blocks = [
        SectionBlock(text=MarkdownTextObject(text=f"*{len(results)}* results found")),
    ]
    for result in results:
        product_variant = "/".join(
            [
                str(result["shopify_store_products_id"]),
                str(result["shopify_store_variants_id"]),
            ]
        )

        stock_status_memo = f'{":white_check_mark: *in stock*" if result["shopify_store_variants_available"] else ":x: *out of stock*"}'
        last_updated = humanize.naturaldelta(
            cast_timestamp_utc(datetime.datetime.now())
            - cast_timestamp_utc(result["shopify_store_variants_updated_at"])
        )

        blocks.extend(
            [
                DividerBlock(),
                SectionBlock(
                    text=MarkdownTextObject(
                        text=f"*<{result['shopify_store_products_handle']}|{result['shopify_store_products_title']}>*\n{result['shopify_store_products_vendor']}\n{result['shopify_store_variants_price']}"
                    ),
                    accessory=ImageElement(
                        image_url=result["shopify_store_images_src"],
                        alt_text=result["shopify_store_products_title"],
                    ),
                ),
                ContextBlock(
                    elements=[
                        TextObject(
                            type="mrkdwn",
                            text=stock_status_memo,
                        ),
                        TextObject(
                            type="mrkdwn",
                            text=f"Updated {last_updated} ago",
                        ),
                    ]
                ),
                ActionsBlock(
                    elements=[
                        ButtonElement(
                            action_id="untrack-product"
                            if result["shopify_store_products_track"]
                            else "track-product",
                            text=PlainTextObject(
                                text="Turn off notificaitons"
                                if result["shopify_store_products_track"]
                                else "Turn on notifications"
                            ),
                            value=product_variant,
                            style="danger"
                            if result["shopify_store_products_track"]
                            else "primary",
                        ),
                        ButtonElement(
                            action_id=result["shopify_store_products_handle"],
                            text=PlainTextObject(text="View online"),
                            url=result["shopify_store_products_handle"],
                        ),
                    ],
                ),
            ]
        )
    return blocks[:75]


def build_most_recently_released(results: List[Dict[str, Any]]) -> List[Block]:
    blocks = []
    for result in results:
        product_variant = "/".join(
            [
                str(result["shopify_store_products_id"]),
                str(result["shopify_store_variants_id"]),
            ]
        )

        stock_status_memo = f'{":white_check_mark: *in stock*" if result["shopify_store_variants_available"] else ":x: *out of stock*"}'
        released_ago = humanize.naturaldelta(
            cast_timestamp_utc(datetime.datetime.now())
            - cast_timestamp_utc(result["shopify_store_products_published_at"])
        )

        blocks.extend(
            [
                DividerBlock(),
                SectionBlock(
                    text=MarkdownTextObject(
                        text=f"*<{result['shopify_store_products_handle']}|{result['shopify_store_products_title']}>*\n{result['shopify_store_products_vendor']}\n{result['shopify_store_variants_price']}"
                    ),
                    accessory=ImageElement(
                        image_url=result["shopify_store_images_src"],
                        alt_text=result["shopify_store_products_title"],
                    ),
                ),
                ContextBlock(
                    elements=[
                        TextObject(
                            type="mrkdwn",
                            text=stock_status_memo,
                        ),
                        TextObject(
                            type="mrkdwn",
                            text=f"Released {released_ago} ago",
                        ),
                    ]
                ),
                ActionsBlock(
                    elements=[
                        ButtonElement(
                            action_id="untrack-product"
                            if result["shopify_store_products_track"]
                            else "track-product",
                            text=PlainTextObject(
                                text="Turn off notificaitons"
                                if result["shopify_store_products_track"]
                                else "Turn on notifications"
                            ),
                            value=product_variant,
                            style="danger"
                            if result["shopify_store_products_track"]
                            else "primary",
                        ),
                        ButtonElement(
                            action_id=result["shopify_store_products_handle"],
                            text=PlainTextObject(text="View online"),
                            url=result["shopify_store_products_handle"],
                        ),
                    ],
                ),
            ]
        )
    return blocks[:75]
