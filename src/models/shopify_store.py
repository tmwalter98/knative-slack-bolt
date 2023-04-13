# coding: utf-8
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    inspect,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, MONEY, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()
metadata = Base.metadata


class CommonBase(Base):
    __abstract__ = True

    id = Column(BigInteger, primary_key=True)

    def __init__(self, **kwargs):
        allowed_args = self.__mapper__.class_manager  # returns a dict
        kwargs = {k: v for k, v in kwargs.items() if k in allowed_args}
        super().__init__(**kwargs)

    def _asdict(self, prefix: bool = False) -> dict:
        t_name = self.__tablename__ + "_" if prefix else ""
        return {
            t_name + c.key: getattr(self, c.key)
            for c in inspect(self).mapper.column_attrs
        }


class ShopifyStoreBase(CommonBase):
    __abstract__ = True

    id = Column(BigInteger, primary_key=True)


class ShopifyStoreProduct(CommonBase):
    __tablename__ = "shopify_store_products"
    __table_args__ = {"schema": "public"}

    id = Column(
        BigInteger,
        primary_key=True,
        server_default=text(
            "nextval('\"public\".shopify_store_products_id_seq'::regclass)"
        ),
    )
    title = Column(Text)
    handle = Column(Text)
    vendor = Column(Text)
    product_type = Column(Text)
    tags = Column(ARRAY(Text()))
    published_at = Column(DateTime(True), nullable=False)
    created_at = Column(DateTime(True), nullable=False)
    updated_at = Column(DateTime(True), nullable=False)
    track = Column(Boolean, nullable=False, server_default=text("false"))


class ShopifyStoreProductsTracking(CommonBase):
    __tablename__ = "shopify_store_products_tracking"
    __table_args__ = {"schema": "public"}

    product_id = Column(BigInteger, primary_key=True)
    track = Column(Boolean, nullable=False, server_default=text("false"))
    include_variants = Column(
        ARRAY(BigInteger()), server_default=text("'{}'::bigint[]")
    )


class ShopifyStoreImage(CommonBase):
    __tablename__ = "shopify_store_images"
    __table_args__ = {"schema": "public"}

    id = Column(
        BigInteger,
        primary_key=True,
        server_default=text(
            "nextval('\"public\".shopify_store_images_id_seq'::regclass)"
        ),
    )
    position = Column(Integer)
    product_id = Column(
        ForeignKey("public.shopify_store_products.id", ondelete="CASCADE")
    )
    variant_ids = Column(ARRAY(BigInteger()))
    src = Column(Text)
    width = Column(Integer)
    height = Column(Integer)
    created_at = Column(DateTime(True), nullable=False)
    updated_at = Column(DateTime(True), nullable=False)
    retrieved_at = Column(
        DateTime(True),
        nullable=False,
        server_default=text("(now() AT TIME ZONE 'utc'::text)"),
    )

    product = relationship("ShopifyStoreProduct")


class ShopifyStoreVariant(CommonBase):
    __tablename__ = "shopify_store_variants"
    __table_args__ = {"schema": "public"}

    id = Column(
        BigInteger,
        primary_key=True,
        server_default=text(
            "nextval('\"public\".shopify_store_variants_id_seq'::regclass)"
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
    product_id = Column(
        ForeignKey("public.shopify_store_products.id", ondelete="CASCADE")
    )
    created_at = Column(DateTime(True), nullable=False)
    updated_at = Column(DateTime(True), nullable=False)

    product = relationship("ShopifyStoreProduct")


class ShopifyStoreVariantsChange(CommonBase):
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
            "nextval('\"public\".shopify_store_variants_changes_id_seq'::regclass)"
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
    product_id = Column(
        ForeignKey("public.shopify_store_products.id", ondelete="CASCADE")
    )
    created_at = Column(DateTime(True), nullable=False)
    updated_at = Column(DateTime(True), nullable=False)
    changed_at = Column(
        DateTime(True),
        nullable=False,
        server_default=text("(now() AT TIME ZONE 'utc'::text)"),
    )
    variant_changes = Column(
        ARRAY(
            Enum(
                "unavailable",
                "available",
                "price_drop",
                "price_increase",
                "new",
                name="variant_change",
                _create_events=False,
            )
        ),
        server_default=text("'{}'::variant_change[]"),
    )

    product = relationship("ShopifyStoreProduct")


class ShopifyStoreProductNotification(CommonBase):
    __tablename__ = "shopify_store_product_notifications"
    __table_args__ = {"schema": "public"}

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v1()"))
    product_id = Column(
        ForeignKey("public.shopify_store_products.id", ondelete="CASCADE")
    )
    variant_id = Column(
        ForeignKey("public.shopify_store_variants.id", ondelete="CASCADE")
    )
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

    change = relationship("ShopifyStoreVariantsChange", uselist=False)
    product = relationship("ShopifyStoreProduct")
    variant = relationship("ShopifyStoreVariant")
