"""
Тесты эндпоинтов клиентов: /api/clients
"""
import uuid


def _uid():
    return uuid.uuid4().hex[:8]


CLIENT_PAYLOAD = {"name": "Test Client", "email": "client@example.com"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_client(client_fixture, auth_headers, payload=None):
    data = payload or {**CLIENT_PAYLOAD, "email": f"c_{_uid()}@example.com"}
    resp = client_fixture.post("/api/clients", json=data, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _delete_client(client_fixture, auth_headers, client_id):
    client_fixture.delete(f"/api/clients/{client_id}", headers=auth_headers)


# ---------------------------------------------------------------------------
# GET /api/clients
# ---------------------------------------------------------------------------

def test_list_clients(client, auth_headers):
    """Список клиентов возвращается без ошибок."""
    resp = client.get("/api/clients", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_clients_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/clients")
    assert resp.status_code == 401


def test_list_clients_search(client, auth_headers):
    """Поиск по имени/email работает."""
    c = _create_client(client, auth_headers, {"name": f"SearchMe_{_uid()}", "email": f"s_{_uid()}@x.com"})
    resp = client.get(f"/api/clients?search=SearchMe", headers=auth_headers)
    assert resp.status_code == 200
    _delete_client(client, auth_headers, c["id"])


def test_list_clients_pagination(client, auth_headers):
    """skip и limit работают корректно."""
    resp = client.get("/api/clients?skip=0&limit=5", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) <= 5


# ---------------------------------------------------------------------------
# POST /api/clients
# ---------------------------------------------------------------------------

def test_create_client(client, auth_headers):
    """Успешное создание клиента."""
    payload = {"name": f"Client_{_uid()}", "email": f"{_uid()}@test.com"}
    resp = client.post("/api/clients", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == payload["name"]
    assert "id" in data
    _delete_client(client, auth_headers, data["id"])


def test_create_client_minimal(client, auth_headers):
    """Создание клиента только с именем (email необязателен)."""
    resp = client.post("/api/clients", json={"name": f"MinClient_{_uid()}"}, headers=auth_headers)
    assert resp.status_code == 201
    _delete_client(client, auth_headers, resp.json()["id"])


def test_create_client_missing_name(client, auth_headers):
    """Создание без имени — 422."""
    resp = client.post("/api/clients", json={"email": "x@x.com"}, headers=auth_headers)
    assert resp.status_code == 422


def test_create_client_unauthenticated(client):
    """Без токена — 401."""
    resp = client.post("/api/clients", json=CLIENT_PAYLOAD)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/clients/{client_id}
# ---------------------------------------------------------------------------

def test_get_client(client, auth_headers):
    """Получение клиента по ID."""
    c = _create_client(client, auth_headers)
    resp = client.get(f"/api/clients/{c['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == c["id"]
    _delete_client(client, auth_headers, c["id"])


def test_get_client_not_found(client, auth_headers):
    """Несуществующий клиент — 404."""
    resp = client.get("/api/clients/999999", headers=auth_headers)
    assert resp.status_code == 404


def test_get_client_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/clients/1")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/clients/{client_id}
# ---------------------------------------------------------------------------

def test_update_client(client, auth_headers):
    """Обновление полей клиента."""
    c = _create_client(client, auth_headers)
    resp = client.patch(
        f"/api/clients/{c['id']}",
        json={"name": "Updated Name", "phone": "+79001234567"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
    assert resp.json()["phone"] == "+79001234567"
    _delete_client(client, auth_headers, c["id"])


def test_update_client_not_found(client, auth_headers):
    """Обновление несуществующего клиента — 404."""
    resp = client.patch("/api/clients/999999", json={"name": "X"}, headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/clients/{client_id}
# ---------------------------------------------------------------------------

def test_delete_client(client, auth_headers):
    """Удаление клиента."""
    c = _create_client(client, auth_headers)
    del_resp = client.delete(f"/api/clients/{c['id']}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/clients/{c['id']}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_delete_client_not_found(client, auth_headers):
    """Удаление несуществующего клиента — 404."""
    resp = client.delete("/api/clients/999999", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_client_unauthenticated(client):
    """Без токена — 401."""
    resp = client.delete("/api/clients/1")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/clients/{client_id}/vpn-profiles
# ---------------------------------------------------------------------------

def test_client_vpn_profiles_empty(client, auth_headers):
    """Список VPN-профилей нового клиента пуст."""
    c = _create_client(client, auth_headers)
    resp = client.get(f"/api/clients/{c['id']}/vpn-profiles", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []
    _delete_client(client, auth_headers, c["id"])


def test_client_vpn_profiles_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/clients/1/vpn-profiles")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/clients/{client_id}/proxies
# ---------------------------------------------------------------------------

def test_client_proxies_empty(client, auth_headers):
    """Список прокси нового клиента пуст."""
    c = _create_client(client, auth_headers)
    resp = client.get(f"/api/clients/{c['id']}/proxies", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []
    _delete_client(client, auth_headers, c["id"])


def test_client_proxies_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/clients/1/proxies")
    assert resp.status_code == 401
