# data_models/recall.py
# Version 2.0 - Pure Pydantic Schema

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class Recall(BaseModel):
    """
    Pydantic model for validating and structuring recall data.
    Used for API input/output and for validating data from external connectors.
    """

    recall_id: str = Field(..., description="Unique identifier for the recall event")
    product_name: str = Field(..., description="Name of the recalled product")
    date: date = Field(..., description="Date the recall was issued")
    reason: Optional[str] = Field(
        None, description="Description of the hazard or reason for recall"
    )
    url: Optional[str] = Field(None, description="Link to the official recall notice")
    source: Optional[str] = Field(None, description="Originating regulatory agency or data source")

    class Config:
        # Enables population from ORM objects and attribute names
        from_attributes = True
