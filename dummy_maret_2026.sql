-- ============================================================
-- dummy_maret_2026.sql (v2 - demand dikoreksi ke ~3000/hari)
-- Data aktual dummy untuk 30-31 Maret 2026 (Ramadan terakhir)
-- Format: 8 shift x 4 variant = 32 baris per hari = 64 baris total
-- is_manual_insert = 1  ->  TIDAK akan dihapus oleh ETL harian
--
-- Dasar nilai demand:
--   Jan 2026 rata-rata = 78,332 / 31 hari = ~2,527/hari
--   Target dummy: ~3,000/hari (normal productive day)
--   Proporsi shift  -> dari pola Jan 2026
--   Proporsi variant -> Coklat ~52%, Moca ~16%, Putih ~18%, Strawberry ~14%
--   Grand total 2 hari: 2,988 + 3,086 = 6,074 unit
--   (Konsisten dengan prediksi Layer 1: 6,180 unit)
-- ============================================================

BEGIN TRANSACTION;

-- STEP 1: Hapus data dummy lama yang formatnya salah
DELETE FROM dbo.Vending_Aggregrated
WHERE YEAR(tanggal) = 2026 AND MONTH(tanggal) = 3;

PRINT 'Data dummy lama Maret 2026 dihapus.';

-- ============================================================
-- STEP 2: Insert 30 Maret 2026  (~2,988 unit)
-- ============================================================
INSERT INTO dbo.Vending_Aggregrated
    (tanggal, keterangan, nama_variant, demand, is_holiday, is_ramadan, is_weekend, is_manual_insert)
VALUES
-- SHIFT1 - AKHIR  (~30% dari total)  = 900 unit
('2026-03-30', 'SHIFT1 - AKHIR', 'Coklat',             468, 0, 0, 0, 1),
('2026-03-30', 'SHIFT1 - AKHIR', 'Moca',               144, 0, 0, 0, 1),
('2026-03-30', 'SHIFT1 - AKHIR', 'Original (Putih)',   162, 0, 0, 0, 1),
('2026-03-30', 'SHIFT1 - AKHIR', 'Strawberry',          126, 0, 0, 0, 1),
-- SHIFT1 - AWAL   (~31.5%)           = 945 unit
('2026-03-30', 'SHIFT1 - AWAL',  'Coklat',             491, 0, 0, 0, 1),
('2026-03-30', 'SHIFT1 - AWAL',  'Moca',               151, 0, 0, 0, 1),
('2026-03-30', 'SHIFT1 - AWAL',  'Original (Putih)',   170, 0, 0, 0, 1),
('2026-03-30', 'SHIFT1 - AWAL',  'Strawberry',          133, 0, 0, 0, 1),
-- SHIFT2 - AKHIR  (~15.7%)           = 471 unit
('2026-03-30', 'SHIFT2 - AKHIR', 'Coklat',             245, 0, 0, 0, 1),
('2026-03-30', 'SHIFT2 - AKHIR', 'Moca',                75, 0, 0, 0, 1),
('2026-03-30', 'SHIFT2 - AKHIR', 'Original (Putih)',    85, 0, 0, 0, 1),
('2026-03-30', 'SHIFT2 - AKHIR', 'Strawberry',           66, 0, 0, 0, 1),
-- SHIFT2 - AWAL   (~5.2%)            = 156 unit
('2026-03-30', 'SHIFT2 - AWAL',  'Coklat',              81, 0, 0, 0, 1),
('2026-03-30', 'SHIFT2 - AWAL',  'Moca',                25, 0, 0, 0, 1),
('2026-03-30', 'SHIFT2 - AWAL',  'Original (Putih)',    28, 0, 0, 0, 1),
('2026-03-30', 'SHIFT2 - AWAL',  'Strawberry',           22, 0, 0, 0, 1),
-- SHIFT3 - AKHIR  (~4.1%)            = 123 unit
('2026-03-30', 'SHIFT3 - AKHIR', 'Coklat',              64, 0, 0, 0, 1),
('2026-03-30', 'SHIFT3 - AKHIR', 'Moca',                20, 0, 0, 0, 1),
('2026-03-30', 'SHIFT3 - AKHIR', 'Original (Putih)',    22, 0, 0, 0, 1),
('2026-03-30', 'SHIFT3 - AKHIR', 'Strawberry',           17, 0, 0, 0, 1),
-- SHIFT3 - AWAL   (~4.1%)            = 123 unit
('2026-03-30', 'SHIFT3 - AWAL',  'Coklat',              64, 0, 0, 0, 1),
('2026-03-30', 'SHIFT3 - AWAL',  'Moca',                20, 0, 0, 0, 1),
('2026-03-30', 'SHIFT3 - AWAL',  'Original (Putih)',    22, 0, 0, 0, 1),
('2026-03-30', 'SHIFT3 - AWAL',  'Strawberry',           17, 0, 0, 0, 1),
-- SHIFTPUTIH - AKHIR (~2.6%)         = 78 unit
('2026-03-30', 'SHIFTPUTIH - AKHIR', 'Coklat',           41, 0, 0, 0, 1),
('2026-03-30', 'SHIFTPUTIH - AKHIR', 'Moca',             12, 0, 0, 0, 1),
('2026-03-30', 'SHIFTPUTIH - AKHIR', 'Original (Putih)', 14, 0, 0, 0, 1),
('2026-03-30', 'SHIFTPUTIH - AKHIR', 'Strawberry',        11, 0, 0, 0, 1),
-- SHIFTPUTIH - AWAL  (~6.4%)         = 192 unit
('2026-03-30', 'SHIFTPUTIH - AWAL',  'Coklat',           100, 0, 0, 0, 1),
('2026-03-30', 'SHIFTPUTIH - AWAL',  'Moca',              31, 0, 0, 0, 1),
('2026-03-30', 'SHIFTPUTIH - AWAL',  'Original (Putih)',  35, 0, 0, 0, 1),
('2026-03-30', 'SHIFTPUTIH - AWAL',  'Strawberry',         26, 0, 0, 0, 1);
-- Total 30 Mar: 900+945+471+156+123+123+78+192 = 2,988 unit

