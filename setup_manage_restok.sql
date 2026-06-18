-- ============ CREATE TABLE manage_restok ============
-- Script untuk membuat tabel manage_restok di SQL Server
-- Table ini menyimpan stok per slot untuk setiap vending machine

-- Check apakah table sudah ada
IF OBJECT_ID('dbo.manage_restok', 'U') IS NOT NULL
    DROP TABLE dbo.manage_restok;

-- Create table manage_restok
CREATE TABLE [dbo].[manage_restok] (
    [id_recnum_mrs] INT IDENTITY(10534,1) PRIMARY KEY,
    [id_recnum_mav] INT NOT NULL,  -- FK ke master_alat_vm (vending machine)
    [stok_qty] INT NOT NULL DEFAULT 0,  -- Jumlah stok di slot
    [status_restok] INT NOT NULL DEFAULT 1,  -- 0 = inactive, 1 = active
    [update_time] DATETIME NULL DEFAULT GETDATE(),
    [user_input] NVARCHAR(100) NOT NULL DEFAULT 'admin',  -- Siapa yang update
    [slot_number] NVARCHAR(10) NOT NULL  -- Slot number (A1, A2, B1, dll)
);

-- Create index untuk query by VM
CREATE NONCLUSTERED INDEX IX_manage_restok_vm
ON [dbo].[manage_restok] ([id_recnum_mav]);

-- Create index untuk query by slot
CREATE NONCLUSTERED INDEX IX_manage_restok_slot
ON [dbo].[manage_restok] ([id_recnum_mav], [slot_number]);

-- Create index untuk query by status
CREATE NONCLUSTERED INDEX IX_manage_restok_status
ON [dbo].[manage_restok] ([status_restok]);

-- Create index untuk alert stok rendah
CREATE NONCLUSTERED INDEX IX_manage_restok_low_stock
ON [dbo].[manage_restok] ([stok_qty], [status_restok]);

-- ============ INSERT DATA AWAL ============
-- Contoh data untuk VM ID 1 dengan 4 slot (A, B, C, D)

INSERT INTO [dbo].[manage_restok] 
([id_recnum_mav], [stok_qty], [status_restok], [update_time], [user_input], [slot_number])
VALUES 
(1, 0, 1, GETDATE(), 'admin', 'A1'),
(1, 0, 1, GETDATE(), 'admin', 'A2'),
(1, 0, 1, GETDATE(), 'admin', 'A3'),
(1, 0, 1, GETDATE(), 'admin', 'B1'),
(1, 0, 1, GETDATE(), 'admin', 'B2'),
(1, 0, 1, GETDATE(), 'admin', 'B3'),
(1, 0, 1, GETDATE(), 'admin', 'C1'),
(1, 0, 1, GETDATE(), 'admin', 'C2'),
(1, 0, 1, GETDATE(), 'admin', 'C3'),
(1, 0, 1, GETDATE(), 'admin', 'D1'),
(1, 0, 1, GETDATE(), 'admin', 'D2'),
(1, 0, 1, GETDATE(), 'admin', 'D3');

-- Verify insert
SELECT * FROM [dbo].[manage_restok];
