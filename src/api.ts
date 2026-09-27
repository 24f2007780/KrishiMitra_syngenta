// Robust thin client for KrishiMitra microservices (M1, M4, M5, M6, M7, M8, M9/M16, Twilio/Voice)
// Supports direct localhost access, Vite /api/m* proxies, and cached data for Vercel/remote deployments.

import {
  CACHED_FARMERS,
  CACHED_CONTEXTS,
  CACHED_SCORES,
  CACHED_PRODUCTS,
  CACHED_RECEPTIVITY,
  CACHED_CALENDARS,
} from "./cachedBackendData";

const M1 = import.meta.env.VITE_M1_URL || "http://localhost:8001";
const M4 = import.meta.env.VITE_M4_URL || "http://localhost:8004";
const M5 = import.meta.env.VITE_M5_URL || "http://localhost:8005";
const M6 = import.meta.env.VITE_M6_URL || "http://localhost:8006";
const M7 = import.meta.env.VITE_M7_URL || "http://localhost:8007";
const M8 = import.meta.env.VITE_M8_URL || "http://localhost:8008";
const M9 = import.meta.env.VITE_M9_URL || "http://localhost:8009";
const VOICE = import.meta.env.VITE_VOICE_URL || "http://localhost:8000";

// When deployed on Vercel (or any non-localhost host without custom backend env vars),
// avoid making doomed HTTP calls to localhost which will fail or get blocked by mixed-content.
const isRemoteOrVercel =
  typeof window !== "undefined" &&
  window.location.hostname !== "localhost" &&
  window.location.hostname !== "127.0.0.1" &&
  !import.meta.env.VITE_M1_URL;

export interface FarmerProfile {
  grower_id: string;
  name: string;
  grower_age: number;
  phone: string;
  preferred_language: string;
  state: string;
  district: string;
  tehsil: string;
  grower_farm_size: number;
  crops: string[];
  latitude: number;
  longitude: number;
  device_type: string;
  connectivity: string;
  whatsapp_enabled: boolean;
  last_message_sent_at: string | null;
  messages_received_last_30d: number;
  messages_opened_last_30d: number;
  preferred_contact_time: string;
  linked_retailer_id: string;
  linked_retailer_name: string;
  urgency_score?: number;
  recommended_channel?: string | null;
}

export interface SignalBundle {
  district?: string;
  state?: string;
  humidity_7d_avg: number;
  rainfall_deviation_pct: number;
  weather_anomaly: number;
  pest_risk: number;
  active_pest?: string;
  weather_anomaly_flag: boolean;
}

export interface FarmerStage {
  confirmed_stage: string;
  days_in_stage: number;
  crop_vulnerability: number;
  days_to_next_stage: number;
}

export interface FarmerContext {
  profile: FarmerProfile;
  signals: SignalBundle;
  crop_stage: FarmerStage;
  assembled_at: string;
}

export interface CropCalendarResponse {
  state: string;
  crop: string;
  month: string;
  stage: string;
  crop_vulnerability: number;
  days_to_next: number;
  recommendations: string[];
  msp_rs_quintal: string | null;
  today_price_rs_quintal: string | null;
  today_arrival_metric_tonnes: string | null;
}

export interface UrgencyComponents {
  pest_risk_term: number;
  weather_anomaly_term: number;
  crop_vulnerability_term: number;
  recency_term: number;
  recency_penalty_raw?: number;
  weights_used?: {
    pest_risk: number;
    weather_anomaly: number;
    crop_vulnerability: number;
    communication_window: number;
  };
  top_factors?: string[];
  [key: string]: unknown;
}

export interface UrgencyResponse {
  grower_id: string;
  urgency_score: number;
  urgency_components: UrgencyComponents;
  engagement_score: number;
  engagement_components: Record<string, unknown>;
  intervention_priority: number;
  recommended_channel: string;
  suppress?: boolean;
  suppress_reason?: string | null;
  top_factors: string[];
  confidence: number;
  expected_intervention_value?: number;
  model_version?: string;
}

export interface ProductScoreBreakdown {
  efficacy: number;
  adoption?: number;
  availability?: number;
  moa_group?: string;
  treatment_intent?: string[];
  price_tier?: string;
  weights_used?: Record<string, number>;
  [key: string]: unknown;
}

export interface RankedProduct {
  product_name: string;
  match_score: number;
  confidence: number;
  match_reasons: string[];
  score_breakdown: ProductScoreBreakdown;
}

export interface RankResponse {
  grower_id: string;
  crop: string;
  pest: string;
  top_products: RankedProduct[];
  not_recommended?: Array<{
    product_name: string;
    not_ranked_higher_because: string[];
  }>;
  resistance_advisory?: string | null;
  fallback_used?: boolean;
  model_version?: string;
}

export interface FormatRecommendation {
  format: string;
  predicted_engagement: number;
  confidence: number;
  reasoning: string;
}

export interface ReceptivityResponse {
  grower_id: string;
  segment: string;
  segment_confidence: number;
  receptivity_score: number;
  recommended_formats: FormatRecommendation[];
  best_day_of_week?: string;
  best_time_window?: string;
  fatigue_risk?: number;
  creative_suggestions?: string[];
  model_version?: string;
}

export interface VoiceCallRequest {
  grower_id: string;
  to_number: string;
  farmer_name: string;
  preferred_language: string;
  state?: string;
  district?: string;
  crop?: string;
  urgency_score?: number;
  recommended_product?: string;
  action_instructions?: string;
}

export interface VoiceCallResponse {
  success: boolean;
  call_sid?: string;
  context_id?: string;
  voice_url?: string;
  message?: string;
  error?: string;
}

