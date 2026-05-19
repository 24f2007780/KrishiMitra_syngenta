"""
M8 Product Ranker — ML Training Pipeline
Syngenta IITM Hackathon 2026

Learns product recommendation signals from real data:
1. Crop→Product affinity (from POS + grower crop calendars)
2. District→Product popularity (regional preference)
3. Product availability (from inventory snapshots)
4. Crop bestsellers (fallback recommendations)

No synthetic features. All signals derived from actual transactions.
"""

import argparse
import pickle
import logging
import json
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_crop(cal_json):
    try:
        cal = json.loads(cal_json) if isinstance(cal_json, str) else {}
        return str(cal.get("crop", "unknown")).lower()
    except Exception:
        return "unknown"


def train(data_dir: str, output_path: str):
    data_dir = Path(data_dir)
    logger.info("Loading data from %s", data_dir)

    growers_df = pd.read_csv(data_dir / "growers.csv")
    retailers_df = pd.read_csv(data_dir / "retailers.csv")
    pos_df = pd.read_csv(data_dir / "retailer_pos.csv")
    inventory_df = pd.read_csv(data_dir / "retailer_inventory_weekly.csv")
    visits_df = pd.read_csv(data_dir / "retailer_visit_log.csv")

    pos_df["transaction_date"] = pd.to_datetime(pos_df["transaction_date"])
    inventory_df["week_end_date"] = pd.to_datetime(inventory_df["week_end_date"])

    # ══════════════════════════════════════════════════════════════════
    # 1. CROP → PRODUCT AFFINITY
    # Which products sell most in tehsils where a specific crop is grown?
    # ══════════════════════════════════════════════════════════════════
    logger.info("Computing crop→product affinity from POS + grower locations...")

    # Map growers to their crops and tehsils
    growers_df["crop"] = growers_df["grower_crop_calendar"].apply(parse_crop)
    grower_tehsil_crop = growers_df[["grower_id", "tehsil", "crop"]].dropna()

    # Map retailers to tehsils
    retailer_tehsil = retailers_df[["retailer_id", "tehsil"]].drop_duplicates()

    # Join POS with retailer tehsil
    pos_geo = pos_df.merge(retailer_tehsil, on="retailer_id", how="inner")

    # For each tehsil, find the dominant crop
    tehsil_crop = grower_tehsil_crop.groupby("tehsil")["crop"].agg(
        lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "unknown"
    ).to_dict()

    # Assign crop to each POS transaction via tehsil
    pos_geo["crop"] = pos_geo["tehsil"].map(tehsil_crop).fillna("unknown")

    # Compute crop-product affinity: normalized sales volume per crop
    crop_product_sales = pos_geo.groupby(["crop", "sku_name"])["sku_qty"].sum().reset_index()
    crop_totals = crop_product_sales.groupby("crop")["sku_qty"].sum()

    crop_product_affinity = defaultdict(dict)
    for _, row in crop_product_sales.iterrows():
        crop = row["crop"]
        product = row["sku_name"]
        total = crop_totals.get(crop, 1)
        affinity = row["sku_qty"] / total  # normalized [0, 1]
        crop_product_affinity[crop][product] = round(float(affinity), 4)

    # Normalize to max=1.0 per crop
    for crop in crop_product_affinity:
        max_val = max(crop_product_affinity[crop].values()) if crop_product_affinity[crop] else 1
        for product in crop_product_affinity[crop]:
            crop_product_affinity[crop][product] = round(
                crop_product_affinity[crop][product] / max_val, 4
            )

    logger.info("  Computed affinity for %d crops", len(crop_product_affinity))

    # ══════════════════════════════════════════════════════════════════
    # 2. DISTRICT → PRODUCT POPULARITY
    # Regional purchase preferences
    # ══════════════════════════════════════════════════════════════════
    logger.info("Computing district→product popularity...")

    retailer_district = retailers_df[["retailer_id", "district"]].drop_duplicates()
    pos_district = pos_df.merge(retailer_district, on="retailer_id", how="inner")

    district_product_sales = pos_district.groupby(["district", "sku_name"])["sku_qty"].sum().reset_index()
    district_totals = district_product_sales.groupby("district")["sku_qty"].sum()

    district_product_popularity = defaultdict(dict)
    for _, row in district_product_sales.iterrows():
        district = row["district"]
        product = row["sku_name"]
        total = district_totals.get(district, 1)
        popularity = row["sku_qty"] / total
        district_product_popularity[district][product] = round(float(popularity), 4)

    # Normalize per district
    for district in district_product_popularity:
        max_val = max(district_product_popularity[district].values()) if district_product_popularity[district] else 1
        for product in district_product_popularity[district]:
            district_product_popularity[district][product] = round(
                district_product_popularity[district][product] / max_val, 4
            )

    logger.info("  Computed popularity for %d districts", len(district_product_popularity))

    # ══════════════════════════════════════════════════════════════════
    # 3. PRODUCT AVAILABILITY (latest inventory snapshot)
    # ══════════════════════════════════════════════════════════════════
    logger.info("Computing product availability from latest inventory...")

    # Get latest week's inventory
    latest_week = inventory_df["week_end_date"].max()
    latest_inv = inventory_df[inventory_df["week_end_date"] == latest_week].copy()

    # Join with retailer district
    latest_inv = latest_inv.merge(retailer_district, on="retailer_id", how="inner")

    # Availability = fraction of retailers in district that have stock > 0
    district_avail = latest_inv.groupby(["district", "sku_name"]).apply(
        lambda g: (g["sku_qty"] > 0).mean(), include_groups=False
    ).reset_index(name="availability")

    product_availability = defaultdict(dict)
    for _, row in district_avail.iterrows():
        product_availability[row["district"]][row["sku_name"]] = round(float(row["availability"]), 3)

    # Global availability
    global_avail = latest_inv.groupby("sku_name").apply(
        lambda g: (g["sku_qty"] > 0).mean(), include_groups=False
    ).to_dict()
    product_availability["_global"] = {k: round(float(v), 3) for k, v in global_avail.items()}

    logger.info("  Availability computed for %d districts", len(product_availability) - 1)

    # ══════════════════════════════════════════════════════════════════
    # 4. CROP BESTSELLERS (fallback)
    # ══════════════════════════════════════════════════════════════════
    logger.info("Computing crop bestsellers for fallback...")

    crop_bestsellers = {}
    for crop in crop_product_affinity:
        sorted_products = sorted(
            crop_product_affinity[crop].items(),
            key=lambda x: x[1], reverse=True
        )
        crop_bestsellers[crop] = [p[0] for p in sorted_products[:3]]

    logger.info("  Bestsellers: %s", crop_bestsellers)

    # ══════════════════════════════════════════════════════════════════
    # 5. FIELD REP RECOMMENDATIONS (expert signal)
    # ══════════════════════════════════════════════════════════════════
    logger.info("Computing field rep recommendation frequency...")

    rep_recs = visits_df["product_recommended"].value_counts(normalize=True).to_dict()
    logger.info("  Top rep recommendations: %s", dict(list(rep_recs.items())[:5]))

    # ══════════════════════════════════════════════════════════════════
    # SERIALIZE
    # ══════════════════════════════════════════════════════════════════
    model_payload = {
        "crop_product_affinity": dict(crop_product_affinity),
        "district_product_popularity": dict(district_product_popularity),
        "product_availability": dict(product_availability),
        "crop_bestsellers": crop_bestsellers,
        "rep_recommendations": rep_recs,
        "metadata": {
            "training_date": str(latest_week.date()),
            "pos_transactions": len(pos_df),
            "inventory_snapshot": str(latest_week.date()),
            "districts": len(district_product_popularity),
            "products": len(global_avail),
        },
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(model_payload, f)
    logger.info("Ranker model saved → %s", output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train M8 product ranker")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output", default="ml/ranker_model.pkl")
    args = parser.parse_args()
    train(args.data_dir, args.output)
