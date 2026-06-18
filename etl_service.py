import os
import sys

import pandas as pd
from sqlalchemy import text

from database import engine
from PYTHONEnginering.Script_Pipeline_Databuilder import build_v3_exact_features


def run_etl_pipeline():
    """
    Fungsi ini mengambil data dari tabel mentah, memprosesnya sesuai algoritma
    di FIRSTFILE.py, dan memasukkannya ke tabel Vending_Aggregrated.
    Berjalan di background agar tidak memblokir API.
    """
    print("[ETL] Memulai proses ETL di Background...")
    try:
        # --- 1. EXTRACT (Tarik Data) ---
        query_transaksi = """
            SELECT update_time, keterangan, id_recnum_mav, slot_number, qty
            FROM dbo.monitor_log_datatransaksi
            WHERE status_transaksi = '1'
            AND keterangan != 'Proses Restock Qty Oleh Admin'
        """
        df = pd.read_sql(query_transaksi, engine)

        # Tabel Referensi
        query_map_new = (
            "SELECT id_recnum_newslot, slot_number FROM dbo.manage_map_new_slot"
        )
        df_map_new = pd.read_sql(query_map_new, engine)
        map_dict = dict(
            zip(df_map_new["id_recnum_newslot"].astype(str), df_map_new["slot_number"])
        )

        query_map_slot = "SELECT id_recnum_mav, slot_name, id_recnum_variant FROM dbo.manage_map_slot_number"
        df_map_slot = pd.read_sql(query_map_slot, engine)
        df_map_slot["slot_name"] = df_map_slot["slot_name"].astype(str).str.strip()

        query_var = "SELECT id_recnum_variant, nama_variant FROM dbo.master_variant"
        df_var = pd.read_sql(query_var, engine)

        # --- 2. TRANSFORM (Pengolahan Data) ---
        # A. Mapping format angka slot murni
        def perbaiki_slot(val):
            val_str = str(val).strip()
            if val_str.isdigit():
                return map_dict.get(val_str, val_str)
            return val_str

        df["slot_number"] = df["slot_number"].apply(perbaiki_slot)

        # B. Ekstrak Huruf Depan Slot (A1 -> A)
        df["slot_base"] = df["slot_number"].astype(str).str[0]

        # C. Gabungkan untuk cari id_recnum_variant dan nama_variant
        df_step1 = pd.merge(
            df,
            df_map_slot,
            left_on=["id_recnum_mav", "slot_base"],
            right_on=["id_recnum_mav", "slot_name"],
            how="left",
        )
        df_final = pd.merge(df_step1, df_var, on="id_recnum_variant", how="left")

        # D. Hapus data yang rasanya tidak dikenali (mencegah error)
        df_final = df_final.dropna(subset=["nama_variant"])

        # E. Ekstrak Tanggal Saja
        df_final["update_time"] = pd.to_datetime(df_final["update_time"])
        df_final["tanggal"] = df_final["update_time"].dt.date

        # F. Agregasi Harian (Demand = Jumlah transaksi per hari per shift per rasa)
        df_daily = (
            df_final.groupby(["tanggal", "keterangan", "nama_variant"])
            .size()
            .reset_index(name="demand")
        )

        # G. Buat Template Kerangka Waktu Lengkap (Menambal hari kosong)
        all_dates = pd.date_range(
            start=df_final["tanggal"].min(), end=df_final["tanggal"].max()
        ).date
        all_shifts = df_final["keterangan"].unique()
        all_variants = df_final["nama_variant"].unique()

        multi_index = pd.MultiIndex.from_product(
            [all_dates, all_shifts, all_variants],
            names=["tanggal", "keterangan", "nama_variant"],
        )
        df_template = pd.DataFrame(index=multi_index).reset_index()

        # H. Gabungkan data asli ke template
        df_agg = pd.merge(
            df_template,
            df_daily,
            on=["tanggal", "keterangan", "nama_variant"],
            how="left",
        )
        df_agg["demand"] = df_agg["demand"].fillna(0).astype(int)

        # I. Kalkulasi Flag Kalender
        # Menggunakan library holidays.Indonesia() — SAMA PERSIS dengan yang dipakai
        # di vending_daily_FEATUREDFORV6.csv dan Script_Pipeline_Databuilder.py.
        # Sebelumnya ETL mendefinisikan is_holiday sebagai "hari tanpa transaksi",
        # yang menyebabkan mismatch dengan standalone script dan Layer 2 distribution.
        import holidays as pyholidays
        import datetime as _dt

        # Ambil range tahun dari data
        _years = sorted(set(pd.to_datetime(df_agg["tanggal"]).dt.year.unique()))
        id_holidays = pyholidays.Indonesia(years=_years, categories=(pyholidays.PUBLIC,))
        holidays_set = set(id_holidays.keys())

        # Tambahkan hari libur yang tidak terdeteksi library (sama dengan Databuilder)
        EXTRA_HOLIDAYS = {
            _dt.date(2025, 12, 25),  # Natal — tidak selalu terdeteksi pyholidays.PUBLIC
        }
        holidays_set = holidays_set | EXTRA_HOLIDAYS

        # Daftar periode Ramadan (sama dengan Databuilder)
        RAMADAN_PERIODS = [
            ("2023-03-22", "2023-04-21"),
            ("2024-03-11", "2024-04-09"),
            ("2025-02-28", "2025-03-30"),
            ("2026-02-17", "2026-03-18"),
        ]

        df_agg["tanggal_dt"] = pd.to_datetime(df_agg["tanggal"])

        # is_holiday: berdasarkan kalender resmi Indonesia
        df_agg["is_holiday"] = df_agg["tanggal_dt"].dt.date.isin(holidays_set).astype(int)

        # is_weekend: Sabtu/Minggu
        df_agg["is_weekend"] = (df_agg["tanggal_dt"].dt.dayofweek >= 5).astype(int)

        # is_ramadan: berdasarkan daftar periode Ramadan
        def _is_ramadan(d):
            for start, end in RAMADAN_PERIODS:
                if pd.Timestamp(start) <= d <= pd.Timestamp(end):
                    return 1
            return 0

        df_agg["is_ramadan"] = df_agg["tanggal_dt"].apply(_is_ramadan)

        # Cleanup kolom sementara
        df_agg.drop(columns=["tanggal_dt"], inplace=True)

        # J. Tandai semua baris sebagai data sistem (bukan input manual)
        # is_manual_insert = 0  → data berasal dari monitor_log_datatransaksi (pipeline ini)
        # is_manual_insert = 1  → data diinput manual oleh admin (dikelola di luar pipeline ini)
        df_agg["is_manual_insert"] = 0

        # --- 3. LOAD (Simpan ke Tabel B) ---
        # PENTING: Jangan TRUNCATE — hanya hapus baris sistem (is_manual_insert = 0)
        # agar data yang diinput manual (is_manual_insert = 1) tetap aman.
        with engine.begin() as conn:
            deleted = conn.execute(
                text("DELETE FROM dbo.Vending_Aggregrated WHERE is_manual_insert = 0")
            )
            print(
                f"  [ETL] {deleted.rowcount} baris sistem lama dihapus (data manual tetap aman)."
            )

        # Simpan ke tabel — hanya kolom yang sesuai skema target
        kolom_target = [
            "tanggal",
            "keterangan",
            "nama_variant",
            "demand",
            "is_holiday",
            "is_ramadan",
            "is_weekend",
            "is_manual_insert",
        ]
        # Sort by tanggal, keterangan, nama_variant sebelum insert agar tabel rapi kronologis
        df_agg_sorted = df_agg[kolom_target].sort_values(
            by=["tanggal", "keterangan", "nama_variant"]
        ).reset_index(drop=True)
        df_agg_sorted.to_sql(
            "Vending_Aggregrated", engine, if_exists="append", index=False, schema="dbo"
        )

        print(
            f"[ETL] Proses ETL Selesai! {len(df_agg)} baris sistem berhasil dimasukkan ke tabel Vending_Aggregrated."
        )

        # --- 4. EKSEKUSI ML FEATURE ENGINEERING (SQL-Based) ---
        print(
            "\n[ETL Step 4] Membentuk fitur ML dari data Vending_Aggregrated (SQL)..."
        )

        # Baca langsung dari SQL (bukan CSV) — sesuai blueprint SQL-First
        df_from_sql = pd.read_sql("SELECT * FROM dbo.Vending_Aggregrated", engine)

        # Simpan ke CSV temp hanya sebagai jembatan ke fungsi build_v3_exact_features
        # (fungsi ini masih menerima path CSV sebagai input/output)
        temp_input = "temp_etl_input.csv"
        temp_output = "temp_etl_output.csv"
        df_from_sql.to_csv(temp_input, index=False)

        build_v3_exact_features(temp_input, temp_output)

        df_ml = pd.read_csv(temp_output)

        # --- 5. LOAD KE TABEL ML (SQL-Based) ---
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE dbo.vending_training_ml"))
        # Sort by variant, period sebelum insert agar tabel ML rapi kronologis
        df_ml_sorted = df_ml.sort_values(
            by=["variant", "period"]
        ).reset_index(drop=True)
        df_ml_sorted.to_sql(
            "vending_training_ml", engine, if_exists="append", index=False, schema="dbo"
        )

        print(
            f"[ETL Step 5] ML Pipeline Selesai! {len(df_ml)} baris -> dbo.vending_training_ml"
        )

        # Bersihkan file sementara
        for f in [temp_input, temp_output]:
            if os.path.exists(f):
                os.remove(f)

    except Exception as e:
        print(f"[ETL ERROR] {e}")
        import traceback

        traceback.print_exc()
