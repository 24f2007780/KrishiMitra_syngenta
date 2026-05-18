from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.models import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./master.db"

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
