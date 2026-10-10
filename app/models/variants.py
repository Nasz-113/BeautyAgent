from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base

if TYPE_CHECKING:
    from app.models.products import Product
    from app.models.filters import Filter
    from app.models.reviews import Review

class Variant(Base):
    __tablename__ = "variant_info"

    variant_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    availability: Mapped[bool] = mapped_column(Boolean, nullable=True, default=None)
    variant_name: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    clean_variant_name: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    display_original_price: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    display_price: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    under_sale: Mapped[bool] = mapped_column(Boolean, nullable=True, default=None)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("product_info.product_id"), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))

    product: Mapped[Product] = relationship(back_populates="variants")
    variant_filters: Mapped[list[VariantFiler]] = relationship(back_populates="variant")
    reviews: Mapped[list[Review]] = relationship(back_populates="variant")

class VariantFiler(Base):
    __tablename__ = "variant_filter_info"

    variant_id: Mapped[int] = mapped_column(Integer, ForeignKey("variant_info.variant_id"), primary_key=True)
    filter_id: Mapped[int] = mapped_column(Integer, ForeignKey("filter_info.filter_id"), primary_key=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))

    variant: Mapped[Variant] = relationship(back_populates="variant_filters")
    filter: Mapped[Filter] = relationship(back_populates="variant_filters")