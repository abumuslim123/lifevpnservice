"""
IKEv2/IPSec (StrongSwan) and L2TP/IPSec service.
"""
import secrets
import string
from typing import Dict, Any, Tuple
from app.models.server import Server
from app.services.ssh import execute_command, upload_file


STRONGSWAN_INSTALL = "apt-get install -y strongswan strongswan-pki libcharon-extra-plugins libcharon-extauth-plugins 2>&1"

L2TP_INSTALL = "apt-get install -y xl2tpd strongswan libcharon-extra-plugins 2>&1"


def generate_psk(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def setup_ikev2(server: Server, server_fqdn: str) -> Tuple[bool, str]:
    script = f"""
set -e
apt-get update -qq
apt-get install -y strongswan strongswan-pki libcharon-extra-plugins libcharon-extauth-plugins 2>&1
mkdir -p /etc/ipsec.d/private /etc/ipsec.d/cacerts /etc/ipsec.d/certs
ipsec pki --gen --type rsa --size 4096 --outform pem > /etc/ipsec.d/private/ca-key.pem
ipsec pki --self --ca --lifetime 3650 --in /etc/ipsec.d/private/ca-key.pem --type rsa --dn "CN=VPN CA" --outform pem > /etc/ipsec.d/cacerts/ca-cert.pem
ipsec pki --gen --type rsa --size 4096 --outform pem > /etc/ipsec.d/private/server-key.pem
ipsec pki --pub --in /etc/ipsec.d/private/server-key.pem --type rsa | ipsec pki --issue --lifetime 1825 --cacert /etc/ipsec.d/cacerts/ca-cert.pem --cakey /etc/ipsec.d/private/ca-key.pem --dn "CN={server_fqdn}" --san "{server_fqdn}" --flag serverAuth --flag ikeIntermediate --outform pem > /etc/ipsec.d/certs/server-cert.pem
"""
    stdout, stderr, code = execute_command(server, script)
    if code != 0:
        return False, stderr
    return True, "IKEv2 PKI initialized"


def create_ikev2_client(server: Server, username: str, password: str) -> Dict[str, Any]:
    script = f"""
grep -q "^{username}" /etc/ipsec.secrets 2>/dev/null || echo '{username} %any% : EAP "{password}"' >> /etc/ipsec.secrets
ipsec reload
"""
    execute_command(server, script)
    ca_cert_stdout, _, _ = execute_command(server, "cat /etc/ipsec.d/cacerts/ca-cert.pem")
    return {
        "username": username,
        "password": password,
        "ca_cert": ca_cert_stdout.strip(),
        "server_ip": server.ip_address,
    }


def setup_l2tp(server: Server, psk: str) -> Tuple[bool, str]:
    # Шаг 1: устанавливаем пакеты и создаём нужные директории
    install_script = """
set -e
apt-get update -qq
apt-get install -y xl2tpd strongswan libcharon-extra-plugins 2>&1
mkdir -p /etc/xl2tpd /etc/ppp /etc/ipsec.d
"""
    stdout, stderr, code = execute_command(server, install_script)
    if code != 0:
        return False, f"Ошибка установки пакетов L2TP: {stderr}"

    ipsec_conf = """config setup

conn %default
    ikelifetime=60m
    keylife=20m
    rekeymargin=3m
    keyingtries=1
    keyexchange=ikev1
    authby=secret

conn L2TP-PSK
    keyexchange=ikev1
    left=%defaultroute
    leftprotoport=17/1701
    right=%any
    rightprotoport=17/%any
    authby=secret
    pfs=no
    rekey=no
    type=transport
    auto=add
"""
    ipsec_secrets = f"""%any %any : PSK "{psk}"
"""
    xl2tpd_conf = """[global]
port = 1701

[lns default]
ip range = 10.11.0.100-10.11.0.200
local ip = 10.11.0.1
require chap = yes
refuse pap = yes
require authentication = yes
name = vpnserver
pppoptfile = /etc/ppp/options.xl2tpd
length bit = yes
"""
    ppp_options = """ipcp-accept-local
ipcp-accept-remote
require-mschap-v2
ms-dns 1.1.1.1
ms-dns 1.0.0.1
noccp
noauth
crtscts
idle 1800
mtu 1410
mru 1410
nodefaultroute
debug
lock
proxyarp
connect-delay 5000
"""
    try:
        upload_file(server, "/etc/ipsec.conf", ipsec_conf)
        upload_file(server, "/etc/ipsec.secrets", ipsec_secrets)
        upload_file(server, "/etc/xl2tpd/xl2tpd.conf", xl2tpd_conf)
        upload_file(server, "/etc/ppp/options.xl2tpd", ppp_options)
        execute_command(server, "systemctl restart strongswan xl2tpd && systemctl enable strongswan xl2tpd")
        return True, "L2TP/IPSec успешно настроен"
    except Exception as e:
        return False, str(e)


def add_l2tp_user(server: Server, username: str, password: str) -> Tuple[bool, str]:
    script = f"""
grep -q "^{username}" /etc/ppp/chap-secrets 2>/dev/null || echo '{username} * {password} *' >> /etc/ppp/chap-secrets
"""
    stdout, stderr, code = execute_command(server, script)
    return code == 0, stderr if code != 0 else "User added"
