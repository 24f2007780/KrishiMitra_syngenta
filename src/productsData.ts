// Syngenta canonical product database and market data definitions.
// Sourced from datasets/product-catalog/canonical_products.json and calendar_service/cache.json.

export interface CanonicalProduct {
  id: number;
  name: string;
  type: string;
  active_ingredients: string;
  description: string;
  target_crop: string;
  target_pest: string;
  effective_stages: string;
  treatment_intent: string;
  efficacy_rating: number;
  price_tier: "low" | "mid" | "premium" | string;
  application_mode: string;
  systemic: boolean;
  rain_sensitive_hours: number;
  moa_group: string;
  moa_class: string;
  resistance_management: string;
  epa_number: string | null;
  logo_url: string;
  product_url: string;
  directions: string;
  dosage: string;
  timing_window: string;
}

export const CANONICAL_PRODUCTS: CanonicalProduct[] = [
  {
    id: 1,
    name: "Topik 15 WP",
    type: "Herbicide",
    active_ingredients: "Clodinafop-propargyl 15% WP (150 g/kg)",
    description: "Selective post-emergence herbicide for control of grassy weeds, especially Phalaris minor (Canary grass), in wheat crops.",
    target_crop: "wheat",
    target_pest: "Phalaris minor (Canary grass), grassy weeds",
    effective_stages: "post-emergence, 30-35 DAS, weed 3-4 leaf stage, tillering",
    treatment_intent: "curative",
    efficacy_rating: 0.9,
    price_tier: "mid",
    application_mode: "Foliar spray",
    systemic: true,
    rain_sensitive_hours: 2,
    moa_group: "HRAC-A",
    moa_class: "ACCase inhibitor",
    resistance_management: "Use in rotation with herbicides having different modes of action (e.g., HRAC-K3) to delay resistance development in grassy weeds.",
    epa_number: null,
    logo_url: "https://www.syngenta.co.in/sites/g/files/kgtney376/files/styles/brand_logo/public/media/image/2021/12/16/topik-thumbnail_with_background.png?itok=f_FdmQi1",
    product_url: "https://www.syngenta.co.in/product/crop-protection/topik-15-wp",
    directions: "Apply 30-35 days after sowing when grassy weeds are at 3-4 leaf stage. Mix 400 g in 375-400 litres of water per hectare. Spray uniformly using a flat fan nozzle.",
    dosage: "160 g per acre (400 g/ha) in 150-160 L water",
    timing_window: "Apply 30-35 DAS at weed 3-4 leaf stage. Ensure at least 2 hours before rain.",
  },
  {
    id: 2,
    name: "Score 250 EC",
    type: "Fungicide",
    active_ingredients: "Difenoconazole 250 g/L",
    description: "Broad-spectrum systemic triazole fungicide effective against leaf rust, leaf spots, blight, and mildew diseases in multiple crops.",
    target_crop: "wheat, mustard, chickpea, lentil, barley, cabbage, cauliflower",
    target_pest: "leaf rust, leaf spot, blight, mildew, fungal diseases",
    effective_stages: "tillering, flowering, pod formation, canopy development, general",
    treatment_intent: "preventive, curative",
    efficacy_rating: 0.9,
    price_tier: "mid",
    application_mode: "Foliar spray",
    systemic: true,
    rain_sensitive_hours: 1,
    moa_group: "FRAC-3",
    moa_class: "DMI triazole",
    resistance_management: "Avoid repeated consecutive applications of FRAC Group 3 fungicides. Rotate with fungicides of different modes of action (FRAC-11 or FRAC-M5).",
    epa_number: null,
    logo_url: "https://www.syngenta.co.ke/sites/g/files/kgtney976/files/styles/brand_logo/public/media/image/2021/12/16/score_logo.jpg",
    product_url: "https://www.syngenta.co.ke/product/crop-protection/score-250-ec",
    directions: "Mix 20 ml in 20 litres of water for knapsack spraying. Spray evenly on crop foliage at early disease appearance or preventively. Use 200 ml per acre.",
    dosage: "200 ml per acre in 150-200 L water (20 ml per 15L sprayer)",
    timing_window: "Apply early morning/late afternoon at first symptom sign. 1-hour rain-fast.",
  },
  {
    id: 3,
    name: "Actara 25 WG",
    type: "Insecticide",
    active_ingredients: "Thiamethoxam 25% WG",
    description: "Systemic neonicotinoid insecticide with fast stomach and contact action for effective control of sucking pests including aphids, whiteflies, and borers.",
    target_crop: "mustard, maize, potato, chickpea, tomato, cabbage, cotton",
    target_pest: "aphid, whitefly, borer, leafminer, leafhopper, sucking pests",
    effective_stages: "vegetative, flowering, pod formation, transplanting, general",
    treatment_intent: "curative, rescue, preventive",
    efficacy_rating: 0.92,
    price_tier: "premium",
    application_mode: "Foliar spray / Soil drench",
    systemic: true,
    rain_sensitive_hours: 1,
    moa_group: "IRAC-4A",
    moa_class: "Neonicotinoid",
    resistance_management: "Do not apply more than 3 consecutive sprays. Rotate with insecticides having different IRAC groups (e.g. IRAC-6) to delay resistance.",
    epa_number: "100-938",
    logo_url: "https://assets.syngenta-us.com/images/prod_logos/Actaralogo.svg",
    product_url: "https://www.syngenta-us.com/insecticides/actara",
    directions: "Spray at first sign of aphids, whiteflies, or sucking pests. Ensure uniform leaf coverage using fine spray droplets. Avoid spraying during flowering to protect pollinators.",
    dosage: "40-80 g per acre depending on pest pressure in 150 L water",
    timing_window: "Early morning spray before pollinator activity; 1-hour rain-fastness.",
  },
  {
    id: 4,
    name: "Kavach 75 WP",
    type: "Fungicide",
    active_ingredients: "Chlorothalonil 75% WP",
    description: "Broad-spectrum non-systemic multi-site contact fungicide effective against early blight, late blight, rust, tikka disease, and fruit rot.",
    target_crop: "potato, groundnut, grapes, chillies, chickpea, cumin, wheat",
    target_pest: "early blight, late blight, tikka disease, rust, anthracnose, fungal diseases",
    effective_stages: "tillering, vegetative, flowering, pod formation, general",
    treatment_intent: "preventive",
    efficacy_rating: 0.84,
    price_tier: "low",
    application_mode: "Foliar spray",
    systemic: false,
    rain_sensitive_hours: 4,
    moa_group: "FRAC-M5",
    moa_class: "Chloronitrile (multi-site contact)",
    resistance_management: "Multi-site contact fungicide with minimal resistance risk. Excellent partner for tank mixing or alternating with systemic single-site fungicides.",
    epa_number: null,
    logo_url: "https://www.syngenta.co.in/sites/g/files/kgtney376/files/styles/brand_logo/public/media/image/2022/05/26/kavach-thumbnail_with_background.png?itok=29XbjIVZ",
    product_url: "https://www.syngenta.co.in/product/crop-protection/kavach",
    directions: "Spray preventively before disease spreads widely. Use 350-500 g per acre mixed in 150-200 litres of water. Ensure complete foliage coverage.",
    dosage: "400-500 g per acre in 200 L water",
    timing_window: "Preventive application prior to humid/cloudy spells. Allow 4 hours dry weather.",
  },
  {
    id: 5,
    name: "Amistar 250 SC",
    type: "Fungicide",
    active_ingredients: "Azoxystrobin 250 SC",
    description: "Broad-spectrum systemic and preventive fungicide with translaminar activity against rusts, blights, and mildew in cereals, vegetables, and oilseeds.",
    target_crop: "wheat, barley, maize, potato, tomato, mustard, chickpea",
    target_pest: "rust, septoria, blight, mildew, leaf spot, fungal diseases",
    effective_stages: "vegetative, tillering, flowering, early disease development, general",
    treatment_intent: "preventive, curative",
    efficacy_rating: 0.91,
    price_tier: "premium",
    application_mode: "Foliar spray",
    systemic: true,
    rain_sensitive_hours: 1,
    moa_group: "FRAC-11",
    moa_class: "QoI strobilurin",
    resistance_management: "Maximum 2 consecutive sprays. Alternate with fungicides possessing different modes of action (FRAC Group 3 or M5).",
    epa_number: "100-1313",
    logo_url: "https://assets.syngenta-us.com/images/prod_logos/amistartoplogo.svg",
    product_url: "https://www.syngenta-us.com/fungicides/amistar-top",
    directions: "Apply preventively before disease spreads. Use 200 ml per acre in 150-200 litres of water. Repeat after 10-14 days if high humidity persists.",
    dosage: "200 ml per acre in 150-200 L water",
    timing_window: "Apply at flag-leaf/tillering or early symptom onset; 1-hour rain-fastness.",
  },
  {
    id: 6,
    name: "Alto 5 SC",
    type: "Fungicide",
    active_ingredients: "Cyproconazole 5% SC",
    description: "Systemic triazole fungicide with strong curative activity against rusts, powdery mildew, and leaf spots in cereals and legumes.",
    target_crop: "wheat, triticale, soybean, peanuts",
    target_pest: "rust, powdery mildew, aerial blight, leaf spots",
    effective_stages: "tillering, vegetative, flowering, disease onset, general",
    treatment_intent: "curative",
    efficacy_rating: 0.87,
    price_tier: "mid",
    application_mode: "Foliar spray",
    systemic: true,
    rain_sensitive_hours: 1,
    moa_group: "FRAC-3",
    moa_class: "DMI triazole",
    resistance_management: "Rotate with FRAC Group 11 or Group M5 fungicides. Do not use sequentially if another triazole was applied previously.",
    epa_number: "100-1226",
    logo_url: "https://assets.syngenta-us.com/images/prod_logos/altologo.svg",
    product_url: "https://www.syngenta-us.com/fungicides/alto-100-sl",
    directions: "Apply at early disease appearance. Spray evenly for complete crop coverage. Suitable for tank mixing with compatible inputs.",
    dosage: "200 ml per acre in 150 L water",
    timing_window: "Curative spray at onset of fungal lesions. 1-hour rain-fast.",
  },
  {
    id: 7,
    name: "Vertimec 1.8 EC",
    type: "Insecticide / Acaricide",
    active_ingredients: "Abamectin 1.8% EC",
    description: "Biological-origin insecticide and acaricide with translaminar action against mites and leaf-feeding insect pests.",
    target_crop: "brinjal, potato, chickpea, cumin, maize, tomato",
    target_pest: "red spider mites, mites, borers, leafminers",
    effective_stages: "vegetative, flowering, pod formation, early infestation",
    treatment_intent: "curative",
    efficacy_rating: 0.85,
    price_tier: "mid",
    application_mode: "Foliar spray",
    systemic: false,
    rain_sensitive_hours: 3,
    moa_group: "IRAC-6",
    moa_class: "Avermectin",
    resistance_management: "Rotate with insecticides from different IRAC groups (e.g. IRAC-4A) to avoid mite resistance development.",
    epa_number: null,
    logo_url: "https://www.syngenta.com.bd/sites/g/files/kgtney411/files/styles/brand_logo/public/media/image/2025/11/09/vertimec_1.8ec_cmyk.jpg?itok=efOPsAxB",
    product_url: "https://www.syngenta.com.bd/product/crop-protection/vertimec-1.8-ec",
    directions: "Spray at first appearance of mites. Mix 1.25 ml per litre of water. Ensure complete spray coverage on leaf undersides where mites shelter.",
    dosage: "200-250 ml per acre in 150-200 L water",
    timing_window: "Spray early morning or dusk; allow 3 hours before rainfall.",
  },
  {
    id: 8,
    name: "Axial 50 EC",
    type: "Herbicide",
    active_ingredients: "Pinoxaden 50 EC",
    description: "Selective post-emergence ACCase inhibitor herbicide for control of wild oats, canary grass, and grassy weeds in wheat crops.",
    target_crop: "wheat, barley",
    target_pest: "wild oats, ryegrass, canary grass, grassy weeds",
    effective_stages: "post-emergence, tillering, 2-4 leaf weed stage",
    treatment_intent: "curative",
    efficacy_rating: 0.88,
    price_tier: "premium",
    application_mode: "Foliar spray",
    systemic: true,
    rain_sensitive_hours: 1,
    moa_group: "HRAC-A",
    moa_class: "ACCase inhibitor",
    resistance_management: "Rotate with herbicides from different HRAC groups. Do not apply more than once per crop season.",
    epa_number: "100-1632",
    logo_url: "https://www.syngenta.co.zm/sites/g/files/kgtney966/files/styles/brand_logo/public/media/image/2019/07/24/axial_thumb_nail.jpg?itok=kj6wDy4Q",
    product_url: "https://www.syngenta.co.zm/product/crop-protection/axial-050-ec",
    directions: "Apply only on young actively growing weeds at 2-4 leaf stage. Use 350-400 ml per acre with flat fan nozzles for complete weed coverage.",
    dosage: "350-400 ml per acre in 150 L water",
    timing_window: "Weed 2-4 leaf stage during active tillering. 1-hour rain-fast.",
  },
  {
    id: 9,
    name: "Cruiser 350 FS",
    type: "Seed Treatment",
    active_ingredients: "Thiamethoxam 30% FS",
    description: "Systemic seed treatment insecticide providing early-season protection against sucking pests and wireworms, ensuring vigorous crop establishment.",
    target_crop: "cotton, wheat, soybean, maize, chickpea, mustard",
    target_pest: "aphids, borers, soil insects, early-season sucking pests",
    effective_stages: "seed treatment, sowing, germination, early seedling",
    treatment_intent: "preventive, seed_treatment",
    efficacy_rating: 0.82,
    price_tier: "mid",
    application_mode: "Seed treatment",
    systemic: true,
    rain_sensitive_hours: 0,
    moa_group: "IRAC-4A",
    moa_class: "Neonicotinoid",
    resistance_management: "Avoid repeated use of Group 4A across consecutive crop cycles to sustain efficacy.",
    epa_number: "100-941",
    logo_url: "https://assets.syngenta-us.com/images/prod_logos/cruiser5fslogo.svg",
    product_url: "https://www.syngenta-us.com/seed-treatment/cruiser-5fs",
    directions: "Apply directly as seed treatment before sowing. Mix 3-5 ml per kg seed with 10 ml water slurry. Dry in shade before sowing.",
    dosage: "3-5 ml per kg seed",
    timing_window: "Seed treatment 12-24 hours prior to sowing.",
  },
  {
    id: 10,
    name: "Tilt 250 EC",
    type: "Fungicide",
    active_ingredients: "Propiconazole 250 g/L EC",
    description: "Systemic triazole fungicide providing rapid curative and residual preventive control of stripe rust, brown rust, and leaf blights in cereals.",
    target_crop: "wheat, barley, lentil, mustard, rice",
    target_pest: "stem rust, yellow rust, leaf spot, powdery mildew, blight",
    effective_stages: "tillering, flowering, disease onset, general",
    treatment_intent: "preventive, curative",
    efficacy_rating: 0.86,
    price_tier: "low",
    application_mode: "Foliar spray",
    systemic: true,
    rain_sensitive_hours: 2,
    moa_group: "FRAC-3",
    moa_class: "DMI triazole",
    resistance_management: "Rotate with fungicides having different FRAC groups (FRAC-11 or FRAC-M5) to suppress resistance.",
    epa_number: "100-617",
    logo_url: "https://assets.syngenta-us.com/images/prod_logos/tiltlogo.svg",
    product_url: "https://www.syngenta-us.com/fungicides/tilt",
    directions: "Apply at early disease appearance. Use 200 ml per acre for wheat rust control. Ensure thorough foliage coverage using 150-200 L water per acre.",
    dosage: "200 ml per acre in 150-200 L water (20 ml per 15-20L knapsack sprayer)",
    timing_window: "Apply immediately upon rust observation. Ensure 2 hours dry canopy.",
  },
  {
    id: 11,
    name: "Movondo",
    type: "Herbicide",
    active_ingredients: "Pyroxasulfone 85% WG",
    description: "Selective early post-emergence herbicide providing multi-spectrum residual control of Phalaris minor and hardy broadleaf weeds.",
    target_crop: "wheat, maize, soybean",
    target_pest: "Phalaris minor, annual grasses, broadleaf weeds",
    effective_stages: "post-emergence, vegetative, tillering",
    treatment_intent: "curative, rescue",
    efficacy_rating: 0.9,
    price_tier: "premium",
    application_mode: "Foliar spray",
    systemic: true,
    rain_sensitive_hours: 1,
    moa_group: "HRAC-K3",
    moa_class: "VLCFA inhibitor",
    resistance_management: "Ideal rotation partner for ACCase-resistant grassy weeds. Breaks cross-resistance cycles.",
    epa_number: null,
    logo_url: "https://www.syngenta.co.in/sites/g/files/kgtney376/files/styles/brand_logo/public/media/image/2024/09/25/0917p24-syn-movondo-banner.jpg?itok=SnmqU4OA",
    product_url: "https://www.syngenta.co.in/product/crop-protection/herbicide/movondo",
    directions: "Apply as early post-emergence spray on actively growing weeds. Use 60 g per acre mixed in 150-200 litres of water with flat fan nozzle.",
    dosage: "60 g per acre in 150-200 L water",
    timing_window: "Early post-emergence 20-30 DAS under moist soil conditions.",
  },
  {
    id: 12,
    name: "Vibrance Integral",
    type: "Seed Treatment",
    active_ingredients: "Sedaxane 15% + Azoxystrobin 3.75% + Thiamethoxam 26.25% FS",
    description: "Comprehensive triple-action seed treatment providing root health protection, seedling vigor, and control against early chewing and sucking pests.",
    target_crop: "rice, wheat, maize, chickpea, potato",
    target_pest: "sheath blight, seed rot, damping-off, root rot, thrips, aphids",
    effective_stages: "seed treatment, sowing, germination, seedling",
    treatment_intent: "preventive, seed_treatment",
    efficacy_rating: 0.9,
    price_tier: "premium",
    application_mode: "Seed treatment",
    systemic: true,
    rain_sensitive_hours: 0,
    moa_group: "FRAC-11+7 / IRAC-4A",
    moa_class: "QoI + SDHI + Neonicotinoid",
    resistance_management: "Built-in multiple modes of action naturally delay pathogen and insect resistance.",
    epa_number: "100-1656",
    logo_url: "https://assets.syngenta-us.com/images/prod_logos/VibranceRST_RGB.SVG",
    product_url: "https://www.syngenta-us.com/fungicides/vibrance-rst",
    directions: "Mix 3 ml product per kg seed with 10 ml water to form uniform coating slurry. Dry in shade before sowing.",
    dosage: "3 ml per kg seed",
    timing_window: "Treat seed prior to sowing; dry in shade.",
  },
];

