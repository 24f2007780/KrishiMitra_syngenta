#!/usr/bin/env python3
"""Initialize SQLite and seed farmers/products if tables are empty."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, init_db, ensure_farmer_schema
from app.seeder import seed_farmers, seed_products
from shared.models import Farmer, Product


def main() -> None:
    init_db()
    ensure_farmer_schema()
    db = SessionLocal()
    try:
        farmer_n = db.query(Farmer).count()
        product_n = db.query(Product).count()

        if product_n == 0:
            product_n = seed_products(db)
            print(f"Seeded {product_n} products.")
        else:
            print(f"Products already present: {product_n}")

        if farmer_n == 0:
            farmer_n = seed_farmers(db)
            print(f"Seeded {farmer_n} farmers (CSV or built-in demo set).")
        else:
            print(f"Farmers already present: {farmer_n}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
