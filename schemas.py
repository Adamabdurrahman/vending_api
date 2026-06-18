from pydantic import BaseModel
from typing import Optional

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


# ============ VARIANT SCHEMAS ============

class VariantCreateRequest(BaseModel):
    nama_variant: str
    image_url: Optional[str] = None
    status: int = 1  # Default active

class VariantUpdateRequest(BaseModel):
    nama_variant: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[int] = None

class VariantResponse(BaseModel):
    id_recnum_variant: int
    nama_variant: str
    image_url: Optional[str] = None
    status: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

class VariantListResponse(BaseModel):
    total: int
    data: list[VariantResponse]


# ============ RESTOCK SCHEMAS ============

class RestockCreateRequest(BaseModel):
    id_recnum_mav: int  # ID vending machine
    stok_qty: int  # Jumlah stok
    slot_number: str  # Slot number (A1, A2, B1, dll)
    user_input: str = "admin"  # Default admin
    status_restok: int = 1  # Default active

class RestockUpdateRequest(BaseModel):
    stok_qty: Optional[int] = None
    status_restok: Optional[int] = None
    user_input: Optional[str] = None

class RestockResponse(BaseModel):
    id_recnum_mrs: int
    id_recnum_mav: int
    stok_qty: int
    status_restok: int
    slot_number: str
    update_time: Optional[str] = None
    user_input: str

    class Config:
        from_attributes = True

class RestockListResponse(BaseModel):
    total: int
    data: list[RestockResponse]

class RestockByVMResponse(BaseModel):
    """Response untuk daftar restock per vending machine"""
    id_recnum_mav: int
    total_slots: int
    total_qty: int
    restocks: list[RestockResponse]


# ============ INVENTORY DASHBOARD SCHEMAS ============

class StockInItem(BaseModel):
    variant_name: str
    qty: int

class StockInRequest(BaseModel):
    items: list[StockInItem]
    note: Optional[str] = None

class StockInResult(BaseModel):
    variant_name: str
    qty_added: int
    previous_balance: int
    new_balance: int

class StockInResponse(BaseModel):
    success: bool
    message: str
    total_added: int | None = None
    results: Optional[list[StockInResult]] = None
    errors: Optional[list[str]] = None

class StockMovementItem(BaseModel):
    id: int
    date: str
    date_string: str
    time_string: str
    variant_name: str
    movement_type: str
    qty: int
    balance_after: int
    note: Optional[str] = None
    created_by: str

class PaginatedMovementResponse(BaseModel):
    page: int
    per_page: int
    total_items: int
    total_pages: int
    items: list[StockMovementItem]

class InventoryVariantMonthly(BaseModel):
    month_name: str
    month_number: int
    predicted: int

class InventoryVariantSummary(BaseModel):
    variant_name: str
    predicted_demand: int
    warehouse_stock: int
    vm_stock: int
    total_available: int
    to_purchase: int
    purchase_percentage: float
    monthly: list[InventoryVariantMonthly]

class HistoryVariantSummary(BaseModel):
    variant_name: str
    stock_in: int
    stock_out: int
    consumed: int
    predicted: int
    actual: int

class HistorySummary(BaseModel):
    total_stock_in: int
    total_stock_out: int
    total_consumed: int
    predicted_demand: int
    actual_demand: int
    prediction_accuracy: float
    per_variant: list[HistoryVariantSummary]

class InventoryDashboardSummary(BaseModel):
    total_predicted_demand: int
    total_warehouse_stock: int
    total_vm_stock: int
    total_available: int
    total_to_purchase: int

class DecisionSupportInfo(BaseModel):
    recommended_purchase_total: int
    top_variant: str
    top_variant_qty: int
    notes: list[str]

class AutoSyncInfo(BaseModel):
    processed_variants: int
    total_out_qty: int
    note: str

class InventoryDashboardResponse(BaseModel):
    year: int
    quarter: int
    quarter_label: str
    has_prediction_data: bool
    available_quarters: list[dict]
    summary: Optional[InventoryDashboardSummary] = None
    variants: list[InventoryVariantSummary]
    history_summary: Optional[HistorySummary] = None
    decision_support: Optional[DecisionSupportInfo] = None
    auto_sync_info: Optional[AutoSyncInfo] = None
    movements: Optional[PaginatedMovementResponse] = None
    stock_in_result: Optional[StockInResponse] = None

    class Config:
        from_attributes = True


# ============ SLOT NUMBER SCHEMAS ============

class SlotCreateRequest(BaseModel):
    id_recnum_mav: int
    slot_name: str
    slot_number_max: int
    id_recnum_variant: int | None = None
    user_input: str = "admin"

class SlotUpdateRequest(BaseModel):
    slot_name: str | None = None
    slot_number_max: int | None = None
    id_recnum_variant: int | None = None
    user_input: str | None = None

class SlotResponse(BaseModel):
    id_recnum_msn: int
    id_recnum_mav: int
    slot_name: str
    slot_number_max: int
    id_recnum_variant: int | None = None
    update_time: Optional[str] = None
    user_input: str

    class Config:
        from_attributes = True

class SlotByVMResponse(BaseModel):
    id_recnum_mav: int
    total_rows: int
    total_slots: int
    slots: list[SlotResponse]


# ============ MACHINE SCHEMAS ============

class MachineCreateRequest(BaseModel):
    nama_vm: str
    no_ref: str | None = None
    ip_address: str | None = None
    user_input: str = "admin"

class MachineUpdateRequest(BaseModel):
    nama_vm: str | None = None
    no_ref: str | None = None
    ip_address: str | None = None
    user_input: str | None = None

class MachineResponse(BaseModel):
    id_recnum_mav: int
    nama_vm: str
    no_ref: str | None = None
    ip_address: str | None = None
    update_time: Optional[str] = None
    user_input: str

    class Config:
        from_attributes = True


# ============ SHIFT SCHEMAS ============

class ShiftCreateRequest(BaseModel):
    nama_shift: str
    nama_bagian: str
    jam_mulai: str
    jam_akhir: str
    status_active: int = 1
    user_input: str = "admin"

class ShiftUpdateRequest(BaseModel):
    nama_shift: str | None = None
    nama_bagian: str | None = None
    jam_mulai: str | None = None
    jam_akhir: str | None = None
    status_active: int | None = None
    user_input: str | None = None

class ShiftResponse(BaseModel):
    id_recnum_mst: int
    nama_shift: str
    nama_bagian: str
    jam_mulai: str
    jam_akhir: str
    status_active: int
    update_time: Optional[str] = None
    user_input: str

    class Config:
        from_attributes = True

