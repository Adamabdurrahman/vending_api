from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    # Kolom Pydantic untuk input (berdasarkan kebiasaan FastAPI, huruf kecil untuk API input)
    username: str
    password: str


class LoginResponse(BaseModel):
    id_recnum_mur: int
    Id: str
    username: str
    email_primary: str
    level_user: int
    status_active: str
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True


class AccountResponse(BaseModel):
    id_recnum_mur: int
    username: str
    email_primary: str
    email_secondary: Optional[str] = None
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True


class AccountUpdateRequest(BaseModel):
    username: str
    email_primary: str
    email_secondary: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    new_password: str


class RegisterRequest(BaseModel):
    id: Optional[str] = None
    username: str
    password: str
    level_user: int
    email_primary: str
    email_secondary: Optional[str] = None
    nohp: str


class VerifyTokenRequest(BaseModel):
    user_id: str
    token: str


class ApproveUserRequest(BaseModel):
    target_user_id: str
    admin_id: str


class ResetPasswordRequest(BaseModel):
    username: str
    email: str


class ResetPasswordConfirmRequest(BaseModel):
    user_id: str
    token: str
    new_password: str


class PendingUserResponse(BaseModel):
    id_recnum_mur: int
    Id: str
    UserName: str
    email_primary: str
    nohp: str
    register_time: Optional[str] = None

    class Config:
        from_attributes = True


class AdminUpdateUserRequest(BaseModel):
    level_user: int
    new_password: Optional[str] = None


class UserManagementResponse(BaseModel):
    id_recnum_mur: int
    Id: str
    UserName: str
    level_user: int
    email_primary: str
    nohp: str
    status_active: str
    register_time: Optional[str] = None

    class Config:
        from_attributes = True


class VariantBase(BaseModel):
    nama_variant: Optional[str] = None
    url_image: Optional[str] = None
    status_variant: Optional[int] = 1


class VariantCreate(VariantBase):
    nama_variant: str


class VariantUpdate(BaseModel):
    nama_variant: Optional[str] = None
    url_image: Optional[str] = None
    status_variant: Optional[int] = None


class VariantResponse(VariantBase):
    id_recnum_variant: int

    class Config:
        from_attributes = True


# ================================================================
# SCHEMAS BARU — Restock, SlotNumber, Machine, Shift
# ================================================================


# ── RESTOCK ────────────────────────────────────────────────────────────────────
class RestockCreateRequest(BaseModel):
    id_recnum_mav: int
    slot_number: str
    stok_qty: int
    user_input: str = "admin"
    status_restok: str = "1"  # varchar di DB: '0' atau '1'


class RestockUpdateRequest(BaseModel):
    stok_qty: Optional[int] = None
    status_restok: Optional[str] = None
    user_input: Optional[str] = None


class RestockResponse(BaseModel):
    id_recnum_mrs: int
    id_recnum_mav: int
    stok_qty: int
    status_restok: str
    slot_number: str
    update_time: Optional[str] = None
    user_input: str

    class Config:
        from_attributes = True


class RestockListResponse(BaseModel):
    total: int
    data: list[RestockResponse]


class RestockByVMResponse(BaseModel):
    id_recnum_mav: int
    total_slots: int
    total_qty: int
    restocks: list[RestockResponse]


# ── SLOT NUMBER ──────────────────────────────────────────────────────────
class SlotCreateRequest(BaseModel):
    id_recnum_mav: int
    slot_name: str
    slot_number_max: int
    id_recnum_variant: Optional[int] = None
    user_input: str = "admin"


class SlotUpdateRequest(BaseModel):
    slot_name: Optional[str] = None
    slot_number_max: Optional[int] = None
    id_recnum_variant: Optional[int] = None
    user_input: Optional[str] = None


class SlotResponse(BaseModel):
    id_recnum_msn: int
    id_recnum_mav: int
    slot_name: str
    slot_number_max: int
    id_recnum_variant: Optional[int] = None
    update_time: Optional[str] = None
    user_input: Optional[str] = None

    class Config:
        from_attributes = True


class SlotByVMResponse(BaseModel):
    id_recnum_mav: int
    total_rows: int
    total_capacity: int
    slots: list[SlotResponse]


# ── MACHINE ──────────────────────────────────────────────────────────────────
class MachineCreateRequest(BaseModel):
    nama_vm: str
    no_ref: Optional[str] = None
    ip_address: Optional[str] = None
    user_input: str = "admin"


class MachineUpdateRequest(BaseModel):
    nama_vm: Optional[str] = None
    no_ref: Optional[str] = None
    ip_address: Optional[str] = None
    user_input: Optional[str] = None


class MachineResponse(BaseModel):
    id_recnum_mav: int
    nama_vm: str
    no_ref: Optional[str] = None
    ip_address: Optional[str] = None
    update_time: Optional[str] = None
    user_input: Optional[str] = None

    class Config:
        from_attributes = True


class MachineListResponse(BaseModel):
    total: int
    data: list[MachineResponse]


# ── SHIFT ───────────────────────────────────────────────────────────────────────
class ShiftCreateRequest(BaseModel):
    nama_shift: str
    nama_bagian: str
    jam_mulai: Optional[str] = None  # format 'HH:MM'
    jam_akhir: Optional[str] = None  # format 'HH:MM'
    status_active: str = "1"  # varchar di DB: '0' atau '1'
    user_input: str = "admin"


class ShiftUpdateRequest(BaseModel):
    nama_shift: Optional[str] = None
    nama_bagian: Optional[str] = None
    jam_mulai: Optional[str] = None
    jam_akhir: Optional[str] = None
    status_active: Optional[str] = None
    user_input: Optional[str] = None


class ShiftResponse(BaseModel):
    id_recnum_mst: int
    nama_shift: str
    nama_bagian: str
    jam_mulai: Optional[str] = None
    jam_akhir: Optional[str] = None
    status_active: str
    update_time: Optional[str] = None
    user_input: Optional[str] = None

    class Config:
        from_attributes = True


class ShiftListResponse(BaseModel):
    total: int
    data: list[ShiftResponse]


# ================================================================
# SCHEMAS INVENTORY DASHBOARD
# ================================================================


class InventoryStockInItem(BaseModel):
    variant_name: str
    qty: int


class InventoryStockInRequest(BaseModel):
    items: list[InventoryStockInItem]
    note: Optional[str] = None
    date: Optional[str] = (
        None  # Format YYYY-MM-DD. Default: hari ini. Isi untuk data historis/penyesuaian.
    )
