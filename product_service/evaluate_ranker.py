"""
M8 Product Ranker — Performance Evaluation
Syngenta IITM Hackathon 2026

═══════════════════════════════════════════════════════════════════
HOW TO TEST A RECOMMENDATION SYSTEM WITHOUT EXPLICIT LABELS
═══════════════════════════════════════════════════════════════════

Problem: No one labeled "this was the correct product for this farmer."

Solution: Use IMPLICIT FEEDBACK from real behavior:
  - If a farmer in crop X, district Y, bought product Z → that's a positive signal
  - Test: Would our ranker have recommended Z in that context?

Metrics:
  1. Hit Rate @K: Did the purchased product appear in top-K recommendations?
  2. MRR (Mean Reciprocal Rank): How high did the purchased product rank?
  3. NDCG @K: Normalized Discounted Cumulative Gain
  4. Coverage: What % of products does the system recommend across all queries?
  5. Diversity: How diverse are recommendations (MoA spread)?
  6. Agronomic Coherence: Do recommendations match crop-pest domain rules?

Evaluation Strategy:
  - Temporal split: Train model on Oct–Feb POS, evaluate on Mar–Apr purchases
  - For each Mar–Apr purchase, reconstruct the farmer's context and ask:
    "Would the ranker have recommended this product?"

═══════════════════════════════════════════════════════════════════
"""

import sys
import json
import math
from pathlib import Path
from collections import defaultdict, Counter
from typing import List

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from product_service.ranker import rank_products
from shared.models import RankRequest, CropType, PestType, CropStage
from product_service.product_catalog import PRODUCT_CATALOG, get_moa_group

DATA_DIR = Path("dataset")

print("=" * 70)
print("M8 PRODUCT RANKER — PERFORMANCE EVALUATION")
print("=" * 70)
print()

# ── 1. Load data ───────────────────────────────────────────────────────────────
print("[1] LOADING DATA")
print("-" * 50)

growers_df = pd.read_csv(DATA_DIR / "growers.csv")
retailers_df = pd.read_csv(DATA_DIR / "retailers.csv")
pos_df = pd.read_csv(DATA_DIR / "retailer_pos.csv")

pos_df["transaction_date"] = pd.to_datetime(pos_df["transaction_date"])

# Map retailers to districts
retailer_district = retailers_df[["retailer_id", "state", "district", "tehsil"]].drop_duplicates()
pos_geo = pos_df.merge(retailer_district, on="retailer_id", how="inner")

# Map tehsils/districts/states to lists of growers for deterministic alignment
tehsil_to_growers = growers_df.groupby("tehsil")["grower_id"].apply(list).to_dict()
district_to_growers = growers_df.groupby("district")["grower_id"].apply(list).to_dict()
state_to_growers = growers_df.groupby("state")["grower_id"].apply(list).to_dict()
all_growers = growers_df["grower_id"].tolist()

grower_ids = []
for idx, row in pos_geo.iterrows():
    teh = row["tehsil"]
    dist = row["district"]
    st = row["state"]
    
    g_list = tehsil_to_growers.get(teh)
    if not g_list:
        g_list = district_to_growers.get(dist)
    if not g_list:
        g_list = state_to_growers.get(st)
    if not g_list:
        g_list = all_growers
        
    g_idx = hash(row["transaction_id"]) % len(g_list)
    grower_ids.append(g_list[g_idx])

pos_geo["grower_id"] = grower_ids

# Map growers to crops
def parse_crop(cal):
    try:
        cal = json.loads(cal) if isinstance(cal, str) else {}
        return str(cal.get("crop", "unknown")).lower()
    except:
        return "unknown"

growers_df["crop"] = growers_df["grower_crop_calendar"].apply(parse_crop)
grower_info = growers_df[["grower_id", "crop", "district", "tehsil", "grower_farm_size"]].copy()
grower_farm_sizes = growers_df.set_index("grower_id")["grower_farm_size"].to_dict()

print(f"    POS transactions: {len(pos_df)}")
print(f"    Growers: {len(growers_df)}")
print(f"    Products in catalog: {len(PRODUCT_CATALOG)}")
print()

