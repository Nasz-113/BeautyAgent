from __future__ import annotations

from typing import TYPE_CHECKING

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base

if TYPE_CHECKING:
    from app.models.brands import Brand
    from app.models.variants import Variant
    from app.models.reviews import Review    

class Product(Base):
    __tablename__ = "product_info"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(Integer, ForeignKey("brand_info.brand_id"), nullable=True, default=None)
    application: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    product_name: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    clean_product_name: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    description: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    display_original_price: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    display_price: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    additional_benefits: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))

    brand: Mapped[Brand] = relationship(back_populates="products")
    variants: Mapped[list[Variant]] = relationship(back_populates="product")
    reviews: Mapped[list[Review]] = relationship(back_populates="product")