import asyncio
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.proxy import ProxyConfig, ProxyType
from app.models.server import Server
from app.models.user import User
from app.schemas.proxy import ProxyConfigCreate, ProxyConfigUpdate, ProxyConfigRead
from app.routers.deps import get_current_active_user, require_manager

router = APIRouter(prefix="/api/proxies", tags=["proxies"])


@router.get("", response_model=List[ProxyConfigRead])
async def list_proxies(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
    client_id: int = None,
    user_id: int = None,
):
    query = select(ProxyConfig).order_by(ProxyConfig.id)
    if client_id:
        query = query.where(ProxyConfig.client_id == client_id)
    if user_id:
        query = query.where(ProxyConfig.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ProxyConfigRead, status_code=status.HTTP_201_CREATED)
async def create_proxy(
    payload: ProxyConfigCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    server_result = await db.execute(select(Server).where(Server.id == payload.server_id))
    server = server_result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    from app.services.proxy_service import generate_password
    if not payload.password:
        payload = payload.model_copy(update={"password": generate_password()})

    proxy = ProxyConfig(**payload.model_dump())
    db.add(proxy)
    await db.commit()
    await db.refresh(proxy)
    return proxy


@router.get("/{proxy_id}", response_model=ProxyConfigRead)
async def get_proxy(
    proxy_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
):
    result = await db.execute(select(ProxyConfig).where(ProxyConfig.id == proxy_id))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return proxy


@router.patch("/{proxy_id}", response_model=ProxyConfigRead)
async def update_proxy(
    proxy_id: int,
    payload: ProxyConfigUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    result = await db.execute(select(ProxyConfig).where(ProxyConfig.id == proxy_id))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(proxy, field, value)
    await db.commit()
    await db.refresh(proxy)
    return proxy


@router.delete("/{proxy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proxy(
    proxy_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    result = await db.execute(select(ProxyConfig).where(ProxyConfig.id == proxy_id))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    await db.delete(proxy)
    await db.commit()


@router.post("/{proxy_id}/deploy")
async def deploy_proxy(
    proxy_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    result = await db.execute(select(ProxyConfig).where(ProxyConfig.id == proxy_id))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    server_result = await db.execute(select(Server).where(Server.id == proxy.server_id))
    server = server_result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    def _deploy():
        from app.services.proxy_service import setup_3proxy, setup_shadowsocks, setup_trojango
        if proxy.proxy_type in (ProxyType.HTTP, ProxyType.HTTPS, ProxyType.SOCKS5):
            return setup_3proxy(server, proxy.proxy_type.value, proxy.port, proxy.username or "vpnuser", proxy.password or "")
        elif proxy.proxy_type == ProxyType.SHADOWSOCKS:
            method = (proxy.config_data or {}).get("method", "aes-256-gcm")
            return setup_shadowsocks(server, proxy.port, proxy.password or "", method)
        elif proxy.proxy_type == ProxyType.TROJAN:
            cert = (proxy.config_data or {}).get("cert_path", "/etc/ssl/certs/ssl-cert-snakeoil.pem")
            key = (proxy.config_data or {}).get("key_path", "/etc/ssl/private/ssl-cert-snakeoil.key")
            return setup_trojango(server, proxy.port, proxy.password or "", cert, key)
        return False, "Unsupported proxy type for direct deployment"

    loop = asyncio.get_event_loop()
    ok, message = await loop.run_in_executor(None, _deploy)
    return {"success": ok, "message": message}


@router.get("/{proxy_id}/share-link")
async def get_share_link(
    proxy_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
):
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(ProxyConfig).where(ProxyConfig.id == proxy_id).options(selectinload(ProxyConfig.server))
    )
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    from app.services.proxy_service import build_proxy_share_link, generate_proxy_qr
    link = build_proxy_share_link(proxy)
    qr = generate_proxy_qr(link) if link else ""
    return {"link": link, "qr_base64": qr}
