from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
import enum


class ProtocolTypeEnum(str, enum.Enum):
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


class ProtocolConfigBase(BaseModel):
    server_id: int
    protocol: ProtocolTypeEnum
    port: int
    config_data: Optional[Dict[str, Any]] = None
    extra: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class ProtocolConfigCreate(ProtocolConfigBase):
    pass


class ProtocolConfigUpdate(BaseModel):
    port: Optional[int] = None
    config_data: Optional[Dict[str, Any]] = None
    extra: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    is_installed: Optional[bool] = None


class ProtocolConfigRead(ProtocolConfigBase):
    id: int
    is_installed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
