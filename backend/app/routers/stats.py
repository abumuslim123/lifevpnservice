from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.server import Server, ServerStatus
from app.models.client import Client
from app.models.vpn_profile import VpnProfile
from app.models.proxy import ProxyConfig
from app.routers.deps import get_current_active_user

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/dashboard")
async def dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
):
    servers_total = await db.scalar(select(func.count(Server.id)))
    servers_online = await db.scalar(select(func.count(Server.id)).where(Server.status == ServerStatus.ONLINE))
    clients_total = await db.scalar(select(func.count(Client.id)))
    profiles_total = await db.scalar(select(func.count(VpnProfile.id)))
    profiles_active = await db.scalar(select(func.count(VpnProfile.id)).where(VpnProfile.is_active == True))
    proxies_total = await db.scalar(select(func.count(ProxyConfig.id)))
    proxies_active = await db.scalar(select(func.count(ProxyConfig.id)).where(ProxyConfig.is_active == True))
    users_total = await db.scalar(select(func.count(User.id)))

    servers_result = await db.execute(
        select(Server.id, Server.name, Server.ip_address, Server.status, Server.location, Server.last_check_at)
        .order_by(Server.id).limit(10)
    )
    servers_list = [
        {
            "id": row.id,
            "name": row.name,
            "ip_address": row.ip_address,
            "status": row.status,
            "location": row.location,
            "last_check_at": row.last_check_at,
        }
        for row in servers_result.all()
    ]

    from sqlalchemy import text
    protocol_rows = await db.execute(
        select(VpnProfile.active_protocol, func.count(VpnProfile.id).label("count"))
        .group_by(VpnProfile.active_protocol)
    )
    protocols_distribution = [
        {"protocol": row.active_protocol, "count": row.count}
        for row in protocol_rows.all()
    ]

    return {
        "servers": {"total": servers_total, "online": servers_online},
        "clients": {"total": clients_total},
        "vpn_profiles": {"total": profiles_total, "active": profiles_active},
        "proxies": {"total": proxies_total, "active": proxies_active},
        "users": {"total": users_total},
        "servers_list": servers_list,
        "protocols_distribution": protocols_distribution,
    }
