from sqlalchemy import Column, Integer, String, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

Base = declarative_base()

# SQLAlchemy Models
class Farmer(Base):
    __tablename__ = "farmers"

    farmer_id = Column(String, primary_key=True, index=True)
    name = Column(String)
    age = Column(Integer)
    phone = Column(String, unique=True, index=True)
    preferred_language = Column(String) # Tamil / Telugu / Hindi / Marathi / Kannada
    state = Column(String, index=True)
    district = Column(String)
    village = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    acres = Column(Float)
    crops = Column(String) # Comma-separated list of crops
    device_type = Column(String) # feature_phone / android / ios
    connectivity = Column(String) # 2G / 3G / 4G / offline
    whatsapp_enabled = Column(Boolean)
    last_message_sent_at = Column(String, nullable=True) # ISO date string
    messages_received_last_30d = Column(Integer)
    messages_opened_last_30d = Column(Integer)
    preferred_contact_time = Column(String) # morning / afternoon / evening
    linked_retailer_id = Column(String)
    linked_retailer_name = Column(String)
    urgency_score = Column(Float, default=0.0)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String, index=True)
    active_ingredients = Column(String)
    description = Column(String)
    target_crop = Column(String, index=True)
    target_pest = Column(String, index=True)

# Pydantic Schemas (M3 Shared Models)

class FarmerProfile(BaseModel):
    farmer_id: str
    name: str
    age: int
    phone: str
    preferred_language: str
    state: str
    district: str
    village: str
    acres: float
    crops: List[str]
    latitude: float
    longitude: float
    device_type: str
    connectivity: str
    whatsapp_enabled: bool
    last_message_sent_at: Optional[str]
    messages_received_last_30d: int
    messages_opened_last_30d: int
    preferred_contact_time: str
    linked_retailer_id: str
    linked_retailer_name: str

    class Config:
        from_attributes = True

class SignalBundle(BaseModel):
    district: Optional[str] = None
    state: Optional[str] = None
    humidity_7d_avg: float
    rainfall_deviation_pct: float
    temperature_anomaly: float
    pest_risk_level: str         # low / medium / high
    active_pest: Optional[str]   # "fungal" / "aphid" / "stem_borer"
    weather_anomaly_flag: bool

class FarmerStage(BaseModel):
    confirmed_stage: str         # sowing / vegetative / flowering / harvest
    days_in_stage: int
    vulnerability: str           # low / medium / high
    days_to_next_stage: int

class CropStageInfo(BaseModel):
    state: str
    crop: str
    month: str
    stage: str
    vulnerability: str
    days_to_next: int
    recommendations: List[str] = []
    msp_rs_quintal: Optional[str] = None
    today_price_rs_quintal: Optional[str] = None
    today_arrival_metric_tonnes: Optional[str] = None

class FarmerContext(BaseModel):
    profile: FarmerProfile
    signals: SignalBundle
    crop_stage: FarmerStage
    assembled_at: str

class ScoredContext(BaseModel):
    context: FarmerContext
    urgency_score: float         # 0.0 – 1.0
    suppress: bool               # True = do not send (fatigue guard)
    recommended_products: List[str]
    why_now_reason_en: str       # English rationale
    why_now_reason_local: str    # Farmer's language rationale

class GeneratedContent(BaseModel):
    farmer_id: str
    sms_text: str
    whatsapp_text: str
    image_concept: str
    voice_script: str
    language: str

class DeliveryRecord(BaseModel):
    farmer_id: str
    channel: str
    scheduled_at: str
    content_type: str
    message_preview: str
    urgency_score: float
    status: str                  # queued / sent / opened / purchased / ignored

    class Config:
        from_attributes = True

# Product Profile (Used for M2)
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
