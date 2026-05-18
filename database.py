from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import urllib

# Ganti dengan password 'sa' kamu yang sebenarnya.
# Format: mssql+pyodbc://username:password@server/database?driver=ODBC+Driver+17+for+SQL+Server
server = r'ADAM123\SQLEXPRESS'
database = 'db_vending_machine' # Sesuaikan dengan nama database aslimu (di screenshot nama db tidak kelihatan utuh, asumsi 'master' atau sesuaikan)
username = 'sa'
password = '07Mei2005'

# Menggunakan OLE DB atau ODBC
# pyodbc connection string
connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
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
