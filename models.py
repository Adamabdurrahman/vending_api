from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Time

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

    id_recnum_variant = Column(BigInteger, primary_key=True, index=True)
    nama_variant = Column(String(100), nullable=True)
    url_image = Column(String(200), nullable=True)
    status_variant = Column(Integer, nullable=True)


# ================================================================
# MODEL BARU — ditambahkan berdasarkan DB asli (bukan dari branch teman)
# ================================================================


class Restock(Base):
    """Stok per slot untuk setiap vending machine — dbo.manage_restok"""

    __tablename__ = "manage_restok"
    __table_args__ = {"schema": "dbo"}

    id_recnum_mrs = Column(BigInteger, primary_key=True, index=True)
    id_recnum_mav = Column(BigInteger, nullable=True)
    stok_qty = Column(Integer, nullable=False)
    status_restok = Column(String(10), nullable=False, default="1")  # varchar di DB
    update_time = Column(DateTime, nullable=True)
    user_input = Column(String(100), nullable=True)
    slot_number = Column(String(10), nullable=False)


class SlotNumber(Base):
    """Konfigurasi slot mesin — dbo.manage_map_slot_number"""

    __tablename__ = "manage_map_slot_number"
    __table_args__ = {"schema": "dbo"}

    id_recnum_msn = Column(BigInteger, primary_key=True, index=True)
    id_recnum_mav = Column(BigInteger, nullable=True)
    slot_name = Column(String(10), nullable=False)
    slot_number_max = Column(Integer, nullable=False)
    update_time = Column(DateTime, nullable=True)
    user_input = Column(String(100), nullable=True)
    id_recnum_variant = Column(BigInteger, nullable=True)


class Machine(Base):
    """Data mesin vending — dbo.master_alat_vm"""

    __tablename__ = "master_alat_vm"
    __table_args__ = {"schema": "dbo"}

    id_recnum_mav = Column(BigInteger, primary_key=True, index=True)
    nama_vm = Column(String(255), nullable=False)
    no_ref = Column(String(255), nullable=True)
    update_time = Column(DateTime, nullable=True)
    user_input = Column(String(100), nullable=True)
    ip_address = Column(String(100), nullable=True)


class Shift(Base):
    """Jam shift kerja — dbo.master_settime"""

    __tablename__ = "master_settime"
    __table_args__ = {"schema": "dbo"}

    id_recnum_mst = Column(BigInteger, primary_key=True, index=True)
    nama_shift = Column(String(100), nullable=False)
    nama_bagian = Column(String(100), nullable=False)
    jam_mulai = Column(Time, nullable=True)  # time di DB
    jam_akhir = Column(Time, nullable=True)  # time di DB
    status_active = Column(String(10), nullable=False, default="1")  # varchar di DB
    update_time = Column(DateTime, nullable=True)
    user_input = Column(String(100), nullable=True)
