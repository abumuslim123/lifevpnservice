import subprocess
import ipaddress
from typing import Dict, Any, Tuple
from app.models.server import Server
from app.services.ssh import execute_command, upload_file
from app.utils.logging import get_logger

logger = get_logger(__name__)


def generate_keypair() -> Tuple[str, str]:
    """Generate WireGuard private/public key pair locally."""
    try:
        private_key = subprocess.check_output(["wg", "genkey"]).decode().strip()
        public_key = subprocess.check_output(
            ["wg", "pubkey"], input=private_key.encode()
        ).decode().strip()
        return private_key, public_key
    except (FileNotFoundError, subprocess.CalledProcessError):
        import secrets
        import base64
        private_bytes = secrets.token_bytes(32)
        private_key = base64.b64encode(private_bytes).decode()
        try:
            result = subprocess.run(
                ["wg", "pubkey"], input=private_key.encode(), capture_output=True
            )
            public_key = result.stdout.decode().strip()
        except Exception:
            public_key = base64.b64encode(secrets.token_bytes(32)).decode()
        return private_key, public_key


def generate_preshared_key() -> str:
    try:
        return subprocess.check_output(["wg", "genpsk"]).decode().strip()
    except Exception:
        import secrets
        import base64
        return base64.b64encode(secrets.token_bytes(32)).decode()


def build_server_config(
    server_private_key: str,
    listen_port: int,
    peers: list[Dict[str, Any]],
    server_address: str = "10.8.0.1/24",
    dns: str = "1.1.1.1",
) -> str:
    lines = [
        "[Interface]",
        f"Address = {server_address}",
        f"ListenPort = {listen_port}",
        f"PrivateKey = {server_private_key}",
        "PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE",
        "PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE",
        "",
    ]
    for peer in peers:
        lines += [
            "[Peer]",
            f"PublicKey = {peer['public_key']}",
            f"AllowedIPs = {peer['allowed_ips']}",
        ]
        if peer.get("preshared_key"):
            lines.append(f"PresharedKey = {peer['preshared_key']}")
        lines.append("")
    return "\n".join(lines)


def build_client_config(
    client_private_key: str,
    client_address: str,
    server_public_key: str,
    server_endpoint: str,
    listen_port: int,
    preshared_key: str = "",
    dns: str = "1.1.1.1, 1.0.0.1",
    allowed_ips: str = "0.0.0.0/0, ::/0",
) -> str:
    lines = [
        "[Interface]",
        f"PrivateKey = {client_private_key}",
        f"Address = {client_address}",
        f"DNS = {dns}",
        "",
        "[Peer]",
        f"PublicKey = {server_public_key}",
        f"Endpoint = {server_endpoint}:{listen_port}",
        f"AllowedIPs = {allowed_ips}",
        "PersistentKeepalive = 25",
    ]
    if preshared_key:
        lines.insert(-1, f"PresharedKey = {preshared_key}")
    return "\n".join(lines)


def install_wireguard(server: Server) -> Tuple[bool, str]:
    stdout, stderr, code = execute_command(
        server,
        "apt-get update -qq && apt-get install -y wireguard wireguard-tools 2>&1"
    )
    if code != 0:
        stdout2, stderr2, code2 = execute_command(
            server,
            "yum install -y wireguard-tools 2>&1"
        )
        if code2 != 0:
            return False, stderr or stderr2
    return True, "WireGuard installed successfully"


def apply_server_config(server: Server, interface_name: str, config: str, port: int) -> Tuple[bool, str]:
    config_path = f"/etc/wireguard/{interface_name}.conf"
    try:
        upload_file(server, config_path, config)
        execute_command(server, f"chmod 600 {config_path}")
        execute_command(server, f"wg-quick down {interface_name} 2>/dev/null || true")
        stdout, stderr, code = execute_command(server, f"wg-quick up {interface_name}")
        if code != 0:
            return False, stderr
        execute_command(server, f"systemctl enable wg-quick@{interface_name}")
        execute_command(server, f"sysctl -w net.ipv4.ip_forward=1")
        execute_command(server, "echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf")
        return True, "WireGuard configured and started"
    except Exception as e:
        return False, str(e)


