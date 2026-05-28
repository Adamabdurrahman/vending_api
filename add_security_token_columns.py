import sqlalchemy
from sqlalchemy import text
from database import engine

def migrate():
    print("Starting migration to add security_token and token_expiry to dbo.master_user...")
    
    with engine.connect() as conn:
        # Cek apakah kolom security_token sudah ada
        check_token_sql = text("""
            IF NOT EXISTS (
                SELECT * FROM sys.columns 
                WHERE object_id = OBJECT_ID(N'[dbo].[master_user]') 
                AND name = 'security_token'
            )
            BEGIN
                ALTER TABLE [dbo].[master_user] ADD [security_token] VARCHAR(100) NULL;
                SELECT 'Column security_token added' as result;
            END
            ELSE
            BEGIN
                SELECT 'Column security_token already exists' as result;
            END
        """)
        
        # Cek apakah kolom token_expiry sudah ada
        check_expiry_sql = text("""
            IF NOT EXISTS (
                SELECT * FROM sys.columns 
                WHERE object_id = OBJECT_ID(N'[dbo].[master_user]') 
                AND name = 'token_expiry'
            )
            BEGIN
                ALTER TABLE [dbo].[master_user] ADD [token_expiry] DATETIME NULL;
                SELECT 'Column token_expiry added' as result;
            END
            ELSE
            BEGIN
                SELECT 'Column token_expiry already exists' as result;
            END
        """)
        
        # Eksekusi migrasi dalam transaksi
        trans = conn.begin()
        try:
            res_token = conn.execute(check_token_sql).scalar()
            print(f"Security Token Column Check: {res_token}")
            
            res_expiry = conn.execute(check_expiry_sql).scalar()
            print(f"Token Expiry Column Check: {res_expiry}")
            
            trans.commit()
            print("Migration completed successfully!")
        except Exception as e:
            trans.rollback()
            print(f"Error occurred during migration: {e}")

if __name__ == "__main__":
    migrate()
