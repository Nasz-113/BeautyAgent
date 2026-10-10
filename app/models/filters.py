from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from configs.database import Base

if TYPE_CHECKING:
    from app.models.variants import VariantFiler


class Filter(Base):
    __tablename__ = "filter_info"

    filter_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    filter_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("filter_type_info.filter_type_id"), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))

    filter_type: Mapped[FilterType] = relationship(back_populates="filters")
    variant_filters: Mapped[list[VariantFiler]] = relationship(back_populates="filter")

class FilterType(Base):
    __tablename__ = "filter_type_info"

    filter_type_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, default=datetime.now(UTC))

    filters: Mapped[list[Filter]] = relationship(back_populates="filter_type")