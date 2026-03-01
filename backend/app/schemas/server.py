from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
import enum


class ServerStatusEnum(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    CONNECTING = "connecting"


class ServerOSEnum(str, enum.Enum):
    UBUNTU = "ubuntu"
    DEBIAN = "debian"
    CENTOS = "centos"
    FEDORA = "fedora"
    ALMALINUX = "almalinux"
    OTHER = "other"


class ServerBase(BaseModel):
    name: str
    ip_address: str
    ssh_port: int = 22
    ssh_user: str = "root"
    location: Optional[str] = None
    country_code: Optional[str] = None
    os_type: ServerOSEnum = ServerOSEnum.UBUNTU
    notes: Optional[str] = None
    is_active: bool = True


class ServerCreate(ServerBase):
    ssh_password: Optional[str] = None
    ssh_private_key: Optional[str] = None


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_user: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_private_key: Optional[str] = None
    location: Optional[str] = None
    country_code: Optional[str] = None
    os_type: Optional[ServerOSEnum] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ServerRead(ServerBase):
    id: int
    status: ServerStatusEnum
    last_check_at: Optional[datetime] = None
    installed_protocols: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
