from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class ProtocolType(str, enum.Enum):
    WIREGUARD = "wireguard"
    AMNEZIA_WG = "amnezia_wg"
    OPENVPN = "openvpn"
    IKEV2 = "ikev2"
    L2TP = "l2tp"
    PPTP = "pptp"
    XRAY_VLESS = "xray_vless"
    XRAY_VMESS = "xray_vmess"
    XRAY_TROJAN = "xray_trojan"
    XRAY_SHADOWSOCKS = "xray_shadowsocks"


class ProtocolConfig(Base):
    __tablename__ = "protocol_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True)
    protocol: Mapped[ProtocolType] = mapped_column(SAEnum(ProtocolType), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    is_installed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config_data: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    server: Mapped["Server"] = relationship("Server", back_populates="protocol_configs")  # noqa: F821
