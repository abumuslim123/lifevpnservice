from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
import enum


class ProxyTypeEnum(str, enum.Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"
    SHADOWSOCKS = "shadowsocks"
    TROJAN = "trojan"
    VMESS = "vmess"
    VLESS = "vless"


class ProxyConfigBase(BaseModel):
    name: str
    proxy_type: ProxyTypeEnum
    server_id: int
    port: int
    client_id: Optional[int] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    config_data: Optional[Dict[str, Any]] = None
    is_active: bool = True
    notes: Optional[str] = None


class ProxyConfigCreate(ProxyConfigBase):
    pass


class ProxyConfigUpdate(BaseModel):
    name: Optional[str] = None
    port: Optional[int] = None
    client_id: Optional[int] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    config_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class ProxyConfigRead(ProxyConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
