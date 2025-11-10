from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import db_url

engine = create_engine(db_url(), echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