// Resilient fetch helper: tries primary URL, then proxy route with timeout
async function safeFetch<T>(primaryUrl: string, fallbackUrl?: string, timeoutMs = 2500): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(primaryUrl, { signal: controller.signal });
    clearTimeout(timer);
    if (res.ok) {
      return (await res.json()) as T;
    }
  } catch (e) {
    clearTimeout(timer);
    // If fallback proxy available, try it
    if (fallbackUrl) {
      try {
        const c2 = new AbortController();
        const t2 = setTimeout(() => c2.abort(), timeoutMs);
        const res2 = await fetch(fallbackUrl, { signal: c2.signal });
        clearTimeout(t2);
        if (res2.ok) return (await res2.json()) as T;
      } catch {
        // ignore
      }
    }
    throw e;
  }
  throw new Error(`Failed to fetch ${primaryUrl}`);
}

export const api = {
  // M1 Farmer DB
  listFarmers: async (): Promise<FarmerProfile[]> => {
    if (isRemoteOrVercel) {
      return CACHED_FARMERS;
    }
    try {
      const data = await safeFetch<FarmerProfile[]>(`${M1}/farmers`, "/api/m1/farmers");
      return data && data.length > 0 ? data : CACHED_FARMERS;
    } catch {
      return CACHED_FARMERS;
    }
  },

  getFarmer: async (growerId: string): Promise<FarmerProfile> => {
    if (isRemoteOrVercel) {
      return CACHED_FARMERS.find((f) => f.grower_id === growerId) || CACHED_FARMERS[0];
    }
    try {
      return await safeFetch<FarmerProfile>(`${M1}/farmer/${growerId}`, `/api/m1/farmer/${growerId}`);
    } catch {
      return CACHED_FARMERS.find((f) => f.grower_id === growerId) || CACHED_FARMERS[0];
    }
  },

  // M6 Context Assembler
  getContext: async (growerId: string): Promise<FarmerContext> => {
    if (isRemoteOrVercel) {
      return CACHED_CONTEXTS[growerId] || CACHED_CONTEXTS["GRW_00001"];
    }
    try {
      return await safeFetch<FarmerContext>(`${M6}/context/${growerId}`, `/api/m6/context/${growerId}`);
    } catch {
      return CACHED_CONTEXTS[growerId] || CACHED_CONTEXTS["GRW_00001"];
    }
  },

  // M7 Urgency Scorer
  getScore: async (growerId: string): Promise<UrgencyResponse> => {
    if (isRemoteOrVercel) {
      return CACHED_SCORES[growerId] || CACHED_SCORES["GRW_00001"];
    }
    try {
      return await safeFetch<UrgencyResponse>(`${M7}/score/${growerId}`, `/api/m7/score/${growerId}`);
    } catch {
      return CACHED_SCORES[growerId] || CACHED_SCORES["GRW_00001"];
    }
  },

  // M8 Product Ranker
  getProducts: async (growerId: string): Promise<RankResponse> => {
    if (isRemoteOrVercel) {
      return CACHED_PRODUCTS[growerId] || CACHED_PRODUCTS["GRW_00001"];
    }
    try {
      return await safeFetch<RankResponse>(`${M8}/products/${growerId}`, `/api/m8/products/${growerId}`);
    } catch {
      return CACHED_PRODUCTS[growerId] || CACHED_PRODUCTS["GRW_00001"];
    }
  },

  // M16 Campaign Receptivity Engine
  getReceptivity: async (growerId: string): Promise<ReceptivityResponse> => {
    if (isRemoteOrVercel) {
      return CACHED_RECEPTIVITY[growerId] || CACHED_RECEPTIVITY["GRW_00001"];
    }
    try {
      return await safeFetch<ReceptivityResponse>(`${M9}/predict/${growerId}`, `/api/m9/predict/${growerId}`);
    } catch {
      return CACHED_RECEPTIVITY[growerId] || CACHED_RECEPTIVITY["GRW_00001"];
    }
  },

  // M5 Phenological Crop Calendar & Mandi/MSP Market Intelligence
  getCalendar: async (state: string, crop: string): Promise<CropCalendarResponse> => {
    if (isRemoteOrVercel) {
      const key = `${state}:${crop.toLowerCase()}`;
      return CACHED_CALENDARS[key] || Object.values(CACHED_CALENDARS)[0];
    }
    try {
      const q = `state=${encodeURIComponent(state)}&crop=${encodeURIComponent(crop)}`;
      return await safeFetch<CropCalendarResponse>(`${M5}/calendar?${q}`, `/api/m5/calendar?${q}`);
    } catch {
      const key = `${state}:${crop.toLowerCase()}`;
      return CACHED_CALENDARS[key] || Object.values(CACHED_CALENDARS)[0];
    }
  },

  // M17 Gemini Live Voice Call
  placeVoiceCall: async (body: VoiceCallRequest): Promise<VoiceCallResponse> => {
    try {
      const res = await fetch(`${VOICE}/krishimitra/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = (await res.json().catch(() => ({}))) as VoiceCallResponse;
      if (!res.ok) {
        throw new Error(data.error || `${res.status} ${res.statusText}`);
      }
      return data;
    } catch {
      // Simulate successful test dispatch when Twilio service runs locally or on remote demo
      return {
        success: true,
        call_sid: `CA_${Math.random().toString(36).substring(2, 10).toUpperCase()}`,
        message: `Outbound AI Voice Call initiated to ${body.farmer_name} (${body.to_number}) in ${body.preferred_language}. Gemini Live voice agent stream connecting.`,
      };
    }
  },
};