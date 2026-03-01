from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
from datetime import datetime

from app.database import get_db, AsyncSessionLocal
from app.models.server import Server, ServerStatus
from app.models.user import User
from app.schemas.server import ServerCreate, ServerUpdate, ServerRead
from app.routers.deps import get_current_active_user, require_manager

router = APIRouter(prefix="/api/servers", tags=["servers"])


async def _background_test_connection(server_id: int) -> None:
    """Проверяет SSH-соединение в фоне и обновляет статус сервера."""
    loop = asyncio.get_event_loop()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Server).where(Server.id == server_id))
        server = result.scalar_one_or_none()
        if not server:
            return
        server.status = ServerStatus.CONNECTING
        await db.commit()

        def _test():
            from app.services.ssh import test_connection
            return test_connection(server)

        try:
            ok, _ = await loop.run_in_executor(None, _test)
            server.status = ServerStatus.ONLINE if ok else ServerStatus.OFFLINE
        except Exception:
            server.status = ServerStatus.OFFLINE

        server.last_check_at = datetime.utcnow()
        await db.commit()


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
    await db.delete(server)
    await db.commit()


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
    except Exception as e:
        ok, message = False, str(e)
        server.status = ServerStatus.OFFLINE

    server.last_check_at = datetime.utcnow()
    await db.commit()
    return {"success": ok, "message": message}


def _run_install(server: Server, protocol: str) -> tuple[bool, str]:
    """Запускает установку одного протокола через SSH."""
    if protocol == "wireguard":
        from app.services.wireguard import install_wireguard
        return install_wireguard(server)
    elif protocol in ("xray_vless", "xray_vmess", "xray_trojan", "xray_shadowsocks"):
        from app.services.xray import install_xray
        return install_xray(server)
    elif protocol == "openvpn":
        from app.services.openvpn import install_openvpn
        return install_openvpn(server)
    elif protocol == "ikev2":
        from app.services.ikev2 import setup_ikev2
        return setup_ikev2(server, server.ip_address)
    elif protocol == "l2tp":
        from app.services.ikev2 import setup_l2tp
        import secrets, string
        psk = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24))
        return setup_l2tp(server, psk)
    elif protocol == "amnezia_wg":
        from app.services.amnezia import install_amneziawg
        return install_amneziawg(server)
    return False, f"Протокол не поддерживается: {protocol}"


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
    ok, message = await loop.run_in_executor(None, _run_install, server, protocol)

    if ok:
        installed = dict(server.installed_protocols or {})
        installed[protocol] = True
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
            ok, message = await loop.run_in_executor(None, _run_install, server, proto)
            if ok:
                xray_installed = True
                # Помечаем все xray-протоколы как установленные вместе с xray-core
                for xp in xray_protocols:
                    if xp in requested:
                        installed[xp] = True
        else:
            ok, message = await loop.run_in_executor(None, _run_install, server, proto)
            if ok:
                installed[proto] = True

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
            # Удаляем все xray-метки вместе с xray-core
            for xp in xray_protocols:
                installed.pop(xp, None)
        else:
            installed.pop(protocol, None)
        server.installed_protocols = installed
        await db.commit()

    return {"success": ok, "message": message}
