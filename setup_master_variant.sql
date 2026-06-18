-- ============ CREATE TABLE master_variant ============
-- Script untuk membuat tabel master_variant di SQL Server
-- Run ini jika table belum ada

-- Check apakah table sudah ada
IF OBJECT_ID('dbo.master_variant', 'U') IS NOT NULL
    DROP TABLE dbo.master_variant;

-- Create table master_variant
CREATE TABLE [dbo].[master_variant] (
    [id_recnum_variant] INT IDENTITY(1,1) PRIMARY KEY,
    [nama_variant] NVARCHAR(100) NOT NULL UNIQUE,
    [image_url] NVARCHAR(255) NULL,
    [status] INT NOT NULL DEFAULT 1,  -- 0 = inactive, 1 = active
    [created_at] DATETIME NULL,
    [updated_at] DATETIME NULL
);

-- Create index untuk query by nama
CREATE NONCLUSTERED INDEX IX_master_variant_nama
ON [dbo].[master_variant] ([nama_variant]);

-- Create index untuk query by status
CREATE NONCLUSTERED INDEX IX_master_variant_status
ON [dbo].[master_variant] ([status]);

-- ============ INSERT DATA AWAL ============

INSERT INTO [dbo].[master_variant] 
([nama_variant], [image_url], [status], [created_at], [updated_at])
VALUES 
('Coklat', NULL, 1, GETDATE(), GETDATE()),
('Strawberry', NULL, 1, GETDATE(), GETDATE()),
('Moca', NULL, 1, GETDATE(), GETDATE()),
('Original (Putih)', NULL, 1, GETDATE(), GETDATE());

-- Verify insert
SELECT * FROM [dbo].[master_variant];
