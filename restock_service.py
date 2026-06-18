"""
Restock Service Module
Menangani business logic untuk CRUD manage_restok (stok VM per slot)
"""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
import models
import schemas
from fastapi import HTTPException, status


def get_all_restocks(db: Session, status_filter: int = None):
    """
    Ambil semua restock dengan opsional filter status
    
    Args:
        db: Database session
        status_filter: Optional, filter by status (0 atau 1)
    
    Returns:
        dict dengan total dan list restock
    """
    query = db.query(models.Restock)
    
    if status_filter is not None:
        query = query.filter(models.Restock.status_restok == status_filter)
    
    restocks = query.order_by(models.Restock.id_recnum_mrs).all()
    
    return {
        "total": len(restocks),
        "data": restocks
    }


def get_restock_by_id(db: Session, restock_id: int):
    """
    Ambil restock berdasarkan ID
    
    Args:
        db: Database session
        restock_id: ID restock
    
    Returns:
        Restock object atau raise HTTPException 404
    """
    restock = db.query(models.Restock).filter(
        models.Restock.id_recnum_mrs == restock_id
    ).first()
    
    if not restock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Restock dengan ID {restock_id} tidak ditemukan"
        )
    
    return restock


def get_restock_by_vm(db: Session, vm_id: int):
    """
    Ambil semua restock untuk vending machine tertentu
    
    Args:
        db: Database session
        vm_id: ID vending machine
    
    Returns:
        dict dengan info VM dan list restock
    """
    restocks = db.query(models.Restock).filter(
        models.Restock.id_recnum_mav == vm_id,
        models.Restock.status_restok == 1
    ).order_by(models.Restock.slot_number).all()
    
    if not restocks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tidak ada restock aktif untuk VM ID {vm_id}"
        )
    
    total_qty = sum(r.stok_qty for r in restocks)
    
    return {
        "id_recnum_mav": vm_id,
        "total_slots": len(restocks),
        "total_qty": total_qty,
        "restocks": restocks
    }


def create_restock(db: Session, request: schemas.RestockCreateRequest):
    """
    Buat restock baru untuk slot tertentu
    
    Args:
        db: Database session
        request: RestockCreateRequest
    
    Returns:
        Restock object yang baru dibuat
    """
    # Validasi stok_qty
    if request.stok_qty < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jumlah stok tidak boleh negatif"
        )
    
    # Validasi status
    if request.status_restok not in [0, 1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status restock harus 0 (inactive) atau 1 (active)"
        )
    
    # Validasi slot_number format (A1, B2, dll)
    if not _validate_slot_number(request.slot_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format slot number tidak valid (gunakan format A1, B2, dst)"
        )
    
    # Check apakah slot sudah ada untuk VM ini
    existing = db.query(models.Restock).filter(
        models.Restock.id_recnum_mav == request.id_recnum_mav,
        models.Restock.slot_number == request.slot_number
    ).first()
    
    if existing:
        # Update yang sudah ada
        existing.stok_qty = request.stok_qty
        existing.status_restok = request.status_restok
        existing.user_input = request.user_input
        existing.update_time = datetime.now()
        db.commit()
        db.refresh(existing)
        return existing
    
    # Buat restock baru
    new_restock = models.Restock(
        id_recnum_mav=request.id_recnum_mav,
        stok_qty=request.stok_qty,
        status_restok=request.status_restok,
        user_input=request.user_input,
        slot_number=request.slot_number,
        update_time=datetime.now()
    )
    
    db.add(new_restock)
    db.commit()
    db.refresh(new_restock)
    
    return new_restock


def update_restock(db: Session, restock_id: int, request: schemas.RestockUpdateRequest):
    """
    Update restock yang ada
    
    Args:
        db: Database session
        restock_id: ID restock yang akan diupdate
        request: RestockUpdateRequest
    
    Returns:
        Restock object yang sudah diupdate
    """
    restock = get_restock_by_id(db, restock_id)
    
    # Update stok_qty dengan validasi
    if request.stok_qty is not None:
        if request.stok_qty < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Jumlah stok tidak boleh negatif"
            )
        restock.stok_qty = request.stok_qty
    
    # Update status dengan validasi
    if request.status_restok is not None:
        if request.status_restok not in [0, 1]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status restock harus 0 (inactive) atau 1 (active)"
            )
        restock.status_restok = request.status_restok
    
    # Update user_input
    if request.user_input:
        restock.user_input = request.user_input
    
    restock.update_time = datetime.now()
    
    db.commit()
    db.refresh(restock)
    
    return restock


def delete_restock(db: Session, restock_id: int):
    """
    Hapus restock (hard delete)
    
    Args:
        db: Database session
        restock_id: ID restock yang akan dihapus
    
    Returns:
        Pesan sukses atau raise HTTPException
    """
    restock = get_restock_by_id(db, restock_id)
    
    db.delete(restock)
    db.commit()
    
    return {
        "status": "success",
        "message": f"Restock slot {restock.slot_number} (VM {restock.id_recnum_mav}) berhasil dihapus"
    }


def update_stock_qty(db: Session, vm_id: int, slot_number: str, new_qty: int, user: str):
    """
    Update kuantitas stok untuk slot tertentu
    
    Args:
        db: Database session
        vm_id: ID vending machine
        slot_number: Nomor slot
        new_qty: Kuantitas baru
        user: User yang melakukan update
    
    Returns:
        Restock object yang sudah diupdate
    """
    if new_qty < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jumlah stok tidak boleh negatif"
        )
    
    restock = db.query(models.Restock).filter(
        models.Restock.id_recnum_mav == vm_id,
        models.Restock.slot_number == slot_number
    ).first()
    
    if not restock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Restock untuk slot {slot_number} di VM {vm_id} tidak ditemukan"
        )
    
    restock.stok_qty = new_qty
    restock.user_input = user
    restock.update_time = datetime.now()
    
    db.commit()
    db.refresh(restock)
    
    return restock


def get_low_stock_alerts(db: Session, threshold: int = 10):
    """
    Dapatkan restock dengan stok di bawah threshold
    
    Args:
        db: Database session
        threshold: Batas minimal stok (default 10)
    
    Returns:
        List restock yang stoknya rendah
    """
    restocks = db.query(models.Restock).filter(
        models.Restock.stok_qty < threshold,
        models.Restock.status_restok == 1
    ).order_by(models.Restock.id_recnum_mav, models.Restock.slot_number).all()
    
    return {
        "total": len(restocks),
        "threshold": threshold,
        "data": restocks
    }


def _validate_slot_number(slot_number: str) -> bool:
    """
    Validasi format slot number (A1, B2, C10, dll)
    
    Args:
        slot_number: String slot number
    
    Returns:
        True jika valid, False jika tidak
    """
    if not slot_number or len(slot_number) < 2:
        return False
    
    # Slot harus dimulai dengan huruf, diikuti angka
    first_char = slot_number[0]
    rest = slot_number[1:]
    
    if not first_char.isalpha():
        return False
    
    if not rest.isdigit():
        return False
    
    return True