# ── 2. Build evaluation set ────────────────────────────────────────────────────
print("[2] BUILDING EVALUATION SET (Temporal Holdout: Mar–Apr 2026)")
print("-" * 50)

# Temporal split: evaluate on March–April purchases
split_date = pd.Timestamp("2026-03-01")
eval_pos = pos_geo[pos_geo["transaction_date"] >= split_date].copy()

print(f"    Evaluation period: {split_date.date()} onwards")
print(f"    Evaluation transactions: {len(eval_pos)}")
print()

# For each district+product purchase, reconstruct context
# Group by district to infer crop context
district_crop = grower_info.groupby("district")["crop"].agg(
    lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "wheat"
).to_dict()

# Helper Functions for Evaluation
def infer_pest_from_product(product_name: str) -> PestType:
    info = PRODUCT_CATALOG.get(product_name)
    if not info:
        return PestType.general
    category = info.get("category", "").lower()
    if "herbicide" in category:
        return PestType.weeds
    target_pests = info.get("target_pests", set())
    # If the product specifically targets one of the PestType values, use it
    for p in target_pests:
        p_clean = p.strip().lower()
        for pest_enum in PestType:
            if pest_enum.value == p_clean:
                return pest_enum
    if "fungicide" in category:
        return PestType.fungal
    if "insecticide" in category:
        return PestType.aphid
    return PestType.general

def is_agronomically_equivalent(prod_a: str, prod_b: str) -> bool:
    if prod_a == prod_b:
        return True
    info_a = PRODUCT_CATALOG.get(prod_a)
    info_b = PRODUCT_CATALOG.get(prod_b)
    if not info_a or not info_b:
        return False
    # Same category
    if info_a.get("category") != info_b.get("category"):
        return False
    # Same crop (at least one intersection)
    if not info_a["target_crops"].intersection(info_b["target_crops"]):
        return False
    # Same pest target (at least one intersection)
    if not info_a["target_pests"].intersection(info_b["target_pests"]):
        return False
    return True

def is_moa_safe(prod: str, recently_used: List[str]) -> bool:
    prod_moa = get_moa_group(prod)
    if prod_moa == "unknown" or not recently_used:
        return True
    recent_moas = {get_moa_group(p) for p in recently_used if get_moa_group(p) != "unknown"}
    return prod_moa not in recent_moas

def targets_pest_and_crop(prod: str, pest: str, crop: str) -> bool:
    info = PRODUCT_CATALOG.get(prod)
    if not info:
        return False
    crop_match = any(crop.lower() in c for c in info.get("target_crops", set()))
    if not crop_match:
        return False
    if pest == "general":
        return True
    pest_match = any(pest.lower() in p for p in info.get("target_pests", set()))
    return pest_match

# Build evaluation queries: (district, inferred_crop, purchased_product)
eval_queries = []
for _, row in eval_pos.iterrows():
    district = row["district"]
    product = row["sku_name"]
    crop = district_crop.get(district, "wheat")

    # Only evaluate products in our catalog
    if product not in PRODUCT_CATALOG:
        continue

    # Map crop to CropType enum (skip unknowns)
    crop_map = {
        "wheat": "wheat", "mustard": "mustard", "chickpea": "chickpea",
        "potato": "potato", "barley": "barley", "lentil": "lentil",
        "cumin": "cumin", "maize": "maize", "safflower": "safflower",
        "rice": "rice", "cotton": "cotton",
    }
    if crop not in crop_map:
        continue

    eval_queries.append({
        "grower_id": row["grower_id"],
        "district": district,
        "crop": crop,
        "purchased_product": product,
        "date": row["transaction_date"],
        "grower_farm_size": grower_farm_sizes.get(row["grower_id"]),
    })

print(f"    Valid evaluation queries: {len(eval_queries)}")
print(f"    Unique districts: {len(set(q['district'] for q in eval_queries))}")
print(f"    Unique products purchased: {len(set(q['purchased_product'] for q in eval_queries))}")
print()

# ── 3. Run ranker on evaluation queries ────────────────────────────────────────
print("[3] RUNNING RANKER ON EVALUATION QUERIES")
print("-" * 50)

