from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, StrictBool # validator, Field, model_validator
# import re

class BrandInfo(BaseModel):
    """From the json file of each brand, extracts and validates four fields.
    Output::
        {
            'brand_id': int,
            'brand_name': str,
            'clean_brand_name': str,
            'products': list[BrandProductsIds(str)],
            'total_products': int,
            'description': str
        }

    - If the field has no argument --> returns None
    - `Field()` function is for renaming --> new_name: any = Field(alias='oldName')
    """
    brand_id: int | None
    products: List[str] | None
    total_products: int | None
    description: str | None
    clean_brand_name: str | None
    brand_name: str | None


# Raw JSON product page structure (ProductInfo input):
# ├── productDetails
# │   └── productId, displayName, brand (id, name), lovesCount, rating, reviews
# ├── currentSku
# │   └── variationType|Value|Desc, ingredientDesc, listPrice, valuePrice, salePrice,
# │       isLimitedEdition, isNew, isOnlineOnly, isOutOfStock, isSephoraExclusive, highlights
# ├── parentCategory
# │   └── parentCategory 2
# │       └── parentCategory 3
# ├── onSaleChildSkus
# │   └── listPrice, salePrice
# └── regularChildSkus
#     └── listPrice, salePrice

# class IngredientPreference(BaseModel):
#     id: int | None
#     ingredient: str | None

# class SkinType(BaseModel):
#     id: int | None
#     type: str | None

# class Coverage(BaseModel):
#     id: int | None
#     type: str | None

# class Benefits(BaseModel):
#     id: int | None
#     benefit: str | None

# class Formulation(BaseModel):
#     id: int | None
#     type: str | None

# class Finish(BaseModel):
#     id: int | None
#     type: str | None

class FilterTypeInfo(BaseModel):
    filter_type_id: int | None
    value: str | None

class FilterInfo(BaseModel):
    filter_id: int | None
    value: str | None
    filter_type_id: int | None

class VariantFilter(BaseModel):
    variant_id: int | None
    filter_id: int | None

class VariantInfo(BaseModel):
    variant_id: int | None
    availability: StrictBool
    variant_name: str | None
    clean_variant_name: str | None
    display_original_price: str | None
    display_price: str | None
    under_sale: StrictBool
    product_id: int | None
    # NEED CONTINUATION

class ProductInfo(BaseModel):
    product_id: int | None
    brand_id: int | None
    application: str | None
    product_name: str | None
    clean_product_name: str | None
    description: str | None
    display_original_price: str | None
    display_price: str | None
    additional_benefits: str | None 