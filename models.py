from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from database import Base

class User(Base):
    __tablename__ = "master_user"
    __table_args__ = {"schema": "dbo"}

    id_recnum_mur = Column(BigInteger, primary_key=True, index=True)
    Id = Column(String(100), nullable=False)
    UserName = Column(String(100), nullable=False)
    Password = Column(String(200), nullable=False)
    level_user = Column(Integer, nullable=False)
    email_primary = Column(String(200), nullable=False)
    email_secondary = Column(String(200), nullable=True)
    nohp = Column(String(20), nullable=False)
    register_time = Column(DateTime, nullable=True)
    update_time = Column(DateTime, nullable=True)
    approve_by = Column(String(100), nullable=True)
    status_active = Column(String(1), nullable=False)
    photo_url = Column(String(255), nullable=True)
    security_token = Column(String(100), nullable=True)
    token_expiry = Column(DateTime, nullable=True)

class Variant(Base):
    __tablename__ = "master_variant"
    __table_args__ = {"schema": "dbo"}

    id_recnum_variant = Column(Integer, primary_key=True, index=True)
    nama_variant = Column(String(100), nullable=False, unique=True)
    image_url = Column(String(255), nullable=True)
    status = Column(Integer, nullable=False, default=1)  # 0 = inactive, 1 = active
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

class Restock(Base):
    __tablename__ = "manage_restok"
    __table_args__ = {"schema": "dbo"}

    id_recnum_mrs = Column(Integer, primary_key=True, index=True)
    id_recnum_mav = Column(Integer, nullable=False)  # FK ke vending machine
    stok_qty = Column(Integer, nullable=False)  # Jumlah stok
    status_restok = Column(Integer, nullable=False, default=1)  # 0 = inactive, 1 = active
    update_time = Column(DateTime, nullable=True)
    user_input = Column(String(100), nullable=False)  # Siapa yang update
    slot_number = Column(String(10), nullable=False)  # Slot number (A1, A2, B1, dll)


class WarehouseStock(Base):
    __tablename__ = "warehouse_stock"
    __table_args__ = {"schema": "dbo"}

    id = Column(Integer, primary_key=True, index=True)
    variant_name = Column(String(50), nullable=False)
    movement_type = Column(String(10), nullable=False)
    qty = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    note = Column(String(200), nullable=True)
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False)


class SlotNumber(Base):
    __tablename__ = "manage_map_slot_number"
    __table_args__ = {"schema": "dbo"}

    id_recnum_msn = Column(Integer, primary_key=True, index=True)
    id_recnum_mav = Column(Integer, nullable=False)
    slot_name = Column(String(10), nullable=False)
    slot_number_max = Column(Integer, nullable=False)
    update_time = Column(DateTime, nullable=True)
    user_input = Column(String(100), nullable=False)
    id_recnum_variant = Column(Integer, nullable=True)


class Machine(Base):
    __tablename__ = "master_alat_vm"
    __table_args__ = {"schema": "dbo"}

    id_recnum_mav = Column(Integer, primary_key=True, index=True)
    nama_vm = Column(String(255), nullable=False)
    no_ref = Column(String(255), nullable=True)
    update_time = Column(DateTime, nullable=True)
    user_input = Column(String(100), nullable=False)
    ip_address = Column(String(100), nullable=True)


class Shift(Base):
    __tablename__ = "master_settime"
    __table_args__ = {"schema": "dbo"}

    id_recnum_mst = Column(Integer, primary_key=True, index=True)
    nama_shift = Column(String(100), nullable=False)
    nama_bagian = Column(String(100), nullable=True)
    jam_mulai = Column(String(20), nullable=True)
    jam_akhir = Column(String(20), nullable=True)
    status_active = Column(Integer, nullable=False, default=1)
    update_time = Column(DateTime, nullable=True)
    user_input = Column(String(100), nullable=False)

