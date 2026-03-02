from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Text, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.protocol_config import ProtocolType


class VpnProfile(Base):
    __tablename__ = "vpn_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    client_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    server_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("servers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    active_protocol: Mapped[ProtocolType] = mapped_column(SAEnum(ProtocolType), nullable=False)
    enabled_protocols: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    credentials: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    client: Mapped[Optional["Client"]] = relationship("Client", back_populates="vpn_profiles")  # noqa: F821
    user: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User", back_populates="vpn_profiles", foreign_keys=[user_id]
    )
    server: Mapped["Server"] = relationship("Server", back_populates="vpn_profiles")  # noqa: F821
