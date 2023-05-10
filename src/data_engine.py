from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, create_engine, desc, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import text

from models.shopify_store import (
    ShopifyStoreImage,
    ShopifyStoreProduct,
    ShopifyStoreProductNotification,
    ShopifyStoreVariant,
    ShopifyStoreVariantsChange,
)


class DataEngine:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.session = sessionmaker(bind=self.engine)
        self.view_data_storage = {}

    def set_view_data(self, view_id: str, data: Dict[str, Any]):
        self.view_data_storage[view_id] = data

    def get_view_data(self, view_id: str) -> Dict[str, Any]:
        return self.view_data_storage[view_id]

    def search_products(
        self, search_term: str
    ) -> List[Tuple[ShopifyStoreProduct, ShopifyStoreVariant, ShopifyStoreImage]]:
        with self.session() as session:
            fulltext_search_columns = [
                "shopify_store_products.title",
                "shopify_store_products.handle",
                "shopify_store_products.vendor",
                "shopify_store_products.product_type",
                "array_to_string(shopify_store_products.tags, ' ')",
                "shopify_store_variants.title",
                "shopify_store_variants.sku",
            ]
            fulltext_column_join = " || ' ' || ".join(fulltext_search_columns)

            # Create a join between the tables
            q = (
                session.query(ShopifyStoreProduct, ShopifyStoreVariant, ShopifyStoreImage)
                .select_from(ShopifyStoreProduct)
                .join(ShopifyStoreVariant)
                .filter(
                    text(f"to_tsvector('english', {fulltext_column_join}) @@ plainto_tsquery('english', :search_term)")
                )
            )
            q = q.params(search_term=search_term)
            q = q.join(ShopifyStoreImage).where(
                ShopifyStoreImage.product_id == ShopifyStoreProduct.id,
                ShopifyStoreImage.position == 1,
            )
            return q.all()

    def get_new_products(
        self, item_count: int = 15
    ) -> List[Tuple[ShopifyStoreProduct, ShopifyStoreVariant, ShopifyStoreImage]]:
        with self.session() as session, session.begin():
            q = (
                session.query(ShopifyStoreProduct, ShopifyStoreVariant, ShopifyStoreImage)
                .select_from(ShopifyStoreProduct)
                .join(ShopifyStoreVariant)
                .join(ShopifyStoreImage)
                .where(
                    ShopifyStoreImage.product_id == ShopifyStoreProduct.id,
                    ShopifyStoreImage.position == 1,
                )
                .filter(ShopifyStoreProduct.vendor.in_(["UniFi", "Rove Concepts - New York/New Jersey - CL"]))
                .order_by(ShopifyStoreProduct.published_at.desc())
                .limit(item_count)
            )
        return q.all()

    def track_product(self, product_id: str, track: bool) -> None:
        with self.session() as session:
            session.query(ShopifyStoreProduct).filter(ShopifyStoreProduct.id == product_id).update({"track": track})
            session.commit()

    async def get_notable_changes(self, variant_change: ShopifyStoreVariantsChange) -> Dict[str, Any]:
        """Get the notable changes between the previous and current change."""
        with self.session() as sess:
            subquery = (
                sess.query(
                    ShopifyStoreVariantsChange.changed_at.label("changed_at"),
                )
                .filter(ShopifyStoreVariantsChange.change_id == variant_change.change_id)
                .subquery()
            )

            query = (
                sess.query(ShopifyStoreVariantsChange)
                .filter(
                    and_(
                        ShopifyStoreVariantsChange.id == variant_change.id,
                        ShopifyStoreVariantsChange.changed_at <= subquery.c.changed_at,
                    )
                )
                .order_by(desc(ShopifyStoreVariantsChange.changed_at))
                .limit(2)
            )
            changes = query.all()

            change_set = {}
            notable_change_types = {"price", "available"}
            if len(changes) >= 2:
                # Compare the attribute values between the two records
                prev_change, curr_change = changes[1], changes[0]
                # if getattr(prev_change, 'operation')
                for attr in ShopifyStoreVariantsChange.__table__.columns:
                    if (
                        getattr(prev_change, attr.name) != getattr(curr_change, attr.name)
                        and attr.name in notable_change_types
                    ):
                        change_set.update(
                            {attr.name: (getattr(prev_change, attr.name), getattr(curr_change, attr.name))}
                        )
            return change_set

    async def get_featured_image(self, product_id: int, variant_id: int) -> Optional[str]:
        """Get the featured image for a product."""
        with self.session() as sess:
            image: Optional[ShopifyStoreImage] = (
                sess.query(ShopifyStoreImage)
                .filter(
                    or_(
                        and_(
                            ShopifyStoreImage.product_id == product_id,
                            ShopifyStoreImage.variant_ids.contains([variant_id]),
                        ),
                        and_(
                            ShopifyStoreImage.product_id == product_id,
                            ShopifyStoreImage.variant_ids == "{}",
                        ),
                    ),
                )
                .order_by(
                    ShopifyStoreImage.position.asc(),
                )
                .first()
            )
            return image.src if image else None

    async def get_notification_related_objects(
        self, notification_id: str
    ) -> Tuple[ShopifyStoreProductNotification, ShopifyStoreVariantsChange, ShopifyStoreVariant, ShopifyStoreProduct,]:
        with self.session() as sess:
            q = (
                sess.query(
                    ShopifyStoreProductNotification,
                    ShopifyStoreVariantsChange,
                    ShopifyStoreVariant,
                    ShopifyStoreProduct,
                )
                .join(
                    ShopifyStoreVariant,
                    ShopifyStoreVariant.id == ShopifyStoreVariantsChange.id,
                )
                .join(
                    ShopifyStoreProduct,
                    ShopifyStoreProduct.id == ShopifyStoreVariantsChange.product_id,
                )
                .filter(
                    ShopifyStoreProductNotification.id == notification_id,
                )
            )
            return q.first()

    async def mark_notification_delivered(self, notification_id: str, delivered: bool = True) -> None:
        with self.session() as sess:
            sess.query(ShopifyStoreProductNotification).filter(
                ShopifyStoreProductNotification.id == notification_id,
            ).update({"delivered": delivered})
            sess.commit()
