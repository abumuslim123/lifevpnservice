"""
AmneziaVPN / AmneziaWG service.
AmneziaWG is a patched WireGuard with obfuscation parameters (Jc, Jmin, Jmax, S1, S2, H1, H2, H3, H4).
The config format is compatible with WireGuard but adds extra fields.
Export format for Amnezia app is a JSON container.
"""
import json
import secrets
import base64
from typing import Dict, Any, Tuple

from app.services.wireguard import generate_keypair, generate_preshared_key
from app.models.server import Server
from app.services.ssh import execute_command, upload_file


AWG_DEFAULTS = {
    "Jc": 4,
    "Jmin": 40,
    "Jmax": 70,
    "S1": 0,
    "S2": 0,
    "H1": 1,
    "H2": 2,
    "H3": 3,
    "H4": 4,
}


def build_awg_client_config(
    client_private_key: str,
    client_address: str,
    server_public_key: str,
    server_endpoint: str,
    listen_port: int,
    preshared_key: str = "",
    dns: str = "1.1.1.1, 1.0.0.1",
    junk_params: Dict[str, int] = None,
) -> str:
    params = junk_params or AWG_DEFAULTS
    lines = [
        "[Interface]",
        f"PrivateKey = {client_private_key}",
        f"Address = {client_address}",
        f"DNS = {dns}",
        f"Jc = {params['Jc']}",
        f"Jmin = {params['Jmin']}",
        f"Jmax = {params['Jmax']}",
        f"S1 = {params['S1']}",
        f"S2 = {params['S2']}",
        f"H1 = {params['H1']}",
        f"H2 = {params['H2']}",
        f"H3 = {params['H3']}",
        f"H4 = {params['H4']}",
        "",
        "[Peer]",
        f"PublicKey = {server_public_key}",
        f"Endpoint = {server_endpoint}:{listen_port}",
        "AllowedIPs = 0.0.0.0/0, ::/0",
        "PersistentKeepalive = 25",
    ]
    if preshared_key:
        lines.insert(-1, f"PresharedKey = {preshared_key}")
    return "\n".join(lines)


def build_amnezia_export(
    client_config: str,
    container_name: str = "amnezia-awg",
    description: str = "AmneziaWG Profile",
) -> Dict[str, Any]:
    """Build Amnezia VPN JSON export container format."""
    return {
        "containers": [
            {
                "container": container_name,
                "awg": {
                    "last_config": client_config,
                    "transport_proto": "udp",
                },
            }
        ],
        "defaultContainer": container_name,
        "description": description,
    }


def export_amnezia_config(client_config: str, description: str = "AmneziaWG Profile") -> str:
    container = build_amnezia_export(client_config, description=description)
    raw_json = json.dumps(container)
    encoded = base64.b64encode(raw_json.encode()).decode()
    return f"vpn://{encoded}"


def install_amneziawg(server: Server) -> Tuple[bool, str]:
    script = """
apt-get update -qq 2>&1
apt-get install -y software-properties-common 2>&1
add-apt-repository -y ppa:amnezia/ppa 2>&1 || true
apt-get install -y amneziawg amneziawg-tools 2>&1
"""
    stdout, stderr, code = execute_command(server, script)
    if code != 0:
        return False, stderr
    return True, "AmneziaWG installed"


def create_awg_profile_credentials(
    server: Server,
    server_public_key: str,
    port: int,
    client_ip_suffix: int = 2,
) -> Dict[str, Any]:
    client_private_key, client_public_key = generate_keypair()
    preshared_key = generate_preshared_key()
    client_address = f"10.9.0.{client_ip_suffix}/32"

    config = build_awg_client_config(
        client_private_key=client_private_key,
        client_address=client_address,
        server_public_key=server_public_key,
        server_endpoint=server.ip_address,
        listen_port=port,
        preshared_key=preshared_key,
    )
    amnezia_link = export_amnezia_config(config)

    return {
        "client_private_key": client_private_key,
        "client_public_key": client_public_key,
        "client_address": client_address,
        "preshared_key": preshared_key,
        "config": config,
        "amnezia_link": amnezia_link,
    }
