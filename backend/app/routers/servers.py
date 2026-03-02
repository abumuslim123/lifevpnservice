import asyncio
import json
from datetime import datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, AsyncSessionLocal
from app.models.server import Server, ServerStatus
from app.models.user import User
from app.models.vpn_profile import VpnProfile
from app.schemas.server import ServerCreate, ServerUpdate, ServerRead
from app.routers.deps import get_current_active_user, require_manager, get_user_from_query_token
from app.utils.sse import broadcaster
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/servers", tags=["servers"])
logger = get_logger(__name__)


async def _background_test_connection(server_id: int) -> None:
    """Проверяет SSH-соединение в фоне и обновляет статус сервера."""
    loop = asyncio.get_event_loop()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Server).where(Server.id == server_id))
        server = result.scalar_one_or_none()
        if not server:
            return

        logger.info("SSH check started", extra={"server_id": server_id, "ip": server.ip_address})
        server.status = ServerStatus.CONNECTING
        await db.commit()

        def _test():
            from app.services.ssh import test_connection
            return test_connection(server)

        try:
            ok, msg = await loop.run_in_executor(None, _test)
            server.status = ServerStatus.ONLINE if ok else ServerStatus.OFFLINE
            logger.info(
                "SSH check finished",
                extra={"server_id": server_id, "status": server.status.value, "ssh_msg": msg},
            )
        except Exception as exc:
            server.status = ServerStatus.OFFLINE
            logger.error(
                "SSH check exception",
                extra={"server_id": server_id, "error": str(exc)},
                exc_info=True,
            )

        server.last_check_at = datetime.utcnow()
        await db.commit()

        await broadcaster.broadcast({
            "type": "status_update",
            "server_id": server_id,
            "status": server.status.value,
            "last_check_at": server.last_check_at.isoformat(),
        })


@router.get("/status/stream")
async def server_status_stream(
    _: Annotated[User, Depends(get_user_from_query_token)],
):
    """SSE-поток обновлений статуса серверов. Подключаться с ?token=<JWT>."""
    q = broadcaster.subscribe()

    async def event_generator():
        try:
            while True:
                try:
                    data = await asyncio.wait_for(q.get(), timeout=25)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            broadcaster.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("", response_model=List[ServerRead])
async def list_servers(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
):
    result = await db.execute(select(Server).order_by(Server.id))
    return result.scalars().all()


