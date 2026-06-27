"""
machine_service.py
Business logic untuk CRUD dbo.master_alat_vm (data mesin vending).

Struktur tabel asli (terverifikasi dari DB):
  id_recnum_mav  bigint  PK
  nama_vm        varchar
  no_ref         varchar  nullable
  update_time    datetime nullable
  user_input     varchar  nullable
  ip_address     varchar  nullable
"""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas


def _serialize(machine: models.Machine) -> dict:
    return {
        "id_recnum_mav": machine.id_recnum_mav,
        "nama_vm": machine.nama_vm,
        "no_ref": machine.no_ref,
        "ip_address": machine.ip_address,
        "update_time": machine.update_time.isoformat() if machine.update_time else None,
        "user_input": machine.user_input,
    }


def get_all_machines(db: Session) -> dict:
    machines = db.query(models.Machine).order_by(models.Machine.id_recnum_mav).all()
    return {
        "total": len(machines),
        "data": [_serialize(m) for m in machines],
    }


def get_machine_by_id(db: Session, machine_id: int) -> dict:
    machine = (
        db.query(models.Machine)
        .filter(models.Machine.id_recnum_mav == machine_id)
        .first()
    )
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine ID {machine_id} tidak ditemukan",
        )
    return _serialize(machine)


def create_machine(db: Session, request: schemas.MachineCreateRequest) -> dict:
    machine = models.Machine(
        nama_vm=request.nama_vm,
        no_ref=request.no_ref,
        ip_address=request.ip_address,
        user_input=request.user_input,
        update_time=datetime.now(),
    )
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return _serialize(machine)


def update_machine(
    db: Session, machine_id: int, request: schemas.MachineUpdateRequest
) -> dict:
    machine = (
        db.query(models.Machine)
        .filter(models.Machine.id_recnum_mav == machine_id)
        .first()
    )
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine ID {machine_id} tidak ditemukan",
        )

    if request.nama_vm is not None:
        machine.nama_vm = request.nama_vm
    if request.no_ref is not None:
        machine.no_ref = request.no_ref
    if request.ip_address is not None:
        machine.ip_address = request.ip_address
    if request.user_input is not None:
        machine.user_input = request.user_input

    machine.update_time = datetime.now()
    db.commit()
    db.refresh(machine)
    return _serialize(machine)


def delete_machine(db: Session, machine_id: int) -> dict:
    machine = (
        db.query(models.Machine)
        .filter(models.Machine.id_recnum_mav == machine_id)
        .first()
    )
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine ID {machine_id} tidak ditemukan",
        )
    nama = machine.nama_vm
    db.delete(machine)
    db.commit()
    return {"status": "success", "message": f"Machine '{nama}' berhasil dihapus"}
