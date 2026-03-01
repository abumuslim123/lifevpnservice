"""
Тесты прокси-эндпоинтов: /api/proxies

deploy и share-link тестируются с мокированием SSH/сервисных вызовов.
"""
import uuid
from unittest.mock import patch


def _uid():
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_server(client, auth_headers):
    resp = client.post(
        "/api/servers",
        json={"name": f"srv_{_uid()}", "ip_address": "10.0.0.88", "ssh_password": "x"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _make_proxy(test_client, auth_headers, server_id, proxy_type="socks5", port=None):
    resp = test_client.post(
        "/api/proxies",
        json={
            "name": f"proxy_{_uid()}",
            "proxy_type": proxy_type,
            "server_id": server_id,
            "port": port or (1080 + int(_uid()[:3], 16) % 1000),
            "username": "proxyuser",
            "password": "proxypass",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# GET /api/proxies
# ---------------------------------------------------------------------------

def test_list_proxies(client, auth_headers):
    """Список прокси возвращается без ошибок."""
    resp = client.get("/api/proxies", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_proxies_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/proxies")
    assert resp.status_code == 401


def test_list_proxies_filter_by_client(client, auth_headers):
    """Фильтрация по client_id работает."""
    resp = client.get("/api/proxies?client_id=999999", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /api/proxies
# ---------------------------------------------------------------------------

def test_create_proxy(client, auth_headers):
    """Успешное создание прокси."""
    server = _make_server(client, auth_headers)
    proxy = _make_proxy(client, auth_headers, server["id"])
    assert proxy["proxy_type"] == "socks5"
    assert "id" in proxy
    client.delete(f"/api/proxies/{proxy['id']}", headers=auth_headers)
    client.delete(f"/api/servers/{server['id']}", headers=auth_headers)


def test_create_proxy_server_not_found(client, auth_headers):
    """Создание прокси для несуществующего сервера — 404."""
    resp = client.post(
        "/api/proxies",
        json={"name": "p", "proxy_type": "http", "server_id": 999999, "port": 8080},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_create_proxy_missing_fields(client, auth_headers):
    """Создание без обязательных полей — 422."""
    resp = client.post("/api/proxies", json={"name": "only"}, headers=auth_headers)
    assert resp.status_code == 422


def test_create_proxy_unauthenticated(client):
    """Без токена — 401."""
    resp = client.post(
        "/api/proxies",
        json={"name": "p", "proxy_type": "http", "server_id": 1, "port": 8080},
    )
    assert resp.status_code == 401


def test_create_proxy_auto_password(client, auth_headers):
    """При отсутствии пароля он генерируется автоматически."""
    server = _make_server(client, auth_headers)
    resp = client.post(
        "/api/proxies",
        json={"name": f"auto_{_uid()}", "proxy_type": "http", "server_id": server["id"], "port": 8181},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    proxy = resp.json()
    assert proxy["password"] is not None and proxy["password"] != ""
    client.delete(f"/api/proxies/{proxy['id']}", headers=auth_headers)
    client.delete(f"/api/servers/{server['id']}", headers=auth_headers)


# ---------------------------------------------------------------------------
# GET /api/proxies/{proxy_id}
# ---------------------------------------------------------------------------

def test_get_proxy(client, auth_headers):
    """Получение прокси по ID."""
    server = _make_server(client, auth_headers)
    proxy = _make_proxy(client, auth_headers, server["id"])
    resp = client.get(f"/api/proxies/{proxy['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == proxy["id"]
    client.delete(f"/api/proxies/{proxy['id']}", headers=auth_headers)
    client.delete(f"/api/servers/{server['id']}", headers=auth_headers)


def test_get_proxy_not_found(client, auth_headers):
    """Несуществующий прокси — 404."""
    resp = client.get("/api/proxies/999999", headers=auth_headers)
    assert resp.status_code == 404


def test_get_proxy_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/proxies/1")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/proxies/{proxy_id}
# ---------------------------------------------------------------------------

def test_update_proxy(client, auth_headers):
    """Обновление полей прокси."""
    server = _make_server(client, auth_headers)
    proxy = _make_proxy(client, auth_headers, server["id"])
    resp = client.patch(
        f"/api/proxies/{proxy['id']}",
        json={"name": "Updated Proxy", "notes": "updated"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Proxy"
    client.delete(f"/api/proxies/{proxy['id']}", headers=auth_headers)
    client.delete(f"/api/servers/{server['id']}", headers=auth_headers)


def test_update_proxy_not_found(client, auth_headers):
    """Обновление несуществующего прокси — 404."""
    resp = client.patch("/api/proxies/999999", json={"name": "X"}, headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/proxies/{proxy_id}
# ---------------------------------------------------------------------------

def test_delete_proxy(client, auth_headers):
    """Удаление прокси."""
    server = _make_server(client, auth_headers)
    proxy = _make_proxy(client, auth_headers, server["id"])
    del_resp = client.delete(f"/api/proxies/{proxy['id']}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/proxies/{proxy['id']}", headers=auth_headers)
    assert get_resp.status_code == 404
    client.delete(f"/api/servers/{server['id']}", headers=auth_headers)


def test_delete_proxy_not_found(client, auth_headers):
    """Удаление несуществующего прокси — 404."""
    resp = client.delete("/api/proxies/999999", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_proxy_unauthenticated(client):
    """Без токена — 401."""
    resp = client.delete("/api/proxies/1")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/proxies/{proxy_id}/deploy
# ---------------------------------------------------------------------------

def test_deploy_proxy_not_found(client, auth_headers):
    """deploy для несуществующего прокси — 404."""
    resp = client.post("/api/proxies/999999/deploy", headers=auth_headers)
    assert resp.status_code == 404


def test_deploy_proxy_mocked(client, auth_headers):
    """deploy возвращает success/message (SSH замокирован)."""
    server = _make_server(client, auth_headers)
    proxy = _make_proxy(client, auth_headers, server["id"], proxy_type="socks5")

    with patch("app.services.proxy_service.setup_3proxy", return_value=(True, "3proxy deployed")):
        resp = client.post(f"/api/proxies/{proxy['id']}/deploy", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data
    assert "message" in data
    client.delete(f"/api/proxies/{proxy['id']}", headers=auth_headers)
    client.delete(f"/api/servers/{server['id']}", headers=auth_headers)


def test_deploy_proxy_unauthenticated(client):
    """Без токена — 401."""
    resp = client.post("/api/proxies/1/deploy")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/proxies/{proxy_id}/share-link
# ---------------------------------------------------------------------------

def test_get_share_link_not_found(client, auth_headers):
    """share-link для несуществующего прокси — 404."""
    resp = client.get("/api/proxies/999999/share-link", headers=auth_headers)
    assert resp.status_code == 404


def test_get_share_link(client, auth_headers):
    """share-link возвращает link и qr_base64."""
    server = _make_server(client, auth_headers)
    proxy = _make_proxy(client, auth_headers, server["id"], proxy_type="shadowsocks")

    with patch("app.services.proxy_service.build_proxy_share_link", return_value="ss://test"):
        with patch("app.services.proxy_service.generate_proxy_qr", return_value="base64data"):
            resp = client.get(f"/api/proxies/{proxy['id']}/share-link", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "link" in data
    assert "qr_base64" in data
    client.delete(f"/api/proxies/{proxy['id']}", headers=auth_headers)
    client.delete(f"/api/servers/{server['id']}", headers=auth_headers)


def test_get_share_link_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/proxies/1/share-link")
    assert resp.status_code == 401
