import datetime as datetime
from typing import Any, Dict, List, Tuple

import humanize
import pytz
from slack_sdk.models.blocks import (
    ActionsBlock,
    Block,
    ButtonElement,
    ContextBlock,
    DividerBlock,
    HeaderBlock,
    ImageElement,
    MarkdownTextObject,
    PlainTextObject,
    SectionBlock,
    TextObject,
)

from models.shopify_store import (
    ShopifyStoreImage,
    ShopifyStoreProduct,
    ShopifyStoreVariant,
)


def cast_timestamp_utc(timestamp: datetime) -> datetime:
    # Check if the timestamp is offset-naive
    if timestamp.tzinfo is None:
        return pytz.UTC.localize(timestamp)
    return timestamp.astimezone(pytz.UTC)


def build_search_results(
    results: List[Tuple[ShopifyStoreProduct, ShopifyStoreVariant, ShopifyStoreImage]]
) -> List[Block]:
    blocks = [
        SectionBlock(text=MarkdownTextObject(text=f"*{len(results)}* results found")),
    ]
    for result in results:
        product: ShopifyStoreProduct = result[0]
        variant: ShopifyStoreVariant = result[1]
        image: ShopifyStoreImage = result[2]

        product_variant = "/".join(
            [
                str(product.id),
                str(variant.id),
            ]
        )

        stock_status_memo = f'{":white_check_mark: *in stock*" if variant.available else ":x: *out of stock*"}'
        last_updated = humanize.naturaldelta(
            cast_timestamp_utc(datetime.datetime.now())
            - cast_timestamp_utc(variant.updated_at)
        )

        blocks.extend(
            [
                DividerBlock(),
                SectionBlock(
                    text=MarkdownTextObject(
                        text=f"*<{product.handle}|{product.title}>*\n{product.vendor}\n{variant.price}"
                    ),
                    accessory=ImageElement(image_url=image.src, alt_text=product.title),
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
                            if product.track
                            else "track-product",
                            text=PlainTextObject(
                                text="Turn off notificaitons"
                                if product.track
                                else "Turn on notifications"
                            ),
                            value=product_variant,
                            style="danger" if product.track else "primary",
                        ),
                        ButtonElement(
                            action_id=product.handle,
                            text=PlainTextObject(text="View online"),
                            url=product.handle,
                        ),
                    ],
                ),
            ]
        )
    return blocks[:75]


def build_most_recently_released(
    results: List[Tuple[ShopifyStoreProduct, ShopifyStoreVariant, ShopifyStoreImage]]
) -> List[Block]:
    blocks = []
    for result in results:
        product: ShopifyStoreProduct = result[0]
        variant: ShopifyStoreVariant = result[1]
        image: ShopifyStoreImage = result[2]

        product_variant = "/".join(
            [
                str(product.id),
                str(variant.id),
            ]
        )

        stock_status_memo = f'{":white_check_mark: *in stock*" if variant.available else ":x: *out of stock*"}'
        released_ago = humanize.naturaldelta(
            cast_timestamp_utc(datetime.datetime.now())
            - cast_timestamp_utc(product.published_at)
        )

        blocks.extend(
            [
                DividerBlock(),
                SectionBlock(
                    text=MarkdownTextObject(
                        text=f"*<{product.handle}|{product.title}>*\n{product.vendor}\n{variant.price}"
                    ),
                    accessory=ImageElement(
                        image_url=image.src,
                        alt_text=product.title,
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
                            if product.track
                            else "track-product",
                            text=PlainTextObject(
                                text="Turn off notificaitons"
                                if product.track
                                else "Turn on notifications"
                            ),
                            value=product_variant,
                            style="danger" if product.track else "primary",
                        ),
                        ButtonElement(
                            action_id=product.handle,
                            text=PlainTextObject(text="View online"),
                            url=product.handle,
                        ),
                    ],
                ),
            ]
        )
    return blocks[:75]


def build_notification_block(
    product: ShopifyStoreProduct,
    variant: ShopifyStoreVariant,
    header: str,
    featured_image: str,
    notable_changes: Dict[str, Any],
) -> List[Block]:
    print(str(notable_changes))
    updated_ago = humanize.naturaldelta(
        cast_timestamp_utc(datetime.datetime.now())
        - cast_timestamp_utc(variant.updated_at)
    )

    stock_status_memo = f'{":white_check_mark: *in stock*" if variant.available else ":x: *out of stock*"}'
    if "available" in notable_changes:
        stock_status_memo = f'{":white_check_mark: *now in stock*" if variant.available else ":x: *now out of stock*"}'

    blocks = list(
        [
            HeaderBlock(text=PlainTextObject(text=header)),
            SectionBlock(
                text=MarkdownTextObject(
                    text=f"*<{product.handle}|{product.title}>*\n{product.vendor}\n{variant.price}"
                ),
                accessory=ImageElement(
                    image_url=featured_image,
                    alt_text=product.title,
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
                        text=f"Updated {updated_ago} ago",
                    ),
                ]
            ),
        ],
    )
    return blocks
