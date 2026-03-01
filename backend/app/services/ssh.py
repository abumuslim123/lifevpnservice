import io
import paramiko
from typing import Tuple, Optional
from app.models.server import Server


def get_ssh_client(server: Server) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict = {
        "hostname": server.ip_address,
        "port": server.ssh_port,
        "username": server.ssh_user,
        "timeout": 15,
    }

    if server.ssh_private_key:
        key_file = io.StringIO(server.ssh_private_key)
        try:
            pkey = paramiko.RSAKey.from_private_key(key_file)
        except paramiko.SSHException:
            key_file.seek(0)
            pkey = paramiko.Ed25519Key.from_private_key(key_file)
        connect_kwargs["pkey"] = pkey
    elif server.ssh_password:
        connect_kwargs["password"] = server.ssh_password

    client.connect(**connect_kwargs)
    return client


def execute_command(server: Server, command: str) -> Tuple[str, str, int]:
    client = get_ssh_client(server)
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=60)
        exit_code = stdout.channel.recv_exit_status()
        return stdout.read().decode("utf-8", errors="replace"), stderr.read().decode("utf-8", errors="replace"), exit_code
    finally:
        client.close()


def upload_file(server: Server, remote_path: str, content: str) -> None:
    client = get_ssh_client(server)
    try:
        sftp = client.open_sftp()
        with sftp.open(remote_path, "w") as f:
            f.write(content)
        sftp.close()
    finally:
        client.close()


def test_connection(server: Server) -> Tuple[bool, str]:
    try:
        stdout, stderr, code = execute_command(server, "echo OK")
        if code == 0 and "OK" in stdout:
            return True, "Connection successful"
        return False, stderr or "Unknown error"
    except Exception as e:
        return False, str(e)
