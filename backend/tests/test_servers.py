"""
Тесты эндпоинтов серверов: /api/servers

SSH-зависимые операции (test-connection, install-protocol, uninstall-protocol)
тестируются на уровне авторизации и валидации, без реального SSH-соединения.
"""
from unittest.mock import patch


SERVER_PAYLOAD = {
    "name": "Test Server",
    "ip_address": "10.0.0.99",
    "ssh_port": 22,
    "ssh_user": "root",
    "ssh_password": "secret",
    "os_type": "ubuntu",
    "location": "Test DC",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_server(client, auth_headers, payload=None):
    data = payload or SERVER_PAYLOAD.copy()
    resp = client.post("/api/servers", json=data, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _delete_server(client, auth_headers, server_id):
    client.delete(f"/api/servers/{server_id}", headers=auth_headers)


# ---------------------------------------------------------------------------
# GET /api/servers
# ---------------------------------------------------------------------------

def test_list_servers(client, auth_headers):
    """Список серверов возвращается без ошибок."""
    resp = client.get("/api/servers", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_servers_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/servers")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/servers
# ---------------------------------------------------------------------------

def test_create_server(client, auth_headers):
    """Успешное создание сервера."""
    server = _create_server(client, auth_headers)
    assert server["name"] == SERVER_PAYLOAD["name"]
    assert server["ip_address"] == SERVER_PAYLOAD["ip_address"]
    assert "id" in server
    _delete_server(client, auth_headers, server["id"])


def test_create_server_missing_required(client, auth_headers):
    """Создание без обязательных полей — 422."""
    resp = client.post("/api/servers", json={"name": "only name"}, headers=auth_headers)
    assert resp.status_code == 422


def test_create_server_unauthenticated(client):
    """Без токена — 401."""
    resp = client.post("/api/servers", json=SERVER_PAYLOAD)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/servers/{server_id}
# ---------------------------------------------------------------------------

def test_get_server(client, auth_headers):
    """Получение сервера по ID."""
    server = _create_server(client, auth_headers)
    resp = client.get(f"/api/servers/{server['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == server["id"]
    _delete_server(client, auth_headers, server["id"])


def test_get_server_not_found(client, auth_headers):
    """Несуществующий сервер — 404."""
    resp = client.get("/api/servers/999999", headers=auth_headers)
    assert resp.status_code == 404


def test_get_server_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/servers/1")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/servers/{server_id}
# ---------------------------------------------------------------------------

def test_update_server(client, auth_headers):
    """Обновление полей сервера."""
    server = _create_server(client, auth_headers)
    resp = client.patch(
        f"/api/servers/{server['id']}",
        json={"name": "Updated Name", "location": "New DC"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
    assert resp.json()["location"] == "New DC"
    _delete_server(client, auth_headers, server["id"])


def test_update_server_not_found(client, auth_headers):
    """Обновление несуществующего сервера — 404."""
    resp = client.patch("/api/servers/999999", json={"name": "X"}, headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/servers/{server_id}
# ---------------------------------------------------------------------------

def test_delete_server(client, auth_headers):
    """Удаление сервера."""
    server = _create_server(client, auth_headers)
    del_resp = client.delete(f"/api/servers/{server['id']}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/servers/{server['id']}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_delete_server_not_found(client, auth_headers):
    """Удаление несуществующего сервера — 404."""
    resp = client.delete("/api/servers/999999", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/servers/check-all
# ---------------------------------------------------------------------------

def test_check_all_servers(client, auth_headers):
    """check-all запускает фоновую проверку и возвращает count."""
    resp = client.post("/api/servers/check-all", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data


def test_check_all_servers_unauthenticated(client):
    """Без токена — 401."""
    resp = client.post("/api/servers/check-all")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/servers/{server_id}/test-connection
# SSH мокируется — реальный коннект не выполняется
# ---------------------------------------------------------------------------

def test_test_server_connection_not_found(client, auth_headers):
    """test-connection для несуществующего сервера — 404."""
    resp = client.post("/api/servers/999999/test-connection", headers=auth_headers)
    assert resp.status_code == 404


def test_test_server_connection_mocked(client, auth_headers):
    """test-connection возвращает success/message (SSH замокирован)."""
    server = _create_server(client, auth_headers)
    with patch("app.services.ssh.test_connection", return_value=(False, "SSH mocked")):
        resp = client.post(
            f"/api/servers/{server['id']}/test-connection", headers=auth_headers
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data
    assert "message" in data
    _delete_server(client, auth_headers, server["id"])


def test_test_server_connection_unauthenticated(client):
    """Без токена — 401."""
    resp = client.post("/api/servers/1/test-connection")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/servers/{server_id}/install-protocol
# ---------------------------------------------------------------------------

def test_install_protocol_not_found(client, auth_headers):
    """install-protocol для несуществующего сервера — 404."""
    resp = client.post(
        "/api/servers/999999/install-protocol?protocol=wireguard",
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_install_protocol_mocked(client, auth_headers):
    """install-protocol вызывает SSH и возвращает success/message (замокировано)."""
    server = _create_server(client, auth_headers)
    with patch("app.services.wireguard.install_wireguard", return_value=(True, "WireGuard installed")):
        resp = client.post(
            f"/api/servers/{server['id']}/install-protocol?protocol=wireguard",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data
    _delete_server(client, auth_headers, server["id"])


def test_install_protocol_unauthenticated(client):
    """Без токена — 401."""
    resp = client.post("/api/servers/1/install-protocol?protocol=wireguard")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/servers/{server_id}/install-protocols
# ---------------------------------------------------------------------------

def test_install_protocols_empty_list(client, auth_headers):
    """Пустой список протоколов — 422."""
    server = _create_server(client, auth_headers)
    resp = client.post(
        f"/api/servers/{server['id']}/install-protocols",
        json={"protocols": []},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    _delete_server(client, auth_headers, server["id"])


def test_install_protocols_not_found(client, auth_headers):
    """install-protocols для несуществующего сервера — 404."""
    resp = client.post(
        "/api/servers/999999/install-protocols",
        json={"protocols": ["wireguard"]},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_install_protocols_mocked(client, auth_headers):
    """install-protocols возвращает results[] (SSH замокирован)."""
    server = _create_server(client, auth_headers)
    with patch("app.services.wireguard.install_wireguard", return_value=(True, "ok")):
        resp = client.post(
            f"/api/servers/{server['id']}/install-protocols",
            json={"protocols": ["wireguard"]},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "success_count" in data
    assert "total" in data
    _delete_server(client, auth_headers, server["id"])


# ---------------------------------------------------------------------------
# POST /api/servers/{server_id}/uninstall-protocol
# ---------------------------------------------------------------------------

def test_uninstall_protocol_not_found(client, auth_headers):
    """uninstall-protocol для несуществующего сервера — 404."""
    resp = client.post(
        "/api/servers/999999/uninstall-protocol",
        json={"protocol": "wireguard"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_uninstall_protocol_mocked(client, auth_headers):
    """uninstall-protocol возвращает success/message (SSH замокирован)."""
    server = _create_server(client, auth_headers)
    with patch("app.services.ssh.execute_command", return_value=("WireGuard удалён", "", 0)):
        resp = client.post(
            f"/api/servers/{server['id']}/uninstall-protocol",
            json={"protocol": "wireguard"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data
    _delete_server(client, auth_headers, server["id"])


def test_uninstall_protocol_unauthenticated(client):
    """Без токена — 401."""
    resp = client.post("/api/servers/1/uninstall-protocol", json={"protocol": "wireguard"})
    assert resp.status_code == 401
