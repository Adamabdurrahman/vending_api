"""
setup_forecast_tables.py
================================================================================
Script untuk menjalankan Step 1A, 1B, 1C dari Implementation Plan:
  1A. CREATE TABLE ForecastResults_Layer1
  1B. CREATE TABLE ForecastResults_Layer2
  1C. Verifikasi tabel OperationalCalendar sudah ada dan terisi
================================================================================
"""

from sqlalchemy import text

from database import engine


def run_setup():
    print("=" * 70)
    print("SETUP TABEL OUTPUT FORECASTING - Step 1A, 1B, 1C")
    print("=" * 70)

    with engine.begin() as conn:
        # ==============================================================
        # STEP 1A: CREATE TABLE ForecastResults_Layer1
        # ==============================================================
        print("\n[Step 1A] Membuat tabel ForecastResults_Layer1...")

        exists_l1 = conn.execute(
            text("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'ForecastResults_Layer1'
        """)
        ).scalar()

        if exists_l1 > 0:
            print("  [INFO] Tabel ForecastResults_Layer1 SUDAH ADA - skip CREATE.")
        else:
            conn.execute(
                text("""
                CREATE TABLE [dbo].[ForecastResults_Layer1] (
                    Id                  INT IDENTITY(1,1) PRIMARY KEY,
                    PredictedMonth      VARCHAR(7) NOT NULL,
                    RunTimestamp        DATETIME NOT NULL,
                    ModelVersion        VARCHAR(20),

                    TotalDemand         INT NOT NULL,
                    DemandCoklat        INT,
                    DemandMoca          INT,
                    DemandOriginal      INT,
                    DemandStrawberry    INT,
                    IsBusinessLogic     BIT DEFAULT 0,
                    ProductiveDays      FLOAT,

                    MAPE_Total          FLOAT,
                    MAE_Total           FLOAT,
                    RMSE_Total          FLOAT,
                    MAPE_Coklat         FLOAT,
                    MAPE_Moca           FLOAT,
                    MAPE_Original       FLOAT,
                    MAPE_Strawberry     FLOAT,
                    SmootherEnabled     BIT DEFAULT 1,

                    ActualDemand        INT NULL,
                    ErrorPercent        FLOAT NULL,
                    ActualUpdatedAt     DATETIME NULL,

                    PatchLogJson        NVARCHAR(MAX) NULL
                )
            """)
            )
            print("  [OK] Tabel ForecastResults_Layer1 berhasil dibuat!")

        # ==============================================================
        # STEP 1B: CREATE TABLE ForecastResults_Layer2
        # ==============================================================
        print("\n[Step 1B] Membuat tabel ForecastResults_Layer2...")

        exists_l2 = conn.execute(
            text("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'ForecastResults_Layer2'
        """)
        ).scalar()

        if exists_l2 > 0:
            print("  [INFO] Tabel ForecastResults_Layer2 SUDAH ADA - skip CREATE.")
        else:
            conn.execute(
                text("""
                CREATE TABLE [dbo].[ForecastResults_Layer2] (
                    Id                  INT IDENTITY(1,1) PRIMARY KEY,
                    RunTimestamp        DATETIME NOT NULL,
                    PredictedMonth      VARCHAR(7) NOT NULL,
                    [Date]              DATE NOT NULL,
                    DayName             VARCHAR(10),
                    Shift               VARCHAR(30) NOT NULL,
                    Variant             VARCHAR(30) NOT NULL,
                    PredictedDemand     INT NOT NULL,
                    IsHoliday           BIT DEFAULT 0,
                    IsRamadan           BIT DEFAULT 0,
                    IsWeekend           BIT DEFAULT 0,

                    ActualDemand        INT NULL,
                    ErrorPercent        FLOAT NULL
                )
            """)
            )
            conn.execute(
                text("""
                CREATE NONCLUSTERED INDEX IX_Layer2_DateShiftVariant
                ON [dbo].[ForecastResults_Layer2] ([Date], Shift, Variant)
            """)
            )
            print("  [OK] Tabel ForecastResults_Layer2 berhasil dibuat (+ index)!")

        # ==============================================================
        # STEP 1C: Verifikasi tabel OperationalCalendar
        # ==============================================================
        print("\n[Step 1C] Memverifikasi tabel OperationalCalendar...")

        exists_oc = conn.execute(
            text("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'OperationalCalendar'
        """)
        ).scalar()

        if exists_oc == 0:
            print("  [FAIL] Tabel OperationalCalendar BELUM ADA!")
            print("     Kamu perlu membuatnya dan mengisinya terlebih dahulu.")
            print("     Jalankan Script_SqlCalendar.py untuk setup.")
        else:
            print("  [OK] Tabel OperationalCalendar ditemukan!")

            total_rows = conn.execute(
                text("SELECT COUNT(*) FROM dbo.OperationalCalendar")
            ).scalar()
            print(f"     Total baris: {total_rows}")

            years = conn.execute(
                text("""
                SELECT DISTINCT YEAR([Date]) AS yr
                FROM dbo.OperationalCalendar
                ORDER BY yr
            """)
            ).fetchall()
            year_list = [str(r[0]) for r in years]
            print(f"     Tahun tersedia: {', '.join(year_list)}")

            has_2026 = "2026" in year_list
            if has_2026:
                count_2026 = conn.execute(
                    text("""
                    SELECT COUNT(*) FROM dbo.OperationalCalendar
                    WHERE YEAR([Date]) = 2026
                """)
                ).scalar()
                print(f"     Data 2026: {count_2026} baris [OK]")
            else:
                print("     [WARN] Data tahun 2026 BELUM ADA di OperationalCalendar!")
                print(
                    "       Jalankan Script_SqlCalendar.py untuk mengisi kalender 2026."
                )

            has_ramadan = conn.execute(
                text("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'OperationalCalendar'
                  AND COLUMN_NAME = 'IsRamadan'
            """)
            ).scalar()

            if has_ramadan > 0:
                ramadan_count = conn.execute(
                    text("""
                    SELECT COUNT(*) FROM dbo.OperationalCalendar
                    WHERE IsRamadan = 1
                """)
                ).scalar()
                print(
                    f"     Kolom IsRamadan: Ada [OK] ({ramadan_count} hari ditandai Ramadan)"
                )
            else:
                print("     [WARN] Kolom IsRamadan BELUM ADA!")
                print("       Jalankan: update_ramadan_flags(engine, year=2026)")

            print("\n     Kolom yang tersedia:")
            columns = conn.execute(
                text("""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'OperationalCalendar'
                ORDER BY ORDINAL_POSITION
            """)
            ).fetchall()
            for col_name, data_type in columns:
                print(f"       - {col_name} ({data_type})")

        # ==============================================================
        # STEP 1D: CREATE TABLE RetrainLog
        # ==============================================================
        print("\n[Step 1D] Membuat tabel RetrainLog...")

        exists_rl = conn.execute(
            text("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'RetrainLog'
        """)
        ).scalar()

        if exists_rl > 0:
            print("  [INFO] Tabel RetrainLog SUDAH ADA - skip CREATE.")
        else:
            conn.execute(
                text("""
                CREATE TABLE [dbo].[RetrainLog] (
                    Id                  INT IDENTITY(1,1) PRIMARY KEY,
                    RunTimestamp        DATETIME NOT NULL,
                    ModelVersion        VARCHAR(50),
                    MAPE                FLOAT,
                    MAE                 FLOAT,
                    RMSE                FLOAT,
                    TrainingRows        INT,
                    TrainingPeriodEnd   VARCHAR(7),
                    BestParams          NVARCHAR(500),
                    Status              VARCHAR(20)
                )
            """)
            )
            print("  [OK] Tabel RetrainLog berhasil dibuat!")

        # ==============================================================
        # STEP 1E: CREATE TABLE SystemNotifications
        # ==============================================================
        print("\n[Step 1E] Membuat tabel SystemNotifications...")

        exists_sn = conn.execute(
            text("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'SystemNotifications'
        """)
        ).scalar()

        if exists_sn > 0:
            print("  [INFO] Tabel SystemNotifications SUDAH ADA - skip CREATE.")
        else:
            conn.execute(
                text("""
                CREATE TABLE [dbo].[SystemNotifications] (
                    Id              INT IDENTITY(1,1) PRIMARY KEY,
                    CreatedAt       DATETIME NOT NULL DEFAULT GETDATE(),
                    NotifType       VARCHAR(30)  NOT NULL,
                    Severity        VARCHAR(10)  NOT NULL,
                    Title           VARCHAR(200) NOT NULL,
                    Message         NVARCHAR(MAX),
                    IsRead          BIT NOT NULL DEFAULT 0,
                    RelatedMonth    VARCHAR(7)  NULL,
                    RelatedQuarter  VARCHAR(10) NULL
                )
            """)
            )
            print("  [OK] Tabel SystemNotifications berhasil dibuat!")

        # ==============================================================
        # STEP 1F: ALTER ForecastResults_Layer1 — tambah kolom baru
        # ==============================================================
        print(
            "\n[Step 1F] Cek kolom is_data_gap & is_retrained di ForecastResults_Layer1..."
        )

        for col_name, col_def in [
            ("is_data_gap", "BIT NOT NULL DEFAULT 0"),
            ("is_retrained", "BIT NOT NULL DEFAULT 0"),
        ]:
            exists_col = conn.execute(
                text("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'ForecastResults_Layer1'
                  AND COLUMN_NAME = :col
            """),
                {"col": col_name},
            ).scalar()

            if exists_col > 0:
                print(f"  [INFO] Kolom {col_name} SUDAH ADA - skip.")
            else:
                conn.execute(
                    text(
                        f"ALTER TABLE [dbo].[ForecastResults_Layer1] ADD [{col_name}] {col_def}"
                    )
                )
                print(f"  [OK] Kolom {col_name} berhasil ditambahkan!")

    # ==============================================================
    # RINGKASAN AKHIR
    # ==============================================================
    print("\n" + "=" * 70)
    print("RINGKASAN SETUP:")
    print("=" * 70)

    with engine.connect() as conn:
        tables = [
            "ForecastResults_Layer1",
            "ForecastResults_Layer2",
            "OperationalCalendar",
            "RetrainLog",
        ]
        for t in tables:
            exists = conn.execute(
                text(f"""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{t}'
            """)
            ).scalar()
            status = "[OK]  " if exists > 0 else "[FAIL]"
            print(f"  {status} dbo.{t}")

    print("\nSetup selesai! Lanjut ke Fase 2 (Refactor Script -> SQL-Based).")
    print("=" * 70)


if __name__ == "__main__":
    run_setup()
