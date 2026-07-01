"""
restock_service.py
Business logic untuk CRUD dbo.manage_restok (stok per slot VM).

CATATAN PENTING:
  - status_restok di DB adalah VARCHAR ('0' / '1'), bukan integer.
  - id_recnum_mrs dan id_recnum_mav adalah BIGINT.
  - POST create bersifat UPSERT: jika slot sudah ada untuk VM tsb, di-UPDATE.
"""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas


def _validate_status(val: str):
    if val not in ("0", "1"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status_restok harus '0' (inactive) atau '1' (active)",
        )


def _validate_slot(slot_number: str):
    if not slot_number or len(slot_number) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format slot_number tidak valid. Contoh: A1, B2, C10",
        )
    if not slot_number[0].isalpha() or not slot_number[1:].isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format slot_number tidak valid. Harus diawali huruf lalu angka (A1, B2, dst)",
        )


def _serialize(restock: models.Restock) -> dict:
    return {
        "id_recnum_mrs": restock.id_recnum_mrs,
        "id_recnum_mav": restock.id_recnum_mav,
        "stok_qty": restock.stok_qty,
        "status_restok": restock.status_restok,
        "slot_number": restock.slot_number,
        "update_time": restock.update_time.isoformat() if restock.update_time else None,
        "user_input": restock.user_input or "",
    }


def get_all_restocks(db: Session, status_filter: str = None) -> dict:
    query = db.query(models.Restock)
    if status_filter is not None:
        query = query.filter(models.Restock.status_restok == status_filter)
    restocks = query.order_by(models.Restock.id_recnum_mrs).all()
    return {
        "total": len(restocks),
        "data": [_serialize(r) for r in restocks],
    }


def get_restock_by_id(db: Session, restock_id: int) -> dict:
    restock = (
        db.query(models.Restock)
        .filter(models.Restock.id_recnum_mrs == restock_id)
        .first()
    )
    if not restock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Restock ID {restock_id} tidak ditemukan",
        )
    return _serialize(restock)


def get_restock_by_vm(db: Session, vm_id: int, page: int = 1, page_size: int = 10) -> dict:
    # Query semua dulu untuk total stats dan total_pages
    all_restocks = (
        db.query(models.Restock)
        .filter(
            models.Restock.id_recnum_mav == vm_id, models.Restock.status_restok == "1"
        )
        .all()
    )

    if not all_restocks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tidak ada restock aktif untuk VM ID {vm_id}",
        )

    total_slots = len(all_restocks)
    total_qty = sum(r.stok_qty for r in all_restocks)
    total_pages = max(1, -(-total_slots // page_size))  # ceiling division
    page = max(1, min(page, total_pages))
    skip = (page - 1) * page_size

    # Query dengan pagination + sort terbaru di atas (update_time DESC)
    paginated = (
        db.query(models.Restock)
        .filter(
            models.Restock.id_recnum_mav == vm_id, models.Restock.status_restok == "1"
        )
        .order_by(models.Restock.update_time.desc())
        .offset(skip)
        .limit(page_size)
        .all()
    )
    return {
        "id_recnum_mav": vm_id,
        "total_slots": total_slots,
        "total_qty": total_qty,
        "total_pages": total_pages,
        "current_page": page,
        "restocks": [_serialize(r) for r in paginated],
    }


def create_restock(db: Session, request: schemas.RestockCreateRequest) -> dict:
    _validate_slot(request.slot_number)
    _validate_status(request.status_restok)

    if request.stok_qty < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="stok_qty tidak boleh negatif",
        )

    # UPSERT: cek apakah slot sudah ada untuk VM ini
    existing = (
        db.query(models.Restock)
        .filter(
            models.Restock.id_recnum_mav == request.id_recnum_mav,
            models.Restock.slot_number == request.slot_number,
        )
        .first()
    )

    if existing:
        existing.stok_qty = request.stok_qty
        existing.status_restok = request.status_restok
        existing.user_input = request.user_input
        existing.update_time = datetime.now()
        db.commit()
        db.refresh(existing)
        return _serialize(existing)

    new_restock = models.Restock(
        id_recnum_mav=request.id_recnum_mav,
        slot_number=request.slot_number,
        stok_qty=request.stok_qty,
        status_restok=request.status_restok,
        user_input=request.user_input,
        update_time=datetime.now(),
    )
    db.add(new_restock)
    db.commit()
    db.refresh(new_restock)
    return _serialize(new_restock)


def update_restock(
    db: Session, restock_id: int, request: schemas.RestockUpdateRequest
) -> dict:
    restock = (
        db.query(models.Restock)
        .filter(models.Restock.id_recnum_mrs == restock_id)
        .first()
    )
    if not restock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Restock ID {restock_id} tidak ditemukan",
        )

    if request.stok_qty is not None:
        if request.stok_qty < 0:
            raise HTTPException(status_code=400, detail="stok_qty tidak boleh negatif")
        restock.stok_qty = request.stok_qty

    if request.status_restok is not None:
        _validate_status(request.status_restok)
        restock.status_restok = request.status_restok

    if request.user_input is not None:
        restock.user_input = request.user_input

    restock.update_time = datetime.now()
    db.commit()
    db.refresh(restock)
    return _serialize(restock)


def delete_restock(db: Session, restock_id: int) -> dict:
    restock = (
        db.query(models.Restock)
        .filter(models.Restock.id_recnum_mrs == restock_id)
        .first()
    )
    if not restock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Restock ID {restock_id} tidak ditemukan",
        )
    slot = restock.slot_number
    vm = restock.id_recnum_mav
    db.delete(restock)
    db.commit()
    return {
        "status": "success",
        "message": f"Restock slot {slot} (VM {vm}) berhasil dihapus",
    }


def update_stock_qty(
    db: Session, vm_id: int, slot_number: str, stok_qty: int, user: str
) -> dict:
    if stok_qty < 0:
        raise HTTPException(status_code=400, detail="stok_qty tidak boleh negatif")

    restock = (
        db.query(models.Restock)
        .filter(
            models.Restock.id_recnum_mav == vm_id,
            models.Restock.slot_number == slot_number,
        )
        .first()
    )
    if not restock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot {slot_number} di VM {vm_id} tidak ditemukan",
        )
    restock.stok_qty = stok_qty
    restock.user_input = user
    restock.update_time = datetime.now()
    db.commit()
    db.refresh(restock)
    return _serialize(restock)


def get_low_stock_alerts(db: Session, threshold: int = 10) -> dict:
    restocks = (
        db.query(models.Restock)
        .filter(
            models.Restock.stok_qty < threshold, models.Restock.status_restok == "1"
        )
        .order_by(models.Restock.id_recnum_mav, models.Restock.slot_number)
        .all()
    )
    return {
        "total": len(restocks),
        "threshold": threshold,
        "data": [_serialize(r) for r in restocks],
    }
