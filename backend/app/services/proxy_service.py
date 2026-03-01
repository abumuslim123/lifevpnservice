"""
Proxy service — manages HTTP/SOCKS5 (3proxy), Shadowsocks (ss-server), Trojan-go proxies on remote servers.
"""
import secrets
import string
from typing import Dict, Any, Tuple

from app.models.server import Server
from app.models.proxy import ProxyType
from app.services.ssh import execute_command, upload_file


def generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ─── 3proxy (HTTP / SOCKS5) ─────────────────────────────────────────────────

THREE_PROXY_INSTALL = """
apt-get install -y 3proxy 2>&1 || (
  apt-get install -y build-essential git 2>&1 &&
  git clone https://github.com/3proxy/3proxy.git /tmp/3proxy &&
  cd /tmp/3proxy && make -f Makefile.Linux &&
  cp bin/3proxy /usr/local/bin/3proxy
)
"""


def build_3proxy_config(proxy_type: str, port: int, username: str, password: str) -> str:
    lines = [
        "nscache 65536",
        f"users {username}:CL:{password}",
        "log /var/log/3proxy.log D",
        "auth strong",
        "allow *",
    ]
    if proxy_type in ("http", "https"):
        lines.append(f"proxy -p{port}")
    else:
        lines.append(f"socks -p{port}")
    return "\n".join(lines)


def setup_3proxy(server: Server, proxy_type: str, port: int, username: str, password: str) -> Tuple[bool, str]:
    stdout, stderr, code = execute_command(server, THREE_PROXY_INSTALL)
    config = build_3proxy_config(proxy_type, port, username, password)
    try:
        upload_file(server, "/etc/3proxy/3proxy.cfg", config)
        execute_command(server, "mkdir -p /var/log && touch /var/log/3proxy.log")
        execute_command(server, "pkill 3proxy 2>/dev/null || true")
        execute_command(server, "3proxy /etc/3proxy/3proxy.cfg &")
        return True, f"{proxy_type.upper()} proxy started on port {port}"
    except Exception as e:
        return False, str(e)


# ─── Shadowsocks (ss-server) ─────────────────────────────────────────────────

SS_INSTALL = "apt-get install -y shadowsocks-libev 2>&1 || pip3 install shadowsocks 2>&1"


def setup_shadowsocks(server: Server, port: int, password: str, method: str = "aes-256-gcm") -> Tuple[bool, str]:
    import json
    config = json.dumps({
        "server": "0.0.0.0",
        "server_port": port,
        "password": password,
        "method": method,
        "timeout": 300,
        "fast_open": False,
    }, indent=2)
    stdout, stderr, code = execute_command(server, SS_INSTALL)
    try:
        upload_file(server, "/etc/shadowsocks-libev/config.json", config)
        execute_command(server, "systemctl restart shadowsocks-libev && systemctl enable shadowsocks-libev")
        return True, f"Shadowsocks started on port {port}"
    except Exception as e:
        return False, str(e)


# ─── Trojan-go ───────────────────────────────────────────────────────────────

def setup_trojango(server: Server, port: int, password: str, cert_path: str, key_path: str) -> Tuple[bool, str]:
    import json
    config = json.dumps({
        "run_type": "server",
        "local_addr": "0.0.0.0",
        "local_port": port,
        "remote_addr": "127.0.0.1",
        "remote_port": 80,
        "password": [password],
        "ssl": {
            "cert": cert_path,
            "key": key_path,
            "sni": server.ip_address,
        },
    }, indent=2)
    install_cmd = """
ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] && ARCH="amd64" || ARCH="arm64"
curl -sSL https://github.com/p4gefau1t/trojan-go/releases/latest/download/trojan-go-linux-${ARCH}.zip -o /tmp/tg.zip
cd /tmp && unzip -o tg.zip && mv trojan-go /usr/local/bin/trojan-go && chmod +x /usr/local/bin/trojan-go
"""
    execute_command(server, install_cmd)
    try:
        upload_file(server, "/etc/trojan-go/config.json", config)
        service_unit = """
[Unit]
Description=Trojan-go
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/trojan-go -config /etc/trojan-go/config.json
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
        upload_file(server, "/etc/systemd/system/trojan-go.service", service_unit)
        execute_command(server, "systemctl daemon-reload && systemctl restart trojan-go && systemctl enable trojan-go")
        return True, f"Trojan-go started on port {port}"
    except Exception as e:
        return False, str(e)


def build_proxy_share_link(proxy: Any) -> str:
    from app.models.proxy import ProxyType
    if proxy.proxy_type == ProxyType.SHADOWSOCKS:
        import base64
        method = (proxy.config_data or {}).get("method", "aes-256-gcm")
        userinfo = base64.b64encode(f"{method}:{proxy.password}".encode()).decode()
        return f"ss://{userinfo}@{proxy.server.ip_address}:{proxy.port}#{proxy.name}"
    elif proxy.proxy_type == ProxyType.TROJAN:
        return f"trojan://{proxy.password}@{proxy.server.ip_address}:{proxy.port}#{proxy.name}"
    elif proxy.proxy_type == ProxyType.SOCKS5:
        if proxy.username and proxy.password:
            return f"socks5://{proxy.username}:{proxy.password}@{proxy.server.ip_address}:{proxy.port}"
        return f"socks5://{proxy.server.ip_address}:{proxy.port}"
    elif proxy.proxy_type in (ProxyType.HTTP, ProxyType.HTTPS):
        if proxy.username and proxy.password:
            return f"http://{proxy.username}:{proxy.password}@{proxy.server.ip_address}:{proxy.port}"
        return f"http://{proxy.server.ip_address}:{proxy.port}"
    return ""


def generate_proxy_qr(share_link: str) -> str:
    """Return base64-encoded PNG QR code for the share link."""
    import qrcode
    import io
    import base64
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(share_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()