def add_peer_to_server(server: Server, interface_name: str, peer_public_key: str, allowed_ips: str, preshared_key: str = "") -> Tuple[bool, str]:
    cmd = f"wg set {interface_name} peer {peer_public_key} allowed-ips {allowed_ips}"
    if preshared_key:
        cmd += f" preshared-key <(echo {preshared_key})"
    stdout, stderr, code = execute_command(server, cmd)
    if code != 0:
        return False, stderr
    execute_command(server, f"wg-quick save {interface_name}")
    return True, "Peer added"


def remove_peer_from_server(server: Server, interface_name: str, peer_public_key: str) -> Tuple[bool, str]:
    stdout, stderr, code = execute_command(
        server, f"wg set {interface_name} peer {peer_public_key} remove"
    )
    if code != 0:
        return False, stderr
    execute_command(server, f"wg-quick save {interface_name}")
    return True, "Peer removed"


def get_server_public_key(server: Server, interface: str = "wg0") -> str:
    """Получить публичный ключ WireGuard сервера через SSH."""
    # Метод 1: wg show для конкретного интерфейса (интерфейс поднят)
    stdout, _, code = execute_command(server, f"wg show {interface} public-key 2>/dev/null")
    if code == 0 and stdout.strip():
        return stdout.strip()
    # Метод 2: wg show all
    stdout, _, code = execute_command(server, "wg show all public-key 2>/dev/null | awk '{print $2}' | head -1")
    if code == 0 and stdout.strip():
        return stdout.strip()
    # Метод 3: grep PrivateKey из конфига
    stdout, _, code = execute_command(
        server,
        f"grep -m1 '^PrivateKey' /etc/wireguard/{interface}.conf 2>/dev/null | awk '{{print $3}}' | wg pubkey 2>/dev/null"
    )
    if code == 0 and stdout.strip():
        return stdout.strip()
    # Метод 4: любой .conf
    stdout, _, code = execute_command(
        server,
        "f=$(ls /etc/wireguard/*.conf 2>/dev/null | head -1); [ -n \"$f\" ] && grep -m1 '^PrivateKey' \"$f\" | awk '{print $3}' | wg pubkey 2>/dev/null"
    )
    if code == 0 and stdout.strip():
        return stdout.strip()
    return ""


def ensure_server_config(server: Server, interface: str = "wg0", port: int = 51820) -> str:
    """Убедиться что серверный конфиг WireGuard существует и интерфейс поднят.
    Если конфига нет — создаёт его автоматически.
    Возвращает публичный ключ сервера."""
    # Сначала пробуем получить существующий ключ
    pub = get_server_public_key(server, interface)
    if pub:
        return pub

    # Конфига нет — создаём серверный ключ и конфиг
    logger.info("WG server config missing, initializing", extra={"server_id": server.id})
    server_private_key, server_public_key = generate_keypair()
    config = build_server_config(server_private_key, port, [], server_address="10.8.0.1/24")
    ok, msg = apply_server_config(server, interface, config, port)
    if ok:
        logger.info("WG server initialized", extra={"server_id": server.id, "pub": server_public_key[:20]})
        return server_public_key

    logger.error("WG server init failed", extra={"server_id": server.id, "msg": msg})
    return ""


def create_profile_credentials(
    server: Server,
    server_public_key: str,
    server_ip: str,
    port: int,
    client_ip_suffix: int = 2,
) -> Dict[str, Any]:
    client_private_key, client_public_key = generate_keypair()
    preshared_key = generate_preshared_key()
    client_address = f"10.8.0.{client_ip_suffix}/32"

    config = build_client_config(
        client_private_key=client_private_key,
        client_address=client_address,
        server_public_key=server_public_key,
        server_endpoint=server_ip,
        listen_port=port,
        preshared_key=preshared_key,
    )

    return {
        "client_private_key": client_private_key,
        "client_public_key": client_public_key,
        "client_address": client_address,
        "preshared_key": preshared_key,
        "config": config,
    }
