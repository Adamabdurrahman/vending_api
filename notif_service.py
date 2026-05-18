"""
notif_service.py
================================================================================
Service notifikasi sistem — menyimpan notifikasi ke dbo.SystemNotifications.
Dibaca oleh dashboard .NET via endpoint GET /api/v1/notifications.

Severity level:
  SUCCESS  → proses selesai normal
  INFO     → informasi umum (misal: quarterly menunggu data)
  WARNING  → ada yang perlu diperhatikan (misal: is_data_gap = True)
  ERROR    → ada proses yang gagal

NotifType:
  ETL             → proses ETL harian
  UPDATE_ACTUALS  → sinkronisasi data aktual
  QUARTERLY       → quarterly prediction run
  RETRAIN         → retraining model
  SYSTEM          → notifikasi sistem umum
================================================================================
"""

import traceback
from datetime import datetime

from sqlalchemy import text

from database import engine


def push(
    notif_type: str,
    severity: str,
    title: str,
    message: str = None,
    related_month: str = None,
    related_quarter: str = None,
):
    """
    Simpan satu notifikasi ke dbo.SystemNotifications.
    Tidak throw exception — kalau gagal, cukup print ke log.
    """
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO dbo.SystemNotifications
                        (CreatedAt, NotifType, Severity, Title, Message, IsRead,
                         RelatedMonth, RelatedQuarter)
                    VALUES
                        (:ts, :ntype, :sev, :title, :msg, 0, :rmonth, :rquarter)
                """),
                {
                    "ts": datetime.now(),
                    "ntype": notif_type[:30],
                    "sev": severity[:10],
                    "title": title[:200],
                    "msg": message,
                    "rmonth": related_month,
                    "rquarter": related_quarter,
                },
            )
    except Exception as e:
        # Notifikasi gagal tidak boleh menghentikan proses utama
        print(f"[NOTIF] Gagal menyimpan notifikasi: {e}")


# ==============================================================================
# SHORTCUT FUNCTIONS — supaya kode pemanggil lebih ringkas
# ==============================================================================


def success(notif_type, title, message=None, related_month=None, related_quarter=None):
    push(notif_type, "SUCCESS", title, message, related_month, related_quarter)


def info(notif_type, title, message=None, related_month=None, related_quarter=None):
    push(notif_type, "INFO", title, message, related_month, related_quarter)


def warning(notif_type, title, message=None, related_month=None, related_quarter=None):
    push(notif_type, "WARNING", title, message, related_month, related_quarter)


def error(notif_type, title, message=None, related_month=None, related_quarter=None):
    push(notif_type, "ERROR", title, message, related_month, related_quarter)


def error_from_exception(
    notif_type, title, exc: Exception, related_month=None, related_quarter=None
):
    """Shortcut untuk error dari exception — otomatis lampirkan traceback."""
    tb = traceback.format_exc()
    full_msg = f"{str(exc)}\n\n{tb}"
    push(notif_type, "ERROR", title, full_msg, related_month, related_quarter)
