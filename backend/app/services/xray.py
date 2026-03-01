import json
import uuid
import secrets
import string
from typing import Dict, Any, Tuple
from app.models.server import Server
from app.services.ssh import execute_command, upload_file


XRAY_INSTALL_SCRIPT = "bash -c \"$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)\" @ install"


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def build_vless_server_config(port: int, users: list[Dict[str, str]], reality_public_key: str = "", reality_short_id: str = "") -> Dict[str, Any]:
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": port,
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": u["uuid"], "flow": "xtls-rprx-vision"} for u in users],
                    "decryption": "none",
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "show": False,
                        "dest": "www.microsoft.com:443",
                        "xver": 0,
                        "serverNames": ["www.microsoft.com"],
                        "privateKey": reality_public_key,
                        "shortIds": [reality_short_id or secrets.token_hex(8)],
                    },
                },
            }
        ],
        "outbounds": [
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "blocked"},
        ],
    }


def build_vmess_server_config(port: int, users: list[Dict[str, str]], ws_path: str = "/vmess") -> Dict[str, Any]:
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": port,
                "protocol": "vmess",
                "settings": {
                    "clients": [{"id": u["uuid"], "alterId": 0} for u in users],
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": {"path": ws_path},
                },
            }
        ],
        "outbounds": [{"protocol": "freedom"}],
    }


def build_trojan_server_config(port: int, users: list[Dict[str, str]]) -> Dict[str, Any]:
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": port,
                "protocol": "trojan",
                "settings": {
                    "clients": [{"password": u["password"]} for u in users],
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "tls",
                    "tlsSettings": {
                        "certificates": [
                            {
                                "certificateFile": "/etc/xray/server.crt",
                                "keyFile": "/etc/xray/server.key",
                            }
                        ]
                    },
                },
            }
        ],
        "outbounds": [{"protocol": "freedom"}],
    }


def build_shadowsocks_server_config(port: int, password: str, method: str = "aes-256-gcm") -> Dict[str, Any]:
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": port,
                "protocol": "shadowsocks",
                "settings": {
                    "method": method,
                    "password": password,
                    "network": "tcp,udp",
                },
            }
        ],
        "outbounds": [{"protocol": "freedom"}],
    }


def install_xray(server: Server) -> Tuple[bool, str]:
    stdout, stderr, code = execute_command(
        server,
        f"curl -sSL https://github.com/XTLS/Xray-install/raw/main/install-release.sh -o /tmp/xray-install.sh && bash /tmp/xray-install.sh install 2>&1"
    )
    if code != 0:
        return False, stderr
    return True, "Xray installed successfully"


def apply_xray_config(server: Server, config: Dict[str, Any]) -> Tuple[bool, str]:
    config_json = json.dumps(config, indent=2)
    try:
        upload_file(server, "/usr/local/etc/xray/config.json", config_json)
        stdout, stderr, code = execute_command(server, "systemctl restart xray")
        if code != 0:
            return False, stderr
        execute_command(server, "systemctl enable xray")
        return True, "Xray configured and restarted"
    except Exception as e:
        return False, str(e)


def build_vless_client_link(
    server_ip: str,
    port: int,
    user_uuid: str,
    server_name: str = "www.microsoft.com",
    public_key: str = "",
    short_id: str = "",
    remark: str = "VLESS",
) -> str:
    params = f"type=tcp&security=reality&pbk={public_key}&fp=chrome&sni={server_name}&sid={short_id}&spx=%2F&flow=xtls-rprx-vision"
    return f"vless://{user_uuid}@{server_ip}:{port}?{params}#{remark}"


def build_vmess_client_link(server_ip: str, port: int, user_uuid: str, ws_path: str = "/vmess", remark: str = "VMess") -> str:
    import base64
    config = {
        "v": "2",
        "ps": remark,
        "add": server_ip,
        "port": str(port),
        "id": user_uuid,
        "aid": "0",
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": "",
        "path": ws_path,
        "tls": "",
        "sni": "",
        "alpn": "",
    }
    encoded = base64.b64encode(json.dumps(config).encode()).decode()
    return f"vmess://{encoded}"


def build_trojan_client_link(server_ip: str, port: int, password: str, sni: str = "", remark: str = "Trojan") -> str:
    return f"trojan://{password}@{server_ip}:{port}?sni={sni}#{remark}"


def build_shadowsocks_client_link(server_ip: str, port: int, password: str, method: str = "aes-256-gcm", remark: str = "SS") -> str:
    import base64
    userinfo = base64.b64encode(f"{method}:{password}".encode()).decode()
    return f"ss://{userinfo}@{server_ip}:{port}#{remark}"


def create_vless_profile_credentials(server_ip: str, port: int) -> Dict[str, Any]:
    user_uuid = generate_uuid()
    link = build_vless_client_link(server_ip, port, user_uuid)
    return {
        "uuid": user_uuid,
        "link": link,
        "protocol": "vless",
    }


def create_vmess_profile_credentials(server_ip: str, port: int) -> Dict[str, Any]:
    user_uuid = generate_uuid()
    link = build_vmess_client_link(server_ip, port, user_uuid)
    return {
        "uuid": user_uuid,
        "link": link,
        "protocol": "vmess",
    }


def create_trojan_profile_credentials(server_ip: str, port: int) -> Dict[str, Any]:
    password = generate_password(24)
    link = build_trojan_client_link(server_ip, port, password)
    return {
        "password": password,
        "link": link,
        "protocol": "trojan",
    }


def create_shadowsocks_profile_credentials(server_ip: str, port: int) -> Dict[str, Any]:
    password = generate_password(24)
    method = "aes-256-gcm"
    link = build_shadowsocks_client_link(server_ip, port, password, method)
    return {
        "password": password,
        "method": method,
        "link": link,
        "protocol": "shadowsocks",
    }
