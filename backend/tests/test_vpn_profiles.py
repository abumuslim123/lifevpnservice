"""
Тесты VPN-профилей: /api/vpn-profiles

Создание профиля требует существующего сервера.
switch-protocol тестируется с мокированием генерации учётных данных.
download-config тестируется с уже имеющимися credentials.
"""
import uuid
from unittest.mock import patch


def _uid():
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------

def _make_server(client, auth_headers):
    resp = client.post(
        "/api/servers",
        json={"name": f"s_{_uid()}", "ip_address": "10.0.0.50", "ssh_password": "x"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _make_client_entity(client, auth_headers):
    resp = client.post(
        "/api/clients",
        json={"name": f"c_{_uid()}"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _make_profile(test_client, auth_headers, server_id, protocol="xray_vless"):
    with patch("app.services.xray.create_vless_profile_credentials", return_value={"uuid": "test-uuid"}):
        resp = test_client.post(
            "/api/vpn-profiles",
            json={
                "name": f"profile_{_uid()}",
                "server_id": server_id,
                "active_protocol": protocol,
            },
            headers=auth_headers,
        )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# GET /api/vpn-profiles
# ---------------------------------------------------------------------------

def test_list_profiles(client, auth_headers):
    """Список профилей возвращается без ошибок."""
    resp = client.get("/api/vpn-profiles", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_profiles_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/vpn-profiles")
    assert resp.status_code == 401


def test_list_profiles_filter_by_client(client, auth_headers):
    """Фильтрация по client_id работает."""
    resp = client.get("/api/vpn-profiles?client_id=9999", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /api/vpn-profiles
# ---------------------------------------------------------------------------

def test_create_profile_xray_vless(client, auth_headers):
    """Создание профиля с xray_vless (credentials мокируются)."""
    server = _make_server(client, auth_headers)
    profile = _make_profile(client, auth_headers, server["id"])
    assert profile["active_protocol"] == "xray_vless"
    assert "id" in profile
    client.delete(f"/api/vpn-profiles/{profile['id']}", headers=auth_headers)
    client.delete(f"/api/servers/{server['id']}", headers=auth_headers)


def test_create_profile_server_not_found(client, auth_headers):
    """Создание профиля для несуществующего сервера — 404."""
    with patch("app.services.xray.create_vless_profile_credentials", return_value={}):
        resp = client.post(
            "/api/vpn-profiles",
            json={"name": "p", "server_id": 999999, "active_protocol": "xray_vless"},
            headers=auth_headers,
        )
    assert resp.status_code == 404


def test_create_profile_missing_fields(client, auth_headers):
    """Создание без обязательных полей — 422."""
    resp = client.post("/api/vpn-profiles", json={"name": "only name"}, headers=auth_headers)
    assert resp.status_code == 422


def test_create_profile_unauthenticated(client):
    """Без токена — 401."""
    resp = client.post("/api/vpn-profiles", json={"name": "x", "server_id": 1, "active_protocol": "wireguard"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/vpn-profiles/{profile_id}
# ---------------------------------------------------------------------------

def test_get_profile(client, auth_headers):
    """Получение профиля по ID."""
    server = _make_server(client, auth_headers)
    profile = _make_profile(client, auth_headers, server["id"])
    resp = client.get(f"/api/vpn-profiles/{profile['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == profile["id"]
    client.delete(f"/api/vpn-profiles/{profile['id']}", headers=auth_headers)
    client.delete(f"/api/servers/{server['id']}", headers=auth_headers)


def test_get_profile_not_found(client, auth_headers):
    """Несуществующий профиль — 404."""
    resp = client.get("/api/vpn-profiles/999999", headers=auth_headers)
    assert resp.status_code == 404


def test_get_profile_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/vpn-profiles/1")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/vpn-profiles/{profile_id}
# ---------------------------------------------------------------------------

def test_update_profile(client, auth_headers):
    """Обновление полей профиля."""
    server = _make_server(client, auth_headers)
    profile = _make_profile(client, auth_headers, server["id"])
    resp = client.patch(
        f"/api/vpn-profiles/{profile['id']}",
        json={"name": "Updated Profile", "notes": "test note"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Profile"
    client.delete(f"/api/vpn-profiles/{profile['id']}", headers=auth_headers)
    client.delete(f"/api/servers/{server['id']}", headers=auth_headers)


def test_update_profile_not_found(client, auth_headers):
    """Обновление несуществующего профиля — 404."""
    resp = client.patch("/api/vpn-profiles/999999", json={"name": "X"}, headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/vpn-profiles/{profile_id}
# ---------------------------------------------------------------------------

def test_delete_profile(client, auth_headers):
    """Удаление профиля."""
    server = _make_server(client, auth_headers)
    profile = _make_profile(client, auth_headers, server["id"])
    del_resp = client.delete(f"/api/vpn-profiles/{profile['id']}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/vpn-profiles/{profile['id']}", headers=auth_headers)
    assert get_resp.status_code == 404
    client.delete(f"/api/servers/{server['id']}", headers=auth_headers)


def test_delete_profile_not_found(client, auth_headers):
    """Удаление несуществующего профиля — 404."""
    resp = client.delete("/api/vpn-profiles/999999", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/vpn-profiles/{profile_id}/switch-protocol
# ---------------------------------------------------------------------------

def test_switch_protocol(client, auth_headers):
    """Переключение протокола обновляет active_protocol и credentials."""
    server = _make_server(client, auth_headers)
    profile = _make_profile(client, auth_headers, server["id"], protocol="xray_vless")

    with patch(
        "app.services.xray.create_vmess_profile_credentials",
        return_value={"id": "test-vmess-id"},
    ):
        resp = client.patch(
            f"/api/vpn-profiles/{profile['id']}/switch-protocol",
            json={"protocol": "xray_vmess"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_protocol"] == "xray_vmess"
    client.delete(f"/api/vpn-profiles/{profile['id']}", headers=auth_headers)
    client.delete(f"/api/servers/{server['id']}", headers=auth_headers)


def test_switch_protocol_not_found(client, auth_headers):
    """switch-protocol для несуществующего профиля — 404."""
    resp = client.patch(
        "/api/vpn-profiles/999999/switch-protocol",
        json={"protocol": "wireguard"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_switch_protocol_invalid_protocol(client, auth_headers):
    """switch-protocol с несуществующим протоколом — 422."""
    resp = client.patch(
        "/api/vpn-profiles/1/switch-protocol",
        json={"protocol": "nonexistent_proto"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_switch_protocol_unauthenticated(client):
    """Без токена — 401."""
    resp = client.patch("/api/vpn-profiles/1/switch-protocol", json={"protocol": "wireguard"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/vpn-profiles/{profile_id}/download-config
# ---------------------------------------------------------------------------

def test_download_config_not_found(client, auth_headers):
    """download-config для несуществующего профиля — 404."""
    resp = client.get("/api/vpn-profiles/999999/download-config?app=wireguard", headers=auth_headers)
    assert resp.status_code == 404


def test_download_config_wireguard(client, auth_headers):
    """download-config возвращает файл конфига (credentials мокируются)."""
    server = _make_server(client, auth_headers)

    with patch("app.services.wireguard.create_profile_credentials", return_value={
        "client_private_key": "privatekey",
        "client_public_key": "publickey",
        "server_public_key": "serverpubkey",
        "client_ip": "10.8.0.2/32",
        "dns": "1.1.1.1",
        "server_endpoint": "10.0.0.50:51820",
    }):
        profile = client.post(
            "/api/vpn-profiles",
            json={"name": "wg_test", "server_id": server["id"], "active_protocol": "wireguard"},
            headers=auth_headers,
        ).json()

    resp = client.get(
        f"/api/vpn-profiles/{profile['id']}/download-config?app=wireguard",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    client.delete(f"/api/vpn-profiles/{profile['id']}", headers=auth_headers)
    client.delete(f"/api/servers/{server['id']}", headers=auth_headers)


def test_download_config_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/vpn-profiles/1/download-config?app=wireguard")
    assert resp.status_code == 401