// Helper to look up canonical product details by name (case-insensitive substring)
export function findCanonicalProduct(name: string): CanonicalProduct | undefined {
  if (!name) return undefined;
  const clean = name.toLowerCase().trim();
  return (
    CANONICAL_PRODUCTS.find((p) => p.name.toLowerCase() === clean) ||
    CANONICAL_PRODUCTS.find((p) => clean.includes(p.name.toLowerCase()) || p.name.toLowerCase().includes(clean))
  );
}

// Fallback/enrichment helper
export function enrichProduct(productName: string): Partial<CanonicalProduct> {
  const match = findCanonicalProduct(productName);
  if (match) return match;

  // Sensible default for any unknown input
  return {
    name: productName,
    type: "Crop Protection Input",
    active_ingredients: "Agronomic formulation",
    application_mode: "Foliar spray",
    dosage: "200 ml / 400 g per acre in 150-200 L water",
    timing_window: "Apply early morning in calm weather",
    directions: "Mix recommended quantity uniformly in clean water. Spray using a knapsack sprayer with flat fan nozzle.",
    rain_sensitive_hours: 2,
    moa_group: "Standard Mode of Action",
    moa_class: "Syngenta crop protection",
    resistance_management: "Rotate with different chemical classes across spray cycles.",
    price_tier: "mid",
    logo_url: "https://www.syngenta.co.in/sites/g/files/kgtney376/files/styles/brand_logo/public/media/image/2021/12/16/score_logo.jpg",
  };
}

