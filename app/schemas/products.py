from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0)
    quantity: int = Field(gt=0)
    image_url: str = Field(min_length=1, max_length=200)
    category_id: int = Field(gt=0)
    subcategory_id: int = Field(gt=0)
    brand_id: int = Field(gt=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)