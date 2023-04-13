from typing import Any, Dict, List

from slack_sdk.models.views import View
from sqlalchemy import and_, cast, create_engine, select
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import text

from models.shopify_store import (
    ShopifyStoreImage,
    ShopifyStoreProduct,
    ShopifyStoreVariant,
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

    def search_products(self, search_term: str) -> List[Dict[str, Any]]:
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
                session.query(
                    ShopifyStoreProduct, ShopifyStoreVariant, ShopifyStoreImage
                )
                .select_from(ShopifyStoreProduct)
                .join(ShopifyStoreVariant)
                .filter(
                    text(
                        f"to_tsvector('english', {fulltext_column_join}) @@ plainto_tsquery('english', :search_term)"
                    )
                )
            )
            q = q.params(search_term=search_term)
            q = q.join(ShopifyStoreImage).where(
                ShopifyStoreImage.product_id == ShopifyStoreProduct.id,
                ShopifyStoreImage.position == 1,
            )

            results = []
            for row in q.all():
                row_dict = {}
                for table in [o._asdict(prefix=True) for o in row]:
                    row_dict.update(table)
                results.append(row_dict)
            return results

    def get_new_products(self, item_count: int = 15) -> List[Dict[str, Any]]:
        results = []
        with self.session() as session, session.begin():
            q = (
                session.query(
                    ShopifyStoreProduct, ShopifyStoreVariant, ShopifyStoreImage
                )
                .select_from(ShopifyStoreProduct)
                .join(ShopifyStoreVariant)
                .join(ShopifyStoreImage)
                .where(
                    ShopifyStoreImage.product_id == ShopifyStoreProduct.id,
                    ShopifyStoreImage.position == 1,
                )
                .filter(
                    ShopifyStoreProduct.vendor.in_(
                        ["UniFi", "Rove Concepts - New York/New Jersey - CL"]
                    )
                )
                .order_by(ShopifyStoreProduct.published_at.desc())
                .limit(item_count)
            )

            for row in q.all():
                row_dict = {}
                for table in [o._asdict(prefix=True) for o in row]:
                    row_dict.update(table)
                results.append(row_dict)
        return results

    def track_product(self, product_id: str, track: bool) -> None:
        with self.session() as session:
            session.query(ShopifyStoreProduct).filter(
                ShopifyStoreProduct.id == product_id
            ).update({"track": track})
            session.commit()
