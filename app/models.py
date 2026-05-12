from sqlalchemy import Column, Integer, String, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional, List

Base = declarative_base()

class Farmer(Base):
    __tablename__ = "farmers"

    farmer_id = Column(String, primary_key=True, index=True)
    name = Column(String)
    age = Column(Integer)
    phone = Column(String, unique=True, index=True)
    preferred_language = Column(String)
    state = Column(String, index=True)
    district = Column(String)
    village = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    acres = Column(Float)
    crops = Column(String) # Comma-separated list of crops
    device_type = Column(String) # feature_phone, android, ios
    connectivity = Column(String) # 2G, 3G, 4G, offline
    whatsapp_enabled = Column(Boolean)
    last_message_sent_at = Column(String) # ISO date string
    messages_received_last_30d = Column(Integer)
    messages_opened_last_30d = Column(Integer)
    preferred_contact_time = Column(String) # morning, afternoon, evening
    linked_retailer_id = Column(String)
    linked_retailer_name = Column(String)
    urgency_score = Column(Float, default=0.0) # For demo moments

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String, index=True)
    active_ingredients = Column(String)
    description = Column(String)
    target_crop = Column(String, index=True)
    target_pest = Column(String, index=True)

# Pydantic Schemas
class FarmerProfile(BaseModel):
    farmer_id: str
    name: str
    age: int
    phone: str
    preferred_language: str
    state: str
    district: str
    village: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    acres: float
    crops: str
    device_type: str
    connectivity: str
    whatsapp_enabled: bool
    last_message_sent_at: str
    messages_received_last_30d: int
    messages_opened_last_30d: int
    preferred_contact_time: str
    linked_retailer_id: str
    linked_retailer_name: str
    urgency_score: float

    class Config:
        from_attributes = True

class ProductProfile(BaseModel):
    id: Optional[int] = None
    name: str
    type: str
    active_ingredients: Optional[str] = None
    description: Optional[str] = None
    target_crop: Optional[str] = None
    target_pest: Optional[str] = None

    class Config:
        from_attributes = True
