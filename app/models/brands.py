from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base
from datetime import UTC, datetime

if TYPE_CHECKING:
    from app.models.products import Product

class Brand(Base):
    __tablename__ = "brand_info"

    brand_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    brand_name: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    clean_brand_name: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    description: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    total_products: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))

    products: Mapped[list[Product]] = relationship(back_populates="brand")