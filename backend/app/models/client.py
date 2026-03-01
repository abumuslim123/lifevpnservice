from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    telegram: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    vpn_profiles: Mapped[List["VpnProfile"]] = relationship(  # noqa: F821
        "VpnProfile", back_populates="client", cascade="all, delete-orphan"
    )
    proxy_configs: Mapped[List["ProxyConfig"]] = relationship(  # noqa: F821
        "ProxyConfig", back_populates="client", cascade="all, delete-orphan"
    )