// Live Mandi and MSP market benchmarks (fallback aligned with calendar_service cache)
export interface MarketBenchmark {
  commodity: string;
  msp_rs_quintal: string;
  today_price_rs_quintal: string;
  today_arrival_metric_tonnes: string;
  trend: "up" | "down" | "stable";
  market_name?: string;
}

export const MANDI_MARKET_BENCHMARKS: Record<string, MarketBenchmark> = {
  wheat: {
    commodity: "Wheat",
    msp_rs_quintal: "2585.00",
    today_price_rs_quintal: "2469.30",
    today_arrival_metric_tonnes: "57354.99",
    trend: "down",
    market_name: "Khanna Mandi (Punjab) / Bharatpur Mandi",
  },
  cotton: {
    commodity: "Cotton",
    msp_rs_quintal: "7710.00",
    today_price_rs_quintal: "8255.09",
    today_arrival_metric_tonnes: "1928.91",
    trend: "up",
    market_name: "Rajkot APMC / Surat Mandi",
  },
  rice: {
    commodity: "Paddy (Common)",
    msp_rs_quintal: "2369.00",
    today_price_rs_quintal: "2236.51",
    today_arrival_metric_tonnes: "31940.04",
    trend: "down",
    market_name: "Karnal APMC / Thanjavur Mandi",
  },
  paddy: {
    commodity: "Paddy (Common)",
    msp_rs_quintal: "2369.00",
    today_price_rs_quintal: "2236.51",
    today_arrival_metric_tonnes: "31940.04",
    trend: "down",
    market_name: "Karnal APMC / Thanjavur Mandi",
  },
  maize: {
    commodity: "Maize",
    msp_rs_quintal: "2400.00",
    today_price_rs_quintal: "1670.99",
    today_arrival_metric_tonnes: "32521.00",
    trend: "down",
    market_name: "Davangere APMC / Chhindwara Mandi",
  },
  mustard: {
    commodity: "Mustard (Rapeseed)",
    msp_rs_quintal: "5650.00",
    today_price_rs_quintal: "5890.00",
    today_arrival_metric_tonnes: "12450.00",
    trend: "up",
    market_name: "Alwar Mandi / Bharatpur APMC",
  },
  chickpea: {
    commodity: "Gram (Chickpea/Bengalgram)",
    msp_rs_quintal: "5440.00",
    today_price_rs_quintal: "5750.00",
    today_arrival_metric_tonnes: "8120.00",
    trend: "up",
    market_name: "Indore Mandi / Latur APMC",
  },
  bengalgram: {
    commodity: "Bengalgram",
    msp_rs_quintal: "5440.00",
    today_price_rs_quintal: "5750.00",
    today_arrival_metric_tonnes: "8120.00",
    trend: "up",
    market_name: "Latur Mandi",
  },
  groundnut: {
    commodity: "Groundnut",
    msp_rs_quintal: "7263.00",
    today_price_rs_quintal: "7306.85",
    today_arrival_metric_tonnes: "906.10",
    trend: "up",
    market_name: "Gondal APMC / Junagadh Mandi",
  },
  bajra: {
    commodity: "Bajra (Pearl Millet)",
    msp_rs_quintal: "2775.00",
    today_price_rs_quintal: "2207.30",
    today_arrival_metric_tonnes: "1110.38",
    trend: "down",
    market_name: "Jaipur APMC",
  },
};

export function getMandiBenchmark(cropName: string): MarketBenchmark {
  const clean = (cropName || "").toLowerCase().trim();
  for (const [key, val] of Object.entries(MANDI_MARKET_BENCHMARKS)) {
    if (clean.includes(key) || key.includes(clean)) {
      return val;
    }
  }
  return MANDI_MARKET_BENCHMARKS.wheat;
}
