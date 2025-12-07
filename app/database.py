from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Connect to MySQL
# Format: mysql+driver://user:password@host:port/dbname
# The default value matches your docker-compose environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+mysqlconnector://user:password@db:3306/codereviewdb")

# MySQL requires pool_recycle to prevent connection timeouts
# pool_recycle=3600 recycles connections every hour
engine = create_engine(DATABASE_URL, pool_recycle=3600)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ReviewRecord(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    # MySQL requires a length for String columns used in indexes
    task_id = Column(String(255), unique=True, index=True)
    repo_url = Column(String(500))
    pr_number = Column(Integer)
    status = Column(String(50))
    
    # Use JSON column to store the full analysis result
    ai_result = Column(JSON, nullable=True) 
    
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    """Creates the tables if they don't exist."""
    Base.metadata.create_all(bind=engine)