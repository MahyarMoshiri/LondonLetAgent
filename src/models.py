# Defines shared data models for the application
from typing import List, Optional
from pydantic import BaseModel

class UserCriteria(BaseModel):
    location: str
    property_type: Optional[str] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    bedrooms_min: Optional[int] = None
    keywords: Optional[List[str]] = [] # Default to empty list
    private_only: bool = False
    exclude_agents: bool = True # Default based on V1, can be set by CLI

