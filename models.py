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
    approve_by = Column(String(10), nullable=True)
    status_active = Column(String(1), nullable=False)
    photo_url = Column(String(255), nullable=True)