# Sample for speed (full eval on all 50k+ would be slow)
sample_size = min(2000, len(eval_queries))
np.random.seed(42)
sampled_queries = [eval_queries[i] for i in np.random.choice(len(eval_queries), sample_size, replace=False)]

# exact SKU hits
hits_at_2 = 0
hits_at_3 = 0
hits_at_5 = 0

# agronomic hits (agronomically valid alternatives)
agronomic_hits_at_2 = 0
agronomic_hits_at_3 = 0
agronomic_hits_at_5 = 0

# MoA aware hits (agronomically valid + resistance safe)
moa_hits_at_2 = 0
moa_hits_at_3 = 0
moa_hits_at_5 = 0

# functional recall (problem solved regardless of SKU)
functional_recall_at_2 = 0
functional_recall_at_3 = 0
functional_recall_at_5 = 0

# baselines (empirically calculated on same queries for fair comparison)
random_hits_at_2 = 0
random_hits_at_5 = 0
random_agronomic_hits_at_2 = 0
random_agronomic_hits_at_5 = 0

pop_hits_at_2 = 0
pop_hits_at_5 = 0
pop_agronomic_hits_at_2 = 0
pop_agronomic_hits_at_5 = 0

# Get training popularity (prior to split date)
train_pos = pos_geo[pos_geo["transaction_date"] < split_date]
popular_skus = train_pos["sku_name"].value_counts().index.tolist()
all_products = list(PRODUCT_CATALOG.keys())

reciprocal_ranks = []
all_recommended = Counter()
moa_diversity_scores = []

crop_type_map = {
    "wheat": CropType.wheat, "mustard": CropType.mustard,
    "chickpea": CropType.chickpea, "potato": CropType.potato,
    "barley": CropType.barley, "lentil": CropType.lentil,
    "cumin": CropType.cumin, "maize": CropType.maize,
    "safflower": CropType.safflower, "rice": CropType.rice,
    "cotton": CropType.cotton,
}

