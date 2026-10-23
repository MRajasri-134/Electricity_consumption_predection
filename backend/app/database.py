import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:Rajasri39@127.0.0.1:3306/powerpredict"
)

connect_args = {}

if os.getenv("DATABASE_URL"):
    connect_args["ssl"] = {
        "ca": os.path.join(os.path.dirname(os.path.dirname(__file__)), "ca.pem")
    }

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args=connect_args
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
