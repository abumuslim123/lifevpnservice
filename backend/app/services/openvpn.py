"""
OpenVPN service — generates .ovpn client configs via SSH.
Relies on easy-rsa (pre-installed) on the remote server.
"""
import textwrap
from typing import Dict, Any, Tuple
from app.models.server import Server
from app.services.ssh import execute_command, upload_file


OPENVPN_INSTALL_SCRIPT = """
apt-get update -qq
apt-get install -y openvpn easy-rsa 2>&1
"""

OPENVPN_SERVER_CONF = """
port {port}
proto udp
dev tun
ca /etc/openvpn/server/ca.crt
cert /etc/openvpn/server/server.crt
key /etc/openvpn/server/server.key
dh /etc/openvpn/server/dh.pem
server 10.10.0.0 255.255.255.0
ifconfig-pool-persist /var/log/openvpn/ipp.txt
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 1.1.1.1"
push "dhcp-option DNS 1.0.0.1"
keepalive 10 120
tls-auth /etc/openvpn/server/ta.key 0
cipher AES-256-CBC
persist-key
persist-tun
status /var/log/openvpn/openvpn-status.log
verb 3
explicit-exit-notify 1
"""

SETUP_PKI_SCRIPT = """
set -e
mkdir -p /etc/openvpn/server
mkdir -p /var/log/openvpn

# Easy-RSA v3: копируем из системного пути или используем make-cadir
EASYRSA_DIR=/etc/openvpn/easy-rsa
rm -rf "$EASYRSA_DIR"
if [ -d /usr/share/easy-rsa ]; then
    cp -r /usr/share/easy-rsa "$EASYRSA_DIR"
else
    make-cadir "$EASYRSA_DIR"
fi

cd "$EASYRSA_DIR"

# Batch-режим: отключает интерактивный ввод CN (Easy-RSA v3)
export EASYRSA_BATCH=1
export EASYRSA_REQ_CN="VPN CA"

./easyrsa init-pki
./easyrsa build-ca nopass

export EASYRSA_REQ_CN="server"
./easyrsa build-server-full server nopass
./easyrsa gen-dh

cp pki/ca.crt       /etc/openvpn/server/ca.crt
cp pki/issued/server.crt  /etc/openvpn/server/server.crt
cp pki/private/server.key /etc/openvpn/server/server.key
cp pki/dh.pem       /etc/openvpn/server/dh.pem
openvpn --genkey secret /etc/openvpn/server/ta.key
"""


def install_openvpn(server: Server) -> Tuple[bool, str]:
    stdout, stderr, code = execute_command(server, OPENVPN_INSTALL_SCRIPT)
    if code != 0:
        return False, stderr
    stdout2, stderr2, code2 = execute_command(server, SETUP_PKI_SCRIPT)
    if code2 != 0:
        return False, stderr2
    return True, "OpenVPN installed and PKI initialized"


def create_client_cert(server: Server, client_name: str) -> Tuple[bool, str]:
    script = f"""
cd /etc/openvpn/easy-rsa
export EASYRSA_BATCH=1
export EASYRSA_REQ_CN="{client_name}"
./easyrsa build-client-full {client_name} nopass
"""
    stdout, stderr, code = execute_command(server, script)
    if code != 0:
        return False, stderr
    return True, "Client certificate created"


def get_ovpn_config(server: Server, client_name: str, port: int) -> Tuple[bool, str]:
    ok, msg = create_client_cert(server, client_name)
    if not ok:
        return False, msg

    fetch_script = f"""
cat /etc/openvpn/server/ca.crt
echo "---CERT---"
cat /etc/openvpn/easy-rsa/pki/issued/{client_name}.crt
echo "---KEY---"
cat /etc/openvpn/easy-rsa/pki/private/{client_name}.key
echo "---TA---"
cat /etc/openvpn/server/ta.key
"""
    stdout, stderr, code = execute_command(server, fetch_script)
    if code != 0:
        return False, stderr

    parts = stdout.split("---CERT---")
    ca_cert = parts[0].strip()
    rest = parts[1].split("---KEY---")
    client_cert = rest[0].strip()
    rest2 = rest[1].split("---TA---")
    client_key = rest2[0].strip()
    ta_key = rest2[1].strip() if len(rest2) > 1 else ""

    ovpn = textwrap.dedent(f"""
        client
        dev tun
        proto udp
        remote {server.ip_address} {port}
        resolv-retry infinite
        nobind
        persist-key
        persist-tun
        remote-cert-tls server
        cipher AES-256-CBC
        verb 3
        key-direction 1
        <ca>
        {ca_cert}
        </ca>
        <cert>
        {client_cert}
        </cert>
        <key>
        {client_key}
        </key>
        <tls-auth>
        {ta_key}
        </tls-auth>
    """).strip()

    return True, ovpn


def start_openvpn_server(server: Server, port: int) -> Tuple[bool, str]:
    config = OPENVPN_SERVER_CONF.format(port=port)
    try:
        upload_file(server, "/etc/openvpn/server/server.conf", config)
        execute_command(server, "systemctl start openvpn-server@server")
        execute_command(server, "systemctl enable openvpn-server@server")
        execute_command(server, "sysctl -w net.ipv4.ip_forward=1")
        return True, "OpenVPN server started"
    except Exception as e:
        return False, str(e)


def create_openvpn_profile_credentials(server: Server, client_name: str, port: int) -> Dict[str, Any]:
    ok, ovpn_or_error = get_ovpn_config(server, client_name, port)
    return {
        "client_name": client_name,
        "ovpn_config": ovpn_or_error if ok else None,
        "error": None if ok else ovpn_or_error,
    }
