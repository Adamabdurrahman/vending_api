import sqlalchemy
from sqlalchemy import text
from database import engine

def migrate():
    print("Altering approve_by column to VARCHAR(100) to support longer admin IDs...")
    
    with engine.connect() as conn:
        alter_sql = text("""
            ALTER TABLE [dbo].[master_user] ALTER COLUMN [approve_by] VARCHAR(100) NULL;
        """)
        
        trans = conn.begin()
        try:
            conn.execute(alter_sql)
            trans.commit()
            print("Alter table completed successfully!")
        except Exception as e:
            trans.rollback()
            print(f"Error occurred during column alter: {e}")

if __name__ == "__main__":
    migrate()
