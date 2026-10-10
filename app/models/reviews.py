from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base

if TYPE_CHECKING:
    from app.models.products import Product
    from app.models.variants import Variant

class Review(Base):
    __tablename__ = "reviews_info"

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    submission_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("product_info.product_id"), nullable=True, default=None)
    variant_id: Mapped[int] = mapped_column(Integer, ForeignKey("variant_info.variant_id"), nullable=True, default=None)
    reviewed_from: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    rating: Mapped[int] = mapped_column(Integer, nullable=True, default=None)    
    title: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    review_text: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    user_nickname: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))

    product: Mapped[Product] = relationship(back_populates="reviews")
    variant: Mapped[Variant] = relationship(back_populates="reviews")