@router.post("", response_model=ServerRead, status_code=status.HTTP_201_CREATED)
async def create_server(
    payload: ServerCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    server = Server(**payload.model_dump())
    db.add(server)
    await db.commit()
    await db.refresh(server)
    logger.info("Server created", extra={"server_id": server.id, "ip": server.ip_address})
    # Запускаем проверку SSH-соединения в фоне сразу после добавления
    background_tasks.add_task(_background_test_connection, server.id)
    return server


@router.get("/{server_id}", response_model=ServerRead)
async def get_server(
    server_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_active_user)],
):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.patch("/{server_id}", response_model=ServerRead)
async def update_server(
    server_id: int,
    payload: ServerUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(server, field, value)
    await db.commit()
    await db.refresh(server)
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    server_ip = server.ip_address

    # Деактивируем все VPN профили сервера (server_id → NULL, is_active → False)
    profiles_result = await db.execute(select(VpnProfile).where(VpnProfile.server_id == server_id))
    profiles = profiles_result.scalars().all()
    for p in profiles:
        p.server_id = None
        p.is_active = False
    if profiles:
        await db.flush()
        logger.info("Deactivated profiles on server delete", extra={"server_id": server_id, "count": len(profiles)})

    await db.delete(server)
    await db.commit()
    logger.info("Server deleted", extra={"server_id": server_id, "ip": server_ip})


@router.post("/check-all")
async def check_all_servers(
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    """Запускает фоновую проверку всех активных серверов."""
    result = await db.execute(select(Server).where(Server.is_active == True))
    servers = result.scalars().all()
    for s in servers:
        background_tasks.add_task(_background_test_connection, s.id)
    return {"message": f"Запущена проверка {len(servers)} серверов", "count": len(servers)}


@router.post("/{server_id}/test-connection")
async def test_server_connection(
    server_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    server.status = ServerStatus.CONNECTING
    await db.commit()

    def _test():
        from app.services.ssh import test_connection
        return test_connection(server)

    try:
        loop = asyncio.get_event_loop()
        ok, message = await loop.run_in_executor(None, _test)
        server.status = ServerStatus.ONLINE if ok else ServerStatus.OFFLINE
        logger.info(
            "SSH test finished",
            extra={"server_id": server_id, "status": server.status.value, "ssh_msg": message},
        )
    except Exception as exc:
        ok, message = False, str(exc)
        server.status = ServerStatus.OFFLINE
        logger.error(
            "SSH test exception",
            extra={"server_id": server_id, "error": message},
            exc_info=True,
        )

    server.last_check_at = datetime.utcnow()
    await db.commit()

    await broadcaster.broadcast({
        "type": "status_update",
        "server_id": server_id,
        "status": server.status.value,
        "last_check_at": server.last_check_at.isoformat(),
    })

    return {"success": ok, "message": message}


def _run_install(server: Server, protocol: str) -> tuple[bool, str, dict]:
    """Запускает установку одного протокола через SSH.
    Возвращает (success, message, extra_data) где extra_data сохраняется в installed_protocols."""
    if protocol == "wireguard":
        from app.services.wireguard import install_wireguard, get_server_public_key
        ok, msg = install_wireguard(server)
        extra: dict = {}
        if ok:
            pub = get_server_public_key(server)
            if pub:
                extra["wg_public_key"] = pub
        return ok, msg, extra
    elif protocol == "amnezia_wg":
        from app.services.amnezia import install_amneziawg
        from app.services.wireguard import get_server_public_key
        ok, msg = install_amneziawg(server)
        extra = {}
        if ok:
            pub = get_server_public_key(server, interface="awg0")
            if pub:
                extra["awg_public_key"] = pub
        return ok, msg, extra
    elif protocol in ("xray_vless", "xray_vmess", "xray_trojan", "xray_shadowsocks"):
        from app.services.xray import install_xray
        ok, msg = install_xray(server)
        return ok, msg, {}
    elif protocol == "openvpn":
        from app.services.openvpn import install_openvpn
        ok, msg = install_openvpn(server)
        return ok, msg, {}
    elif protocol == "ikev2":
        from app.services.ikev2 import setup_ikev2
        ok, msg = setup_ikev2(server, server.ip_address)
        return ok, msg, {}
    elif protocol == "l2tp":
        from app.services.ikev2 import setup_l2tp
        import secrets, string
        psk = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24))
        ok, msg = setup_l2tp(server, psk)
        return ok, msg, {"l2tp_psk": psk} if ok else {}
    return False, f"Протокол не поддерживается: {protocol}", {}


@router.post("/{server_id}/install-protocol")
async def install_protocol(
    server_id: int,
    protocol: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    """Установить один протокол (legacy)."""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    loop = asyncio.get_event_loop()
    ok, message, extra = await loop.run_in_executor(None, _run_install, server, protocol)

    if ok:
        installed = dict(server.installed_protocols or {})
        installed[protocol] = True
        installed.update(extra)
        server.installed_protocols = installed
        await db.commit()

    return {"success": ok, "message": message}


class InstallProtocolsRequest(BaseModel):
    protocols: list[str]


@router.post("/{server_id}/install-protocols")
async def install_protocols(
    server_id: int,
    payload: InstallProtocolsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    """Установить несколько протоколов последовательно. Возвращает результат по каждому."""
    if not payload.protocols:
        raise HTTPException(status_code=422, detail="Список протоколов пуст")

    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    # Xray-группа — устанавливается один раз для всех xray_* протоколов
    xray_protocols = {"xray_vless", "xray_vmess", "xray_trojan", "xray_shadowsocks"}
    requested = list(dict.fromkeys(payload.protocols))  # убираем дубли, сохраняя порядок

    installed = dict(server.installed_protocols or {})
    results = []
    xray_installed = False  # флаг чтобы не ставить xray дважды

    loop = asyncio.get_event_loop()

    for proto in requested:
        # Для xray-протоколов достаточно одной установки xray-core
        if proto in xray_protocols:
            if xray_installed or all(p in xray_protocols and installed.get(p) for p in [proto]):
                if xray_installed:
                    installed[proto] = True
                    results.append({"protocol": proto, "success": True, "message": "Xray уже установлен"})
                    continue
            ok, message, extra = await loop.run_in_executor(None, _run_install, server, proto)
            if ok:
                xray_installed = True
                for xp in xray_protocols:
                    if xp in requested:
                        installed[xp] = True
                installed.update(extra)
        else:
            ok, message, extra = await loop.run_in_executor(None, _run_install, server, proto)
            if ok:
                installed[proto] = True
                installed.update(extra)

        results.append({"protocol": proto, "success": ok, "message": message})

    server.installed_protocols = installed
    await db.commit()

    success_count = sum(1 for r in results if r["success"])
    return {
        "results": results,
        "success_count": success_count,
        "total": len(results),
    }


def _run_uninstall(server: Server, protocol: str) -> tuple[bool, str]:
    """Удаляет протокол с сервера через SSH."""
    from app.services.ssh import execute_command

    scripts: dict[str, str] = {
        "wireguard": """
systemctl stop wg-quick@wg0 2>/dev/null || true
systemctl disable wg-quick@wg0 2>/dev/null || true
apt-get remove -y wireguard wireguard-tools 2>&1
rm -rf /etc/wireguard
echo "WireGuard удалён"
""",
        "amnezia_wg": """
systemctl stop awg-quick@awg0 2>/dev/null || true
systemctl disable awg-quick@awg0 2>/dev/null || true
apt-get remove -y amneziawg 2>&1 || true
rm -rf /etc/amnezia /etc/wireguard/awg0.conf 2>/dev/null
echo "AmneziaWG удалён"
""",
        "xray_vless": None,   # управляется единым xray-core
        "xray_vmess": None,
        "xray_trojan": None,
        "xray_shadowsocks": None,
        "_xray_core": """
systemctl stop xray 2>/dev/null || true
systemctl disable xray 2>/dev/null || true
rm -f /usr/local/bin/xray
rm -rf /usr/local/etc/xray /etc/systemd/system/xray.service
systemctl daemon-reload
echo "Xray-core удалён"
""",
        "openvpn": """
systemctl stop openvpn-server@server 2>/dev/null || true
systemctl disable openvpn-server@server 2>/dev/null || true
apt-get remove -y openvpn easy-rsa 2>&1
rm -rf /etc/openvpn /var/log/openvpn
echo "OpenVPN удалён"
""",
        "ikev2": """
systemctl stop strongswan 2>/dev/null || true
systemctl disable strongswan 2>/dev/null || true
apt-get remove -y strongswan strongswan-pki libcharon-extra-plugins libcharon-extauth-plugins 2>&1
rm -rf /etc/ipsec.d /etc/strongswan.d
echo "IKEv2/StrongSwan удалён"
""",
        "l2tp": """
systemctl stop xl2tpd 2>/dev/null || true
systemctl disable xl2tpd 2>/dev/null || true
apt-get remove -y xl2tpd 2>&1
rm -f /etc/xl2tpd/xl2tpd.conf /etc/ppp/options.xl2tpd /etc/ipsec.conf /etc/ipsec.secrets
echo "L2TP/IPSec удалён"
""",
    }

    xray_protocols = {"xray_vless", "xray_vmess", "xray_trojan", "xray_shadowsocks"}

    if protocol in xray_protocols:
        # Xray удаляется только если это последний xray-протокол на сервере
        script = scripts["_xray_core"]
    else:
        script = scripts.get(protocol)

    if script is None:
        return False, f"Удаление протокола '{protocol}' не поддерживается"

    try:
        stdout, stderr, code = execute_command(server, script.strip())
        if code != 0:
            return False, stderr or "Ошибка выполнения скрипта"
        return True, stdout.strip().splitlines()[-1] if stdout.strip() else "Протокол удалён"
    except Exception as e:
        return False, str(e)


class UninstallProtocolRequest(BaseModel):
    protocol: str
    remove_all_xray: bool = False  # если True — удаляет xray-core даже если есть другие xray-протоколы


@router.post("/{server_id}/uninstall-protocol")
async def uninstall_protocol(
    server_id: int,
    payload: UninstallProtocolRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    """Удалить протокол с сервера."""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    protocol = payload.protocol
    xray_protocols = {"xray_vless", "xray_vmess", "xray_trojan", "xray_shadowsocks"}
    installed = dict(server.installed_protocols or {})

    # Для xray: физически удаляем xray-core только если это последний xray-протокол
    # или если явно запрошено remove_all_xray
    actually_remove_binary = True
    if protocol in xray_protocols and not payload.remove_all_xray:
        remaining_xray = [p for p in xray_protocols if p != protocol and installed.get(p)]
        if remaining_xray:
            # Просто убираем метку — бинарник не трогаем
            installed.pop(protocol, None)
            server.installed_protocols = installed
            await db.commit()
            return {"success": True, "message": f"Протокол {protocol} отмечен как удалённый (xray-core сохранён)"}
        actually_remove_binary = True

    loop = asyncio.get_event_loop()
    ok, message = await loop.run_in_executor(None, _run_uninstall, server, protocol)

    if ok:
        if protocol in xray_protocols and actually_remove_binary:
            for xp in xray_protocols:
                installed.pop(xp, None)
            # Деактивируем профили всех xray-протоколов
            affected_protos = list(xray_protocols)
        else:
            installed.pop(protocol, None)
            affected_protos = [protocol]

        server.installed_protocols = installed

        # Деактивируем VPN профили с удалённым протоколом
        from app.models.protocol_config import ProtocolType
        from sqlalchemy import and_
        for ap in affected_protos:
            try:
                proto_enum = ProtocolType(ap)
                pr_result = await db.execute(
                    select(VpnProfile).where(
                        and_(VpnProfile.server_id == server_id, VpnProfile.active_protocol == proto_enum)
                    )
                )
                deactivated = pr_result.scalars().all()
                for p in deactivated:
                    p.is_active = False
                if deactivated:
                    logger.info("Deactivated profiles on protocol uninstall", extra={
                        "server_id": server_id, "protocol": ap, "count": len(deactivated)
                    })
            except ValueError:
                pass

        await db.commit()

    return {"success": ok, "message": message}


@router.post("/{server_id}/refresh-keys")
async def refresh_server_keys(
    server_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_manager)],
):
    """Получить и сохранить публичные ключи WireGuard/AmneziaWG с сервера."""
    result = await db.execute(select(Server).where(Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    installed = dict(server.installed_protocols or {})
    updated: dict = {}
    loop = asyncio.get_event_loop()

    if installed.get("wireguard"):
        def _get_wg():
            from app.services.wireguard import ensure_server_config
            return ensure_server_config(server, interface="wg0", port=51820)
        pub = await loop.run_in_executor(None, _get_wg)
        if pub:
            installed["wg_public_key"] = pub
            updated["wg_public_key"] = pub

    if installed.get("amnezia_wg"):
        def _get_awg():
            from app.services.wireguard import ensure_server_config
            return ensure_server_config(server, interface="awg0", port=51821)
        pub = await loop.run_in_executor(None, _get_awg)
        if pub:
            installed["awg_public_key"] = pub
            updated["awg_public_key"] = pub

    server.installed_protocols = installed
    await db.commit()

    return {"updated": updated, "message": f"Обновлено ключей: {len(updated)}"}
