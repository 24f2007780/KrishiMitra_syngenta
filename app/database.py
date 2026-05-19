import os
from sqlalchemy import create_engine
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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
