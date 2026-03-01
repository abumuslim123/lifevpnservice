from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.schemas.protocol_config import ProtocolTypeEnum


class VpnProfileBase(BaseModel):
    name: str
    server_id: int
    active_protocol: ProtocolTypeEnum
    enabled_protocols: Optional[List[ProtocolTypeEnum]] = None
    client_id: Optional[int] = None
    user_id: Optional[int] = None
    is_active: bool = True
    notes: Optional[str] = None


class VpnProfileCreate(VpnProfileBase):
    pass


class VpnProfileUpdate(BaseModel):
    name: Optional[str] = None
    server_id: Optional[int] = None
    active_protocol: Optional[ProtocolTypeEnum] = None
    enabled_protocols: Optional[List[ProtocolTypeEnum]] = None
    client_id: Optional[int] = None
    user_id: Optional[int] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class SwitchProtocolRequest(BaseModel):
    protocol: ProtocolTypeEnum


class VpnProfileRead(VpnProfileBase):
    id: int
    credentials: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
