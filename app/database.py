import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from shared.models import Base

# Ensure the database is always located in the project root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT_DIR, "master.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    import sqlalchemy.exc
    try:
        Base.metadata.create_all(bind=engine)
    except sqlalchemy.exc.OperationalError as e:
        if "already exists" not in str(e):
            raise
    ensure_farmer_schema()


def ensure_farmer_schema() -> None:
    """
    Migrate legacy SQLite where PK column was ``farmer_id`` → ``grower_id``.
    Safe to call on every startup.
    """
    insp = inspect(engine)
    if not insp.has_table("farmers"):
        return

    columns = {c["name"] for c in insp.get_columns("farmers")}
    if "grower_id" in columns:
        return

    if "farmer_id" not in columns:
        return

    print("Migrating farmers.farmer_id → farmers.grower_id …")
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE farmers RENAME COLUMN farmer_id TO grower_id"))
    print("Migration complete.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
