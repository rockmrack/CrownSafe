# data_models/product.py
from pydantic import BaseModel
from typing import Optional

class Product(BaseModel):
    upc: Optional[str] = None
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    country_of_sale: Optional[str] = None
