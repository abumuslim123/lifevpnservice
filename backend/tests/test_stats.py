"""
Тесты статистики: GET /api/stats/dashboard
"""


def test_dashboard_stats(client, auth_headers):
    """dashboard_stats возвращает все ключевые разделы статистики."""
    resp = client.get("/api/stats/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "servers" in data
    assert "clients" in data
    assert "vpn_profiles" in data
    assert "proxies" in data
    assert "users" in data
    assert "servers_list" in data
    assert "protocols_distribution" in data


def test_dashboard_stats_servers_structure(client, auth_headers):
    """Раздел servers содержит total и online."""
    resp = client.get("/api/stats/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    servers = resp.json()["servers"]
    assert "total" in servers
    assert "online" in servers
    assert isinstance(servers["total"], int)
    assert isinstance(servers["online"], int)
    assert servers["online"] <= servers["total"]


def test_dashboard_stats_vpn_profiles_structure(client, auth_headers):
    """Раздел vpn_profiles содержит total и active."""
    resp = client.get("/api/stats/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    profiles = resp.json()["vpn_profiles"]
    assert "total" in profiles
    assert "active" in profiles


def test_dashboard_stats_proxies_structure(client, auth_headers):
    """Раздел proxies содержит total и active."""
    resp = client.get("/api/stats/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    proxies = resp.json()["proxies"]
    assert "total" in proxies
    assert "active" in proxies


def test_dashboard_stats_users_structure(client, auth_headers):
    """Раздел users содержит total и включает минимум admin-пользователя."""
    resp = client.get("/api/stats/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    users = resp.json()["users"]
    assert "total" in users
    assert users["total"] >= 1


def test_dashboard_stats_servers_list(client, auth_headers):
    """servers_list — список объектов с ожидаемыми полями."""
    resp = client.get("/api/stats/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    servers_list = resp.json()["servers_list"]
    assert isinstance(servers_list, list)
    for s in servers_list:
        assert "id" in s
        assert "name" in s
        assert "ip_address" in s
        assert "status" in s


def test_dashboard_stats_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/stats/dashboard")
    assert resp.status_code == 401


def test_dashboard_stats_invalid_token(client):
    """Невалидный токен — 401."""
    resp = client.get(
        "/api/stats/dashboard",
        headers={"Authorization": "Bearer invalid.token"},
    )
    assert resp.status_code == 401


def test_health_endpoint(client):
    """GET /api/health работает без авторизации."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