PRINT '30 Maret 2026: 32 baris diinsert (~2,988 unit)';

-- ============================================================
-- STEP 3: Insert 31 Maret 2026  (~3,086 unit)
-- Sedikit lebih tinggi - hari terakhir sebelum shutdown Lebaran
-- ============================================================
INSERT INTO dbo.Vending_Aggregrated
    (tanggal, keterangan, nama_variant, demand, is_holiday, is_ramadan, is_weekend, is_manual_insert)
VALUES
-- SHIFT1 - AKHIR  = 932 unit
('2026-03-31', 'SHIFT1 - AKHIR', 'Coklat',             485, 0, 0, 0, 1),
('2026-03-31', 'SHIFT1 - AKHIR', 'Moca',               149, 0, 0, 0, 1),
('2026-03-31', 'SHIFT1 - AKHIR', 'Original (Putih)',   168, 0, 0, 0, 1),
('2026-03-31', 'SHIFT1 - AKHIR', 'Strawberry',          130, 0, 0, 0, 1),
-- SHIFT1 - AWAL   = 972 unit
('2026-03-31', 'SHIFT1 - AWAL',  'Coklat',             505, 0, 0, 0, 1),
('2026-03-31', 'SHIFT1 - AWAL',  'Moca',               155, 0, 0, 0, 1),
('2026-03-31', 'SHIFT1 - AWAL',  'Original (Putih)',   175, 0, 0, 0, 1),
('2026-03-31', 'SHIFT1 - AWAL',  'Strawberry',          137, 0, 0, 0, 1),
-- SHIFT2 - AKHIR  = 486 unit
('2026-03-31', 'SHIFT2 - AKHIR', 'Coklat',             252, 0, 0, 0, 1),
('2026-03-31', 'SHIFT2 - AKHIR', 'Moca',                78, 0, 0, 0, 1),
('2026-03-31', 'SHIFT2 - AKHIR', 'Original (Putih)',    88, 0, 0, 0, 1),
('2026-03-31', 'SHIFT2 - AKHIR', 'Strawberry',           68, 0, 0, 0, 1),
-- SHIFT2 - AWAL   = 160 unit
('2026-03-31', 'SHIFT2 - AWAL',  'Coklat',              83, 0, 0, 0, 1),
('2026-03-31', 'SHIFT2 - AWAL',  'Moca',                26, 0, 0, 0, 1),
('2026-03-31', 'SHIFT2 - AWAL',  'Original (Putih)',    29, 0, 0, 0, 1),
('2026-03-31', 'SHIFT2 - AWAL',  'Strawberry',           22, 0, 0, 0, 1),
-- SHIFT3 - AKHIR  = 128 unit
('2026-03-31', 'SHIFT3 - AKHIR', 'Coklat',              66, 0, 0, 0, 1),
('2026-03-31', 'SHIFT3 - AKHIR', 'Moca',                21, 0, 0, 0, 1),
('2026-03-31', 'SHIFT3 - AKHIR', 'Original (Putih)',    23, 0, 0, 0, 1),
('2026-03-31', 'SHIFT3 - AKHIR', 'Strawberry',           18, 0, 0, 0, 1),
-- SHIFT3 - AWAL   = 128 unit
('2026-03-31', 'SHIFT3 - AWAL',  'Coklat',              66, 0, 0, 0, 1),
('2026-03-31', 'SHIFT3 - AWAL',  'Moca',                21, 0, 0, 0, 1),
('2026-03-31', 'SHIFT3 - AWAL',  'Original (Putih)',    23, 0, 0, 0, 1),
('2026-03-31', 'SHIFT3 - AWAL',  'Strawberry',           18, 0, 0, 0, 1),
-- SHIFTPUTIH - AKHIR = 82 unit
('2026-03-31', 'SHIFTPUTIH - AKHIR', 'Coklat',           43, 0, 0, 0, 1),
('2026-03-31', 'SHIFTPUTIH - AKHIR', 'Moca',             13, 0, 0, 0, 1),
('2026-03-31', 'SHIFTPUTIH - AKHIR', 'Original (Putih)', 15, 0, 0, 0, 1),
('2026-03-31', 'SHIFTPUTIH - AKHIR', 'Strawberry',        11, 0, 0, 0, 1),
-- SHIFTPUTIH - AWAL  = 198 unit
('2026-03-31', 'SHIFTPUTIH - AWAL',  'Coklat',           103, 0, 0, 0, 1),
('2026-03-31', 'SHIFTPUTIH - AWAL',  'Moca',              32, 0, 0, 0, 1),
('2026-03-31', 'SHIFTPUTIH - AWAL',  'Original (Putih)',  36, 0, 0, 0, 1),
('2026-03-31', 'SHIFTPUTIH - AWAL',  'Strawberry',         27, 0, 0, 0, 1);
-- Total 31 Mar: 932+972+486+160+128+128+82+198 = 3,086 unit

PRINT '31 Maret 2026: 32 baris diinsert (~3,086 unit)';

-- ============================================================
-- STEP 4: Verifikasi hasil
-- ============================================================
SELECT
    CAST(tanggal AS DATE)        AS tanggal,
    COUNT(*)                     AS jumlah_baris,
    SUM(demand)                  AS total_demand_per_hari
FROM dbo.Vending_Aggregrated
WHERE YEAR(tanggal) = 2026 AND MONTH(tanggal) = 3
GROUP BY CAST(tanggal AS DATE)
ORDER BY tanggal;

SELECT
    nama_variant,
    SUM(demand) AS total_per_variant
FROM dbo.Vending_Aggregrated
WHERE YEAR(tanggal) = 2026 AND MONTH(tanggal) = 3
GROUP BY nama_variant
ORDER BY total_per_variant DESC;

SELECT SUM(demand) AS grand_total_maret FROM dbo.Vending_Aggregrated
WHERE YEAR(tanggal) = 2026 AND MONTH(tanggal) = 3;

COMMIT TRANSACTION;
PRINT 'Selesai. Grand total Maret 2026 = ~6,074 unit (2,988 + 3,086).';
