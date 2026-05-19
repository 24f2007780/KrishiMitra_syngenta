from sqlalchemy import Column, Integer, String, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

Base = declarative_base()

# SQLAlchemy Models
class Farmer(Base):
    __tablename__ = "farmers"

    farmer_id = Column(String, primary_key=True, index=True)
    name = Column(String)
    age = Column(Integer)
    phone = Column(String, unique=True, index=True)
    preferred_language = Column(String)
    state = Column(String, index=True)
    district = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    crops = Column(String)
    device_type = Column(String)
    connectivity = Column(String)
    whatsapp_enabled = Column(Boolean)
    last_message_sent_at = Column(String, nullable=True)
    messages_received_last_30d = Column(Integer)
    messages_opened_last_30d = Column(Integer)
    preferred_contact_time = Column(String)
    linked_retailer_id = Column(String)
    linked_retailer_name = Column(String)
    urgency_score = Column(Float, default=0.0)

    # Added from growers.csv
    tehsil = Column(String)
    grower_age = Column(Integer)
    gender = Column(String)
    grower_crop_calendar = Column(String)
    product_scan = Column(Boolean)
    product_name = Column(String)
    product_scan_datetime = Column(String)
    grower_farm_size = Column(Float)
    offline_campaign_attended = Column(Boolean)
    campaign_attendance_date = Column(String)
    recommended_channel = Column(String, nullable=True)

class WhatsAppCampaign(Base):
    __tablename__ = "whatsapp_campaign"
    
    id = Column(String, primary_key=True)
    campaign_product = Column(String)
    campaign_crop = Column(String)
    grower_id = Column(String) # Foreign key theoretically
    message_sent_date = Column(String)
    delivered_status = Column(Boolean)
    opened_status = Column(Boolean)
    clicked_status = Column(Boolean)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String, index=True)
    active_ingredients = Column(String)
    description = Column(String)
    target_crop = Column(String, index=True)
    target_pest = Column(String, index=True)
    
    # Agronomic attributes matching product_catalog.py
    effective_stages = Column(String, default="general")
    treatment_intent = Column(String)
    efficacy_rating = Column(Float, default=0.8)
    price_tier = Column(String, default="mid")
    application_mode = Column(String, default="foliar")
    systemic = Column(Boolean, default=False)
    rain_sensitive_hours = Column(Integer, default=0)
    moa_group = Column(String)
    moa_class = Column(String)
    
    # Portfolio metadata fields
    resistance_management = Column(String)
    epa_number = Column(String)
    logo_url = Column(String)
    product_url = Column(String)
    directions = Column(String)

# Pydantic Schemas (M3 Shared Models)

class FarmerProfile(BaseModel):
    farmer_id: str
    name: str
    grower_age: int
    phone: str
    preferred_language: str
    state: str
    district: str
    tehsil: str
    grower_farm_size: float
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

    # M7 Urgency & Delivery fields
    urgency_score: Optional[float] = 0.0
    recommended_channel: Optional[str] = None

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
    effective_stages: Optional[str] = None
    treatment_intent: Optional[str] = None
    efficacy_rating: Optional[float] = None
    price_tier: Optional[str] = None
    application_mode: Optional[str] = None
    systemic: Optional[bool] = None
    rain_sensitive_hours: Optional[int] = None
    moa_group: Optional[str] = None
    moa_class: Optional[str] = None
    
    # Portfolio metadata fields
    resistance_management: Optional[str] = None
    epa_number: Optional[str] = None
    logo_url: Optional[str] = None
    product_url: Optional[str] = None
    directions: Optional[str] = None

    class Config:
        from_attributes = True

class DeviceType(str, Enum):
    smartphone = "smartphone"
    keypad = "keypad"
    unknown = "unknown"

class ChannelRecommendation(str, Enum):
    whatsapp = "whatsapp"
    voice_call = "voice_call"
    sms = "sms"
    field_visit = "field_visit"
    suppress = "suppress"

