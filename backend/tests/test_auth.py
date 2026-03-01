"""
Тесты эндпоинтов авторизации: POST /api/auth/login, /api/auth/refresh, GET /api/auth/me
"""


def test_login_success(client):
    """Успешный вход с корректными данными."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    """Вход с неверным паролем — 401."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    """Вход с несуществующим пользователем — 401."""
    resp = client.post("/api/auth/login", json={"username": "ghost", "password": "any"})
    assert resp.status_code == 401


def test_login_missing_fields(client):
    """Логин без обязательных полей — 422."""
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code == 422


def test_refresh_token(client):
    """Обновление токена по refresh_token."""
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    refresh_token = login.json()["refresh_token"]

    resp = client.post(f"/api/auth/refresh?refresh_token={refresh_token}")
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_invalid_token(client):
    """Обновление с невалидным refresh_token — 401."""
    resp = client.post("/api/auth/refresh?refresh_token=invalid.token.here")
    assert resp.status_code == 401


def test_me_authenticated(client, auth_headers):
    """GET /api/auth/me возвращает текущего пользователя."""
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"


def test_me_unauthenticated(client):
    """GET /api/auth/me без токена — 401."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_invalid_token(client):
    """GET /api/auth/me с невалидным токеном — 401."""
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.valid.token"})
    assert resp.status_code == 401