for i, query in enumerate(sampled_queries):
    crop_enum = crop_type_map.get(query["crop"])
    if crop_enum is None:
        continue

    # Reconstruct grower history prior to transaction
    query_date = query["date"]
    grower_id = query["grower_id"]
    grower_history = pos_geo[
        (pos_geo["grower_id"] == grower_id) & 
        (pos_geo["transaction_date"] < query_date)
    ]
    recent_cutoff = query_date - pd.Timedelta(days=14)
    recently_used = grower_history[grower_history["transaction_date"] >= recent_cutoff]["sku_name"].tolist()
    spray_history = grower_history["sku_name"].tolist()

    purchased = query["purchased_product"]
    pest_enum = infer_pest_from_product(purchased)

    request = RankRequest(
        grower_id=grower_id,
        crop=crop_enum,
        pest=pest_enum,
        district=query["district"],
        urgency_score=0.5,  # neutral
        grower_farm_size=None if pd.isna(query["grower_farm_size"]) else float(query["grower_farm_size"]),
        recently_used_products=recently_used if recently_used else None,
        spray_history=spray_history if spray_history else None,
        top_k=5,
    )

    result = rank_products(request)
    recommended_names = [p.product_name for p in result.top_products]

    # Track all recommendations for coverage
    for name in recommended_names:
        all_recommended[name] += 1

    # Exact SKU Hit rate
    if purchased in recommended_names[:2]:
        hits_at_2 += 1
    if purchased in recommended_names[:3]:
        hits_at_3 += 1
    if purchased in recommended_names[:5]:
        hits_at_5 += 1

    # Reciprocal rank
    if purchased in recommended_names:
        rank = recommended_names.index(purchased) + 1
        reciprocal_ranks.append(1.0 / rank)
    else:
        reciprocal_ranks.append(0.0)

    # Agronomic Hit rate
    if any(is_agronomically_equivalent(p, purchased) for p in recommended_names[:2]):
        agronomic_hits_at_2 += 1
    if any(is_agronomically_equivalent(p, purchased) for p in recommended_names[:3]):
        agronomic_hits_at_3 += 1
    if any(is_agronomically_equivalent(p, purchased) for p in recommended_names[:5]):
        agronomic_hits_at_5 += 1

    # MoA-aware Hit rate
    if any(is_agronomically_equivalent(p, purchased) and is_moa_safe(p, recently_used) for p in recommended_names[:2]):
        moa_hits_at_2 += 1
    if any(is_agronomically_equivalent(p, purchased) and is_moa_safe(p, recently_used) for p in recommended_names[:3]):
        moa_hits_at_3 += 1
    if any(is_agronomically_equivalent(p, purchased) and is_moa_safe(p, recently_used) for p in recommended_names[:5]):
        moa_hits_at_5 += 1

    # Functional Recall
    if any(targets_pest_and_crop(p, pest_enum.value, query["crop"]) for p in recommended_names[:2]):
        functional_recall_at_2 += 1
    if any(targets_pest_and_crop(p, pest_enum.value, query["crop"]) for p in recommended_names[:3]):
        functional_recall_at_3 += 1
    if any(targets_pest_and_crop(p, pest_enum.value, query["crop"]) for p in recommended_names[:5]):
        functional_recall_at_5 += 1

    # Empirical Baselines: Random
    rand_rec = list(np.random.choice(all_products, 5, replace=False))
    if purchased in rand_rec[:2]:
        random_hits_at_2 += 1
    if purchased in rand_rec[:5]:
        random_hits_at_5 += 1
    if any(is_agronomically_equivalent(p, purchased) for p in rand_rec[:2]):
        random_agronomic_hits_at_2 += 1
    if any(is_agronomically_equivalent(p, purchased) for p in rand_rec[:5]):
        random_agronomic_hits_at_5 += 1

    # Empirical Baselines: Popularity
    pop_rec = popular_skus[:5]
    if purchased in pop_rec[:2]:
        pop_hits_at_2 += 1
    if purchased in pop_rec[:5]:
        pop_hits_at_5 += 1
    if any(is_agronomically_equivalent(p, purchased) for p in pop_rec[:2]):
        pop_agronomic_hits_at_2 += 1
    if any(is_agronomically_equivalent(p, purchased) for p in pop_rec[:5]):
        pop_agronomic_hits_at_5 += 1

    # MoA diversity in top-3
    moa_groups = set(get_moa_group(p) for p in recommended_names[:3] if get_moa_group(p) != "unknown")
    moa_diversity_scores.append(len(moa_groups) / 3.0 if len(recommended_names) >= 3 else 0)

    if (i + 1) % 500 == 0:
        print(f"    Processed {i+1}/{sample_size} queries...")

print(f"    Completed {sample_size} evaluations.")
print()

# ── 4. Compute metrics ─────────────────────────────────────────────────────────
print("[4] EVALUATION METRICS")
print("-" * 50)

n = len(sampled_queries)
hit_rate_2 = hits_at_2 / n
hit_rate_3 = hits_at_3 / n
hit_rate_5 = hits_at_5 / n

agro_hit_rate_2 = agronomic_hits_at_2 / n
agro_hit_rate_3 = agronomic_hits_at_3 / n
agro_hit_rate_5 = agronomic_hits_at_5 / n

moa_hit_rate_2 = moa_hits_at_2 / n
moa_hit_rate_3 = moa_hits_at_3 / n
moa_hit_rate_5 = moa_hits_at_5 / n

func_recall_2 = functional_recall_at_2 / n
func_recall_3 = functional_recall_at_3 / n
func_recall_5 = functional_recall_at_5 / n

mrr = np.mean(reciprocal_ranks)
avg_diversity = np.mean(moa_diversity_scores)
coverage = len(all_recommended) / len(PRODUCT_CATALOG)