class UrgencyResponse(BaseModel):
    grower_id: str
    urgency_score: float = Field(..., description="Agronomic urgency [0.00–1.00]. Rule-based, deterministic.")
    urgency_components: dict = Field(..., description="Breakdown of agronomic urgency factors.")
    engagement_score: float = Field(..., description="ML-predicted engagement likelihood [0.00–1.00].")
    engagement_components: dict = Field(..., description="Factors driving engagement prediction.")
    intervention_priority: float = Field(..., description="Combined outreach intervention priority [0.00–1.00].")
    recommended_channel: ChannelRecommendation = Field(..., description="Best channel for this farmer given urgency + engagement.")
    suppress: bool = Field(..., description="True if fatigue guard fires.")
    suppress_reason: Optional[str] = None
    top_factors: List[str] = Field(..., description="Top 3 human-readable factors driving the decision.")
    confidence: float = Field(..., description="System confidence in this decision [0.0–1.0].")
    expected_intervention_value: float = Field(..., description="Expected ROI of intervention (benefit * probability - cost).")
    model_version: str

# M8 Product Ranker Pydantic Models
class CropType(str, Enum):
    wheat = "wheat"
    mustard = "mustard"
    chickpea = "chickpea"
    potato = "potato"
    barley = "barley"
    lentil = "lentil"
    cumin = "cumin"
    maize = "maize"
    safflower = "safflower"
    rice = "rice"
    cotton = "cotton"

class PestType(str, Enum):
    aphid = "aphid"
    rust = "rust"
    blight = "blight"
    wilt = "wilt"
    mildew = "mildew"
    borer = "borer"
    whitefly = "whitefly"
    fungal = "fungal"
    weeds = "weeds"
    general = "general"

class CropStage(str, Enum):
    sowing = "sowing"
    tillering = "tillering"
    flowering = "flowering"
    pod_formation = "pod_formation"
    harvest = "harvest"
    general = "general"

class RankRequest(BaseModel):
    """Input for product ranking."""
    grower_id: Optional[str] = Field(None, description="Grower ID for personalization")
    crop: CropType
    pest: PestType = PestType.general
    crop_stage: CropStage = CropStage.general
    urgency_score: float = Field(0.5, ge=0.0, le=1.0, description="From M7 urgency engine")
    district: Optional[str] = Field(None, description="For availability + regional preference")
    grower_farm_size: Optional[float] = Field(None, ge=0, description="For affordability matching")
    recently_used_products: Optional[List[str]] = Field(
        None, description="Products applied in last 14 days — for resistance management"
    )
    spray_history: Optional[List[str]] = Field(
        None, description="Full season spray history — for rotation planning"
    )
    days_to_harvest: Optional[int] = Field(None, ge=0, description="Pre-harvest interval check")
    top_k: int = Field(2, ge=1, le=5, description="Number of products to return")

    @field_validator("urgency_score", mode="before")
    @classmethod
    def clamp(cls, v):
        return max(0.0, min(1.0, float(v)))

class ProductRecommendation(BaseModel):
    """A single product recommendation with full reasoning."""
    product_name: str
    match_score: float = Field(..., description="Combined relevance score [0–1]")
    confidence: float = Field(..., description="Recommendation confidence [0–1]")
    match_reasons: List[str] = Field(..., description="Human-readable reasons")
    score_breakdown: dict = Field(..., description="Efficacy/adoption/availability breakdown")

class RejectedProduct(BaseModel):
    """Explains why a product was NOT recommended higher."""
    product_name: str
    not_ranked_higher_because: List[str]

class RankResponse(BaseModel):
    """Full ranking response."""
    grower_id: Optional[str]
    crop: str
    pest: str
    top_products: List[ProductRecommendation]
    not_recommended: Optional[List[RejectedProduct]] = Field(
        None, description="Why certain products were ranked lower (top 3 rejections)"
    )
    resistance_advisory: Optional[str] = Field(
        None, description="MoA rotation advice based on spray history"
    )
    fallback_used: bool = Field(False, description="True if no direct match found")
    model_version: str
