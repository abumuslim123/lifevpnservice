import asyncio
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.vpn_profile import VpnProfile
from app.models.server import Server
from app.models.user import User
from app.models.protocol_config import ProtocolType
from app.schemas.vpn_profile import VpnProfileCreate, VpnProfileUpdate, VpnProfileRead, SwitchProtocolRequest
from app.routers.deps import get_current_active_user, require_manager

router = APIRouter(prefix="/api/vpn-profiles", tags=["vpn-profiles"])


async def _get_or_404(db: AsyncSession, profile_id: int) -> VpnProfile:
    result = await db.execute(select(VpnProfile).where(VpnProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="VPN profile not found")
    return profile


@router.get("", response_model=List[VpnProfileRead])
async def list_profiles(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
    client_id: int = None,
    user_id: int = None,
):
    query = select(VpnProfile).order_by(VpnProfile.id)
    if client_id:
        query = query.where(VpnProfile.client_id == client_id)
    if user_id:
        query = query.where(VpnProfile.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=VpnProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: VpnProfileCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    server_result = await db.execute(select(Server).where(Server.id == payload.server_id))
    server = server_result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    profile = VpnProfile(
        name=payload.name,
        server_id=payload.server_id,
        active_protocol=payload.active_protocol,
        enabled_protocols=payload.enabled_protocols or [payload.active_protocol],
        client_id=payload.client_id,
        user_id=payload.user_id,
        is_active=payload.is_active,
        notes=payload.notes,
    )

    def _generate_creds():
        proto = payload.active_protocol.value
        if proto == "wireguard":
            from app.services.wireguard import create_profile_credentials
            proto_cfg = {"server_public_key": (server.installed_protocols or {}).get("wg_public_key", "")}
            return create_profile_credentials(server, proto_cfg.get("server_public_key", ""), server.ip_address, 51820)
        elif proto == "amnezia_wg":
            from app.services.amnezia import create_awg_profile_credentials
            pub = (server.installed_protocols or {}).get("awg_public_key", "")
            return create_awg_profile_credentials(server, pub, 51821)
        elif proto == "xray_vless":
            from app.services.xray import create_vless_profile_credentials
            return create_vless_profile_credentials(server.ip_address, 443)
        elif proto == "xray_vmess":
            from app.services.xray import create_vmess_profile_credentials
            return create_vmess_profile_credentials(server.ip_address, 10086)
        elif proto == "xray_trojan":
            from app.services.xray import create_trojan_profile_credentials
            return create_trojan_profile_credentials(server.ip_address, 443)
        elif proto == "xray_shadowsocks":
            from app.services.xray import create_shadowsocks_profile_credentials
            return create_shadowsocks_profile_credentials(server.ip_address, 8388)
        elif proto == "openvpn":
            return {"client_name": payload.name.replace(" ", "_")}
        return {}

    loop = asyncio.get_event_loop()
    creds = await loop.run_in_executor(None, _generate_creds)
    profile.credentials = creds

    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/{profile_id}", response_model=VpnProfileRead)
async def get_profile(
    profile_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
):
    return await _get_or_404(db, profile_id)


@router.patch("/{profile_id}", response_model=VpnProfileRead)
async def update_profile(
    profile_id: int,
    payload: VpnProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    profile = await _get_or_404(db, profile_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    profile = await _get_or_404(db, profile_id)
    await db.delete(profile)
    await db.commit()


@router.patch("/{profile_id}/switch-protocol", response_model=VpnProfileRead)
async def switch_protocol(
    profile_id: int,
    payload: SwitchProtocolRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    profile = await _get_or_404(db, profile_id)
    server_result = await db.execute(select(Server).where(Server.id == profile.server_id))
    server = server_result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    proto = payload.protocol.value

    def _regen_creds():
        if proto == "wireguard":
            from app.services.wireguard import create_profile_credentials
            pub = (server.installed_protocols or {}).get("wg_public_key", "")
            return create_profile_credentials(server, pub, server.ip_address, 51820)
        elif proto == "amnezia_wg":
            from app.services.amnezia import create_awg_profile_credentials
            pub = (server.installed_protocols or {}).get("awg_public_key", "")
            return create_awg_profile_credentials(server, pub, 51821)
        elif proto == "xray_vless":
            from app.services.xray import create_vless_profile_credentials
            return create_vless_profile_credentials(server.ip_address, 443)
        elif proto == "xray_vmess":
            from app.services.xray import create_vmess_profile_credentials
            return create_vmess_profile_credentials(server.ip_address, 10086)
        elif proto == "xray_trojan":
            from app.services.xray import create_trojan_profile_credentials
            return create_trojan_profile_credentials(server.ip_address, 443)
        elif proto == "xray_shadowsocks":
            from app.services.xray import create_shadowsocks_profile_credentials
            return create_shadowsocks_profile_credentials(server.ip_address, 8388)
        return profile.credentials or {}

    loop = asyncio.get_event_loop()
    new_creds = await loop.run_in_executor(None, _regen_creds)

    profile.active_protocol = payload.protocol
    profile.credentials = new_creds
    enabled = list(profile.enabled_protocols or [])
    if payload.protocol not in enabled:
        enabled.append(payload.protocol)
        profile.enabled_protocols = enabled

    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/{profile_id}/download-config")
async def download_config(
    profile_id: int,
    app: str = "wireguard",
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    _: Annotated[User, Depends(get_current_active_user)] = None,
):
    profile = await _get_or_404(db, profile_id)
    server_result = await db.execute(select(Server).where(Server.id == profile.server_id))
    server = server_result.scalar_one_or_none()

    from app.services.config_generator import generate_config
    result = generate_config(
        protocol=profile.active_protocol.value,
        credentials=profile.credentials or {},
        server_ip=server.ip_address if server else "",
        port=51820,
        app=app,
        proxy_name=profile.name,
    )
    return Response(
        content=result["content"],
        media_type=result["mime"],
        headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )
