"""
Universal config generator — produces client configs for:
  • WireGuard app (.conf)
  • AmneziaVPN (vpn:// link / JSON)
  • OpenVPN (.ovpn)
  • v2rayTUN / v2rayNG (JSON)
  • Clash / Clash Meta (YAML)
  • Sing-box (JSON)
  • Shadowrocket (URI)
"""
import json
import yaml
from typing import Dict, Any, Optional


# ─── WireGuard ──────────────────────────────────────────────────────────────

def wireguard_conf(credentials: Dict[str, Any], server_ip: str, port: int) -> str:
    return credentials.get("config", "")


# ─── AmneziaVPN ─────────────────────────────────────────────────────────────

def amnezia_link(credentials: Dict[str, Any]) -> str:
    return credentials.get("amnezia_link", credentials.get("config", ""))


# ─── OpenVPN ────────────────────────────────────────────────────────────────

def openvpn_conf(credentials: Dict[str, Any]) -> str:
    return credentials.get("ovpn_config", "")


# ─── v2rayTUN / v2rayNG JSON ─────────────────────────────────────────────────

def v2ray_json(credentials: Dict[str, Any], server_ip: str, port: int, protocol: str) -> str:
    if protocol == "xray_vmess":
        return json.dumps({
            "v": "2",
            "ps": credentials.get("remark", "VMess"),
            "add": server_ip,
            "port": str(port),
            "id": credentials.get("uuid", ""),
            "aid": "0",
            "scy": "auto",
            "net": "ws",
            "type": "none",
            "host": "",
            "path": "/vmess",
            "tls": "",
        }, indent=2)
    elif protocol == "xray_vless":
        return json.dumps({
            "outbounds": [
                {
                    "protocol": "vless",
                    "settings": {
                        "vnext": [
                            {
                                "address": server_ip,
                                "port": port,
                                "users": [{"id": credentials.get("uuid", ""), "flow": "xtls-rprx-vision", "encryption": "none"}],
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "security": "reality",
                    },
                }
            ]
        }, indent=2)
    elif protocol == "xray_trojan":
        return json.dumps({
            "outbounds": [
                {
                    "protocol": "trojan",
                    "settings": {
                        "servers": [
                            {
                                "address": server_ip,
                                "port": port,
                                "password": credentials.get("password", ""),
                            }
                        ]
                    },
                    "streamSettings": {"network": "tcp", "security": "tls"},
                }
            ]
        }, indent=2)
    return "{}"


# ─── Clash / Clash Meta YAML ─────────────────────────────────────────────────

def clash_yaml(credentials: Dict[str, Any], server_ip: str, port: int, protocol: str, proxy_name: str = "VPN") -> str:
    proxy: Dict[str, Any] = {}
    if protocol == "xray_vmess":
        proxy = {
            "name": proxy_name,
            "type": "vmess",
            "server": server_ip,
            "port": port,
            "uuid": credentials.get("uuid", ""),
            "alterId": 0,
            "cipher": "auto",
            "network": "ws",
            "ws-opts": {"path": "/vmess"},
        }
    elif protocol == "xray_shadowsocks":
        proxy = {
            "name": proxy_name,
            "type": "ss",
            "server": server_ip,
            "port": port,
            "cipher": credentials.get("method", "aes-256-gcm"),
            "password": credentials.get("password", ""),
        }
    elif protocol == "xray_trojan":
        proxy = {
            "name": proxy_name,
            "type": "trojan",
            "server": server_ip,
            "port": port,
            "password": credentials.get("password", ""),
        }
    elif protocol in ("xray_vless",):
        proxy = {
            "name": proxy_name,
            "type": "vless",
            "server": server_ip,
            "port": port,
            "uuid": credentials.get("uuid", ""),
            "flow": "xtls-rprx-vision",
            "network": "tcp",
            "reality-opts": {"public-key": "", "short-id": ""},
        }

    clash_config = {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",
        "proxies": [proxy],
        "proxy-groups": [
            {"name": "PROXY", "type": "select", "proxies": [proxy_name, "DIRECT"]}
        ],
        "rules": ["MATCH,PROXY"],
    }
    return yaml.dump(clash_config, allow_unicode=True, default_flow_style=False)


# ─── Sing-box JSON ────────────────────────────────────────────────────────────

def singbox_json(credentials: Dict[str, Any], server_ip: str, port: int, protocol: str) -> str:
    outbound: Dict[str, Any] = {}
    if protocol == "xray_vmess":
        outbound = {
            "type": "vmess",
            "tag": "proxy",
            "server": server_ip,
            "server_port": port,
            "uuid": credentials.get("uuid", ""),
            "security": "auto",
            "alter_id": 0,
            "transport": {"type": "ws", "path": "/vmess"},
        }
    elif protocol == "xray_vless":
        outbound = {
            "type": "vless",
            "tag": "proxy",
            "server": server_ip,
            "server_port": port,
            "uuid": credentials.get("uuid", ""),
            "flow": "xtls-rprx-vision",
            "tls": {"enabled": True, "server_name": "www.microsoft.com", "utls": {"enabled": True, "fingerprint": "chrome"}},
        }
    elif protocol == "xray_shadowsocks":
        outbound = {
            "type": "shadowsocks",
            "tag": "proxy",
            "server": server_ip,
            "server_port": port,
            "method": credentials.get("method", "aes-256-gcm"),
            "password": credentials.get("password", ""),
        }
    elif protocol == "xray_trojan":
        outbound = {
            "type": "trojan",
            "tag": "proxy",
            "server": server_ip,
            "server_port": port,
            "password": credentials.get("password", ""),
            "tls": {"enabled": True},
        }
    elif protocol == "wireguard":
        outbound = {
            "type": "wireguard",
            "tag": "proxy",
            "server": server_ip,
            "server_port": port,
            "private_key": credentials.get("client_private_key", ""),
            "peer_public_key": credentials.get("server_public_key", ""),
            "local_address": [credentials.get("client_address", "10.8.0.2/32")],
        }

    config = {
        "log": {"level": "info"},
        "inbounds": [
            {"type": "socks", "tag": "socks-in", "listen": "127.0.0.1", "listen_port": 2080},
            {"type": "http", "tag": "http-in", "listen": "127.0.0.1", "listen_port": 2081},
        ],
        "outbounds": [outbound, {"type": "direct", "tag": "direct"}],
        "route": {"rules": [{"outbound": "direct", "ip_is_private": True}], "final": "proxy"},
    }
    return json.dumps(config, indent=2)


# ─── Shadowrocket URI ─────────────────────────────────────────────────────────

def shadowrocket_uri(credentials: Dict[str, Any]) -> str:
    return credentials.get("link", "")


# ─── Universal dispatcher ─────────────────────────────────────────────────────

def generate_config(
    protocol: str,
    credentials: Dict[str, Any],
    server_ip: str,
    port: int,
    app: str,
    proxy_name: str = "VPN",
) -> Dict[str, Any]:
    """
    app: wireguard | amnezia | openvpn | v2raytun | clashyaml | singbox | shadowrocket
    Returns {"content": str, "filename": str, "mime": str}
    """
    if app == "wireguard":
        return {"content": wireguard_conf(credentials, server_ip, port), "filename": "wg0.conf", "mime": "text/plain"}
    elif app == "amnezia":
        return {"content": amnezia_link(credentials), "filename": "amnezia.vpn", "mime": "text/plain"}
    elif app == "openvpn":
        return {"content": openvpn_conf(credentials), "filename": "client.ovpn", "mime": "text/plain"}
    elif app == "v2raytun":
        return {"content": v2ray_json(credentials, server_ip, port, protocol), "filename": "v2ray.json", "mime": "application/json"}
    elif app == "clashyaml":
        return {"content": clash_yaml(credentials, server_ip, port, protocol, proxy_name), "filename": "clash.yaml", "mime": "text/yaml"}
    elif app == "singbox":
        return {"content": singbox_json(credentials, server_ip, port, protocol), "filename": "sing-box.json", "mime": "application/json"}
    elif app == "shadowrocket":
        return {"content": shadowrocket_uri(credentials), "filename": "proxy.txt", "mime": "text/plain"}
    return {"content": "", "filename": "config.txt", "mime": "text/plain"}