print(f"    Exact Hit Rate @2:    {hit_rate_2:.4f}  ({hits_at_2}/{n} SKU matches in top-2)")
print(f"    Exact Hit Rate @3:    {hit_rate_3:.4f}  ({hits_at_3}/{n} SKU matches in top-3)")
print(f"    Exact Hit Rate @5:    {hit_rate_5:.4f}  ({hits_at_5}/{n} SKU matches in top-5)")
print()
print(f"    Agronomic Hit@2:      {agro_hit_rate_2:.4f}  ({agronomic_hits_at_2}/{n} agronomically valid in top-2)")
print(f"    Agronomic Hit@3:      {agro_hit_rate_3:.4f}  ({agronomic_hits_at_3}/{n} agronomically valid in top-3)")
print(f"    Agronomic Hit@5:      {agro_hit_rate_5:.4f}  ({agronomic_hits_at_5}/{n} agronomically valid in top-5)")
print()
print(f"    MoA-aware Hit@2:      {moa_hit_rate_2:.4f}  ({moa_hits_at_2}/{n} resistance-safe in top-2)")
print(f"    MoA-aware Hit@3:      {moa_hit_rate_3:.4f}  ({moa_hits_at_3}/{n} resistance-safe in top-3)")
print(f"    MoA-aware Hit@5:      {moa_hit_rate_5:.4f}  ({moa_hits_at_5}/{n} resistance-safe in top-5)")
print()
print(f"    Functional Recall @2: {func_recall_2:.4f}  ({functional_recall_at_2}/{n} solved in top-2)")
print(f"    Functional Recall @5: {func_recall_5:.4f}  ({functional_recall_at_5}/{n} solved in top-5)")
print()
print(f"    MRR:                  {mrr:.4f}  (Mean Reciprocal Rank)")
print(f"    Coverage:             {coverage:.2%}  ({len(all_recommended)}/{len(PRODUCT_CATALOG)} products recommended)")
print(f"    MoA Diversity:        {avg_diversity:.4f}  (avg unique MoA groups in top-3)")
print()

# ── 5. Random baseline comparison ─────────────────────────────────────────────
print("[5] BASELINE COMPARISON (EMPIRICAL)")
print("-" * 50)
rand_hit_2 = random_hits_at_2 / n
rand_hit_5 = random_hits_at_5 / n
rand_agro_hit_2 = random_agronomic_hits_at_2 / n
rand_agro_hit_5 = random_agronomic_hits_at_5 / n

pop_hit_2 = pop_hits_at_2 / n
pop_hit_5 = pop_hits_at_5 / n
pop_agro_hit_2 = pop_agronomic_hits_at_2 / n
pop_agro_hit_5 = pop_agronomic_hits_at_5 / n

print(f"    Random baseline Exact Hit@2:     {rand_hit_2:.4f}")
print(f"    Random baseline Agronomic Hit@2: {rand_agro_hit_2:.4f}")
print(f"    Popularity baseline Exact Hit@2: {pop_hit_2:.4f}  (always recommend {popular_skus[:2]})")
print(f"    Popularity baseline Agro Hit@2:  {pop_agro_hit_2:.4f}")
print()
print(f"    M8 Ranker Exact Hit@2:           {hit_rate_2:.4f}")
print(f"    M8 Ranker Agronomic Hit@2:       {agro_hit_rate_2:.4f}")
print()

lift_over_random_exact = hit_rate_2 / rand_hit_2 if rand_hit_2 > 0 else 0
lift_over_random_agro = agro_hit_rate_2 / rand_agro_hit_2 if rand_agro_hit_2 > 0 else 0
lift_over_pop_exact = hit_rate_2 / pop_hit_2 if pop_hit_2 > 0 else 0
lift_over_pop_agro = agro_hit_rate_2 / pop_agro_hit_2 if pop_agro_hit_2 > 0 else 0

print(f"    Lift over random (Exact):     {lift_over_random_exact:.2f}×")
print(f"    Lift over random (Agronomic): {lift_over_random_agro:.2f}×")
print(f"    Lift over popularity (Exact): {lift_over_pop_exact:.2f}×")
print(f"    Lift over popularity (Agro):  {lift_over_pop_agro:.2f}×")
print()

# ── 6. Per-crop breakdown ──────────────────────────────────────────────────────
print("[6] PER-CROP HIT RATE")
print("-" * 50)

