1. Manage Variant

SELECT TOP 1000 [id_recnum_variant]
      ,[nama_variant]
      ,[url_image]
      ,[status_variant]
  FROM [db_vending_machine].[dbo].[master_variant]

id_recnum_variant	nama_variant	url_image	status_variant
1	Original (Putih)	NULL	1
2	Coklat	NULL	1
3	Strawberry	NULL	1
5	Moca	NULL	1

2. Manage Restock

SELECT TOP 1000 [id_recnum_mrs]
      ,[id_recnum_mav]
      ,[stok_qty]
      ,[status_restok]
      ,[update_time]
      ,[user_input]
      ,[slot_number]
  FROM [db_vending_machine].[dbo].[manage_restok]

id_recnum_mrs	id_recnum_mav	stok_qty	status_restok	update_time	user_input	slot_number
10534	1	0	1	2024-08-13 19:44:30.333	admin	A1
10535	1	0	1	2024-08-13 19:44:30.337	admin	A2
10536	1	0	1	2024-08-13 19:44:30.337	admin	A3

3. Slot Number

/****** Script for SelectTopNRows command from SSMS  ******/
SELECT TOP 1000 [id_recnum_msn]
      ,[id_recnum_mav]
      ,[slot_name]
      ,[slot_number_max]
      ,[update_time]
      ,[user_input]
      ,[id_recnum_variant]
  FROM [db_vending_machine].[dbo].[manage_map_slot_number]

id_recnum_msn	id_recnum_mav	slot_name	slot_number_max	update_time	user_input	id_recnum_variant
2	1	B	10	2025-07-18 09:58:34.687	admin	2
3	1	C	10	2025-12-19 10:33:08.740	admin	1
4	1	D	6	2025-11-09 23:10:42.490	admin	3

4. Manage Alat VM

SELECT TOP 1000 [id_recnum_mav]
      ,[nama_vm]
      ,[no_ref]
      ,[update_time]
      ,[user_input]
      ,[ip_address]
  FROM [db_vending_machine].[dbo].[master_alat_vm]

id_recnum_mav	nama_vm	no_ref	update_time	user_input	ip_address
1	Vending Machine 01 OFFICE	Zona Simulasi 1 (DevMode) http://localhost:8080/trigger/	2024-09-02 11:47:55.380	admin	192.168.1.1

5. Manage Shift

/****** Script for SelectTopNRows command from SSMS  ******/
SELECT TOP 1000 [id_recnum_mst]
      ,[nama_shift]
      ,[nama_bagian]
      ,[jam_mulai]
      ,[jam_akhir]
      ,[status_active]
      ,[update_time]
      ,[user_input]
  FROM [db_vending_machine].[dbo].[master_settime]

id_recnum_mst	nama_shift	nama_bagian	jam_mulai	jam_akhir	status_active	update_time	user_input
1	Shift 1	Pagi	08:00:00	16:00:00	1	2024-11-11 09:26:27.933	admin
2	Shift 2	Siang/Malam	16:00:00	08:00:00	1	2024-11-11 09:26:27.933	admin


 
