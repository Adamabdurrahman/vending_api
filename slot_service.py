"""
slot_service.py
Business logic untuk CRUD dbo.manage_map_slot_number (konfigurasi slot per VM).

Struktur tabel asli (terverifikasi dari DB):
  id_recnum_msn   bigint  PK
  id_recnum_mav   bigint
  slot_name       varchar
  slot_number_max int
  update_time     datetime
  user_input      varchar
  id_recnum_variant bigint
"""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas


def _serialize(slot: models.SlotNumber) -> dict:
    return {
        "id_recnum_msn": slot.id_recnum_msn,
        "id_recnum_mav": slot.id_recnum_mav,
        "slot_name": slot.slot_name,
        "slot_number_max": slot.slot_number_max,
        "id_recnum_variant": slot.id_recnum_variant,
        "update_time": slot.update_time.isoformat() if slot.update_time else None,
        "user_input": slot.user_input,
    }


def get_slots_by_vm(db: Session, vm_id: int) -> dict:
    slots = (
        db.query(models.SlotNumber)
        .filter(models.SlotNumber.id_recnum_mav == vm_id)
        .order_by(models.SlotNumber.slot_name)
        .all()
    )
    if not slots:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tidak ada slot untuk VM ID {vm_id}",
        )
    total_capacity = sum(s.slot_number_max for s in slots)
    return {
        "id_recnum_mav": vm_id,
        "total_rows": len(slots),
        "total_capacity": total_capacity,
        "slots": [_serialize(s) for s in slots],
    }


def get_slot_by_id(db: Session, slot_id: int) -> dict:
    slot = (
        db.query(models.SlotNumber)
        .filter(models.SlotNumber.id_recnum_msn == slot_id)
        .first()
    )
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot ID {slot_id} tidak ditemukan",
        )
    return _serialize(slot)


def create_slot(db: Session, request: schemas.SlotCreateRequest) -> dict:
    if request.slot_number_max < 0:
        raise HTTPException(
            status_code=400, detail="slot_number_max tidak boleh negatif"
        )
    if not request.slot_name or len(request.slot_name) > 10:
        raise HTTPException(
            status_code=400, detail="slot_name tidak valid (max 10 karakter)"
        )

    slot = models.SlotNumber(
        id_recnum_mav=request.id_recnum_mav,
        slot_name=request.slot_name,
        slot_number_max=request.slot_number_max,
        id_recnum_variant=request.id_recnum_variant,
        user_input=request.user_input,
        update_time=datetime.now(),
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return _serialize(slot)


def update_slot(db: Session, slot_id: int, request: schemas.SlotUpdateRequest) -> dict:
    slot = (
        db.query(models.SlotNumber)
        .filter(models.SlotNumber.id_recnum_msn == slot_id)
        .first()
    )
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot ID {slot_id} tidak ditemukan",
        )

    if request.slot_name is not None:
        if len(request.slot_name) > 10:
            raise HTTPException(status_code=400, detail="slot_name max 10 karakter")
        slot.slot_name = request.slot_name

    if request.slot_number_max is not None:
        if request.slot_number_max < 0:
            raise HTTPException(
                status_code=400, detail="slot_number_max tidak boleh negatif"
            )
        slot.slot_number_max = request.slot_number_max

    if request.id_recnum_variant is not None:
        slot.id_recnum_variant = request.id_recnum_variant

    if request.user_input is not None:
        slot.user_input = request.user_input

    slot.update_time = datetime.now()
    db.commit()
    db.refresh(slot)
    return _serialize(slot)


def delete_slot(db: Session, slot_id: int) -> dict:
    slot = (
        db.query(models.SlotNumber)
        .filter(models.SlotNumber.id_recnum_msn == slot_id)
        .first()
    )
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Slot ID {slot_id} tidak ditemukan",
        )
    slot_name = slot.slot_name
    vm_id = slot.id_recnum_mav
    db.delete(slot)
    db.commit()
    return {
        "status": "success",
        "message": f"Slot '{slot_name}' untuk VM {vm_id} berhasil dihapus",
    }
