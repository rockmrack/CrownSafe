# data_models/product.py

from pydantic import BaseModel


class Product(BaseModel):
    upc: str | None = None
    name: str
    brand: str | None = None
    category: str | None = None
    country_of_sale: str | None = None
