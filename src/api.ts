// Thin client for the KrishiMitra microservices (see run_all.sh for ports).
// Each URL can be overridden with a Vite env var, e.g. VITE_M1_URL, for deployments
// where the services don't run on localhost.

const M1 = import.meta.env.VITE_M1_URL || "http://localhost:8001"; // Farmer DB
const M6 = import.meta.env.VITE_M6_URL || "http://localhost:8006"; // Context assembler
const M7 = import.meta.env.VITE_M7_URL || "http://localhost:8007"; // Urgency scorer
const M8 = import.meta.env.VITE_M8_URL || "http://localhost:8008"; // Product ranker
const M9 = import.meta.env.VITE_M9_URL || "http://localhost:8009"; // Campaign receptivity
const VOICE = import.meta.env.VITE_VOICE_URL || "http://localhost:8000"; // twilio-voice-agent (AI voice calls)

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

export interface UrgencyResponse {
  grower_id: string;
  urgency_score: number;
  urgency_components: Record<string, unknown>;
  engagement_score: number;
  engagement_components: Record<string, unknown>;
  intervention_priority: number;
  recommended_channel: string;
  suppress: boolean;
  suppress_reason: string | null;
  top_factors: string[];
  confidence: number;
  expected_intervention_value: number;
  model_version: string;
}

export interface ProductRecommendation {
  product_name: string;
  match_score: number;
  confidence: number;
  match_reasons: string[];
  score_breakdown: { price_tier?: string; [key: string]: unknown };
}

export interface RankResponse {
  grower_id?: string;
  crop: string;
  pest: string;
  top_products: ProductRecommendation[];
  fallback_used: boolean;
  model_version: string;
}

export interface FormatRecommendation {
  format: string;
  predicted_engagement: number;
  confidence: number;
  reasoning: string;
}

export interface ReceptivityResponse {
  grower_id?: string;
  segment: string;
  segment_confidence: number;
  receptivity_score: number;
  recommended_formats: FormatRecommendation[];
  best_day_of_week: string | null;
  best_time_window: string | null;
  fatigue_risk: number;
  creative_suggestions: string[];
  model_version: string;
}

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`${url} → ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export interface VoiceCallRequest {
  to_number: string;
  farmer_id?: string;
  farmer_name: string;
  preferred_language: string;
  state: string;
  district: string;
  village?: string;
  crops: string[];
  crop_stage: string;
  pest_risk_level: string;
  active_pest?: string;
  why_now: string;
  recommended_product: string;
  retailer_name: string;
  urgency_score?: number;
  intro_script?: string;
}

export interface VoiceCallResponse {
  success: boolean;
  call_sid?: string;
  context_id?: string;
  voice_url?: string;
  message?: string;
  error?: string;
}

export const api = {
  listFarmers: () => getJSON<FarmerProfile[]>(`${M1}/farmers`),
  getContext: (growerId: string) => getJSON<FarmerContext>(`${M6}/context/${growerId}`),
  getScore: (growerId: string) => getJSON<UrgencyResponse>(`${M7}/score/${growerId}`),
  getProducts: (growerId: string) => getJSON<RankResponse>(`${M8}/products/${growerId}`),
  getReceptivity: (growerId: string) => getJSON<ReceptivityResponse>(`${M9}/predict/${growerId}`),
  placeVoiceCall: async (body: VoiceCallRequest): Promise<VoiceCallResponse> => {
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
  },
};