crop_hits = defaultdict(lambda: {"hits": 0, "total": 0})
for i, query in enumerate(sampled_queries):
    crop = query["crop"]
    crop_hits[crop]["total"] += 1
    # Check if purchased product was in top-3 for this query
    crop_enum = crop_type_map.get(crop)
    if crop_enum:
        pest_enum = infer_pest_from_product(query["purchased_product"])
        request = RankRequest(crop=crop_enum, pest=pest_enum, district=query["district"], top_k=3)
        result = rank_products(request)
        if query["purchased_product"] in [p.product_name for p in result.top_products]:
            crop_hits[crop]["hits"] += 1

print(f"    {'Crop':<12} {'Hit@3':<10} {'Queries'}")
print(f"    {'-'*12} {'-'*10} {'-'*8}")
for crop in sorted(crop_hits.keys()):
    data = crop_hits[crop]
    rate = data["hits"] / data["total"] if data["total"] > 0 else 0
    print(f"    {crop:<12} {rate:<10.3f} {data['total']}")
print()

# ── 7. Agronomic coherence check ──────────────────────────────────────────────
print("[7] AGRONOMIC COHERENCE (sanity checks)")
print("-" * 50)

coherence_checks = [
    ("wheat", "rust", "Score 250 EC"),
    ("wheat", "weeds", "Topik 15 WP"),
    ("potato", "blight", "Kavach 75 WP"),
    ("chickpea", "aphid", "Actara 25 WG"),
    ("mustard", "fungal", "Score 250 EC"),
]

coherent = 0
for crop, pest, expected in coherence_checks:
    crop_enum = crop_type_map[crop]
    pest_enum = PestType(pest)
    request = RankRequest(crop=crop_enum, pest=pest_enum, top_k=3)
    result = rank_products(request)
    names = [p.product_name for p in result.top_products]
    passed = expected in names
    coherent += int(passed)
    status = "✓" if passed else "✗"
    print(f"    {status} {crop} + {pest} → expects {expected}: {'FOUND' if passed else 'NOT in top-3 (got: ' + str(names) + ')'}")

print(f"\n    Coherence: {coherent}/{len(coherence_checks)} domain rules satisfied")
print()

# ── 8. Verdict ─────────────────────────────────────────────────────────────────
print("=" * 70)
print("VERDICT")
print("=" * 70)
print()
print(f"  Exact Hit Rate @2:     {hit_rate_2:.3f} (random={rand_hit_2:.3f}, lift={lift_over_random_exact:.1f}×)")
print(f"  Agronomic Hit Rate @2: {agro_hit_rate_2:.3f} (random={rand_agro_hit_2:.3f}, lift={lift_over_random_agro:.1f}×)")
print(f"  MoA-aware Hit Rate @2: {moa_hit_rate_2:.3f}")
print(f"  Functional Recall @2:  {func_recall_2:.3f}")
print(f"  Exact Hit Rate @5:     {hit_rate_5:.3f}")
print(f"  Agronomic Hit Rate @5: {agro_hit_rate_5:.3f}")
print(f"  MRR:                   {mrr:.3f}")
print(f"  Coverage:              {coverage:.0%}")
print(f"  MoA Diversity:         {avg_diversity:.2f}")
print(f"  Coherence:             {coherent}/{len(coherence_checks)}")
print()

if agro_hit_rate_2 > rand_agro_hit_2 * 2:
    print("  ✓ Ranker significantly outperforms random baseline on Agronomic Hit Rate.")
else:
    print("  △ Ranker shows modest agronomic improvement over random.")

if agro_hit_rate_2 > pop_agro_hit_2:
    print("  ✓ Ranker outperforms popularity-only baseline on Agronomic Hit Rate.")
else:
    print("  △ Popularity baseline is competitive (common in sparse catalogs).")

if coherent >= 4:
    print("  ✓ Strong agronomic coherence — domain rules satisfied.")
else:
    print("  △ Some agronomic rules not satisfied — review catalog.")

if coverage > 0.8:
    print("  ✓ Good catalog coverage — not stuck recommending same products.")
else:
    print("  △ Limited catalog coverage — popularity or scoring collapse suspected.")

if avg_diversity > 0.5:
    print("  ✓ Good MoA diversity — resistance management working.")

print()
print("=" * 70)
