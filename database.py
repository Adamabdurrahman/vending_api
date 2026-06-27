from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings
import urllib
import os
from dotenv import load_dotenv

load_dotenv()

# Baca konfigurasi database dari file .env
# Salin .env.example ke .env dan isi dengan nilai yang sesuai
server   = os.getenv("DB_SERVER",   r"YOURPC\SQLEXPRESS")
database = os.getenv("DB_NAME",     "db_vending_machine")
username = os.getenv("DB_USERNAME", "sa")
password = os.getenv("DB_PASSWORD", "")

connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password}"
)
params = urllib.parse.quote_plus(connection_string)

SQLALCHEMY_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params}"

# Create the engine
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)

# Create a scoped session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for declarative models
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
