from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, MONEY, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()
metadata = Base.metadata


class UtilsBase(Base):
    __abstract__ = True

    def __init__(self, **kwargs):
        allowed_args = self.__mapper__.class_manager  # returns a dict
        kwargs = {k: v for k, v in kwargs.items() if k in allowed_args}
        super().__init__(**kwargs)

    def _as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class ShopifyStoreBase(UtilsBase):
    __abstract__ = True

    id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime(True), nullable=False)
    updated_at = Column(DateTime(True), nullable=False)


class ShopifyStoreProduct(ShopifyStoreBase):
    __tablename__ = "shopify_store_products"

    title = Column(Text)
    handle = Column(Text)
    vendor = Column(Text)
    product_type = Column(Text)
    tags = Column(ARRAY(Text()))
    published_at = Column(DateTime(True), nullable=False)

    track = Column(Boolean, nullable=False, server_default=text("false"))


class ShopifyStoreImage(ShopifyStoreBase):
    __tablename__ = "shopify_store_images"

    position = Column(Integer)
    product_id = Column(ForeignKey("shopify_store_products.id", ondelete="CASCADE"))
    variant_ids = Column(ARRAY(BigInteger()))
    src = Column(Text)
    width = Column(Integer)
    height = Column(Integer)

    product = relationship("ShopifyStoreProduct")


class ShopifyStoreVariant(ShopifyStoreBase):
    __tablename__ = "shopify_store_variants"

    title = Column(Text)
    option1 = Column(Text)
    option2 = Column(Text)
    option3 = Column(Text)
    sku = Column(Text)
    requires_shipping = Column(Boolean)
    taxable = Column(Boolean)
    featured_image = Column(JSONB)
    available = Column(Boolean)
    price = Column(MONEY)
    grams = Column(Integer)
    compare_at_price = Column(MONEY)
    position = Column(Integer)
    product_id = Column(ForeignKey("shopify_store_products.id", ondelete="CASCADE"))

    product = relationship("ShopifyStoreProduct")


class ShopifyStoreVariantsChange(ShopifyStoreBase):
    __tablename__ = "shopify_store_variants_changes"
    __table_args__ = {"schema": "public"}

    change_id = Column(
        UUID, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    operation = Column(Text)
    id = Column(
        BigInteger,
        nullable=False,
        server_default=text(
            "nextval('shopify_store_variants_changes_id_seq'::regclass)"
        ),
    )
    title = Column(Text)
    option1 = Column(Text)
    option2 = Column(Text)
    option3 = Column(Text)
    sku = Column(Text)
    requires_shipping = Column(Boolean)
    taxable = Column(Boolean)
    featured_image = Column(JSONB(astext_type=Text()))
    available = Column(Boolean)
    price = Column(MONEY)
    grams = Column(Integer)
    compare_at_price = Column(MONEY)
    position = Column(Integer)
    product_id = Column(ForeignKey("shopify_store_products.id", ondelete="CASCADE"))
    changed_at = Column(
        DateTime(True),
        nullable=False,
        server_default=text("(now() AT TIME ZONE 'utc'::text)"),
    )

    product = relationship(
        "ShopifyStoreProduct", backref="shopify_store_variants_changes"
    )


class ShopifyStoreProductNotification(UtilsBase):
    __tablename__ = "shopify_store_product_notifications"
    __table_args__ = {"schema": "public"}

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v1()"))
    product_id = Column(ForeignKey("shopify_store_products.id", ondelete="CASCADE"))
    variant_id = Column(ForeignKey("shopify_store_variants.id", ondelete="CASCADE"))
    notification_at = Column(
        DateTime(True),
        nullable=False,
        server_default=text("(now() AT TIME ZONE 'utc'::text)"),
    )
    delivered = Column(Boolean, nullable=False, server_default=text("false"))
    change_id = Column(
        ForeignKey("public.shopify_store_variants_changes.change_id"),
        nullable=False,
        unique=True,
    )

    change = relationship("ShopifyStoreVariantsChange")
    product = relationship("ShopifyStoreProduct")
    variant = relationship("ShopifyStoreVariant")
