"""
Тесты CRUD эндпоинтов пользователей: /api/users
Только admin имеет доступ к большинству операций.
"""
import uuid


def _unique_username():
    return f"user_{uuid.uuid4().hex[:8]}"


def _unique_email():
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


# ---------------------------------------------------------------------------
# GET /api/users
# ---------------------------------------------------------------------------

def test_list_users_admin(client, auth_headers):
    """Admin получает список пользователей."""
    resp = client.get("/api/users", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_list_users_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/users")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/users
# ---------------------------------------------------------------------------

def test_create_user_admin(client, auth_headers):
    """Admin создаёт нового пользователя."""
    payload = {
        "username": _unique_username(),
        "email": _unique_email(),
        "password": "testpass123",
        "role": "viewer",
        "is_active": True,
    }
    resp = client.post("/api/users", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == payload["username"]
    assert data["role"] == "viewer"
    assert "id" in data
    # Чистка
    client.delete(f"/api/users/{data['id']}", headers=auth_headers)


def test_create_user_duplicate_username(client, auth_headers):
    """Повторное создание с тем же username — 400."""
    payload = {
        "username": _unique_username(),
        "email": _unique_email(),
        "password": "testpass123",
        "role": "viewer",
    }
    r1 = client.post("/api/users", json=payload, headers=auth_headers)
    assert r1.status_code == 201

    payload2 = dict(payload, email=_unique_email())
    r2 = client.post("/api/users", json=payload2, headers=auth_headers)
    assert r2.status_code == 400
    # Чистка
    client.delete(f"/api/users/{r1.json()['id']}", headers=auth_headers)


def test_create_user_missing_fields(client, auth_headers):
    """Создание без обязательных полей — 422."""
    resp = client.post("/api/users", json={"username": "onlyname"}, headers=auth_headers)
    assert resp.status_code == 422


def test_create_user_unauthenticated(client):
    """Без токена — 401."""
    resp = client.post(
        "/api/users",
        json={"username": "x", "email": "x@x.com", "password": "x"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/users/{user_id}
# ---------------------------------------------------------------------------

def test_get_user_self(client, auth_headers):
    """Admin получает свой профиль."""
    me = client.get("/api/auth/me", headers=auth_headers).json()
    resp = client.get(f"/api/users/{me['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == me["id"]


def test_get_user_not_found(client, auth_headers):
    """Несуществующий пользователь — 404."""
    resp = client.get("/api/users/999999", headers=auth_headers)
    assert resp.status_code == 404


def test_get_user_unauthenticated(client):
    """Без токена — 401."""
    resp = client.get("/api/users/1")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/users/{user_id}
# ---------------------------------------------------------------------------

def test_update_user(client, auth_headers):
    """Admin обновляет данные пользователя."""
    create_resp = client.post(
        "/api/users",
        json={
            "username": _unique_username(),
            "email": _unique_email(),
            "password": "pass123",
            "role": "viewer",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/users/{user_id}",
        json={"full_name": "Updated Name", "role": "manager"},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["full_name"] == "Updated Name"
    assert patch_resp.json()["role"] == "manager"
    # Чистка
    client.delete(f"/api/users/{user_id}", headers=auth_headers)


def test_update_user_not_found(client, auth_headers):
    """Обновление несуществующего пользователя — 404."""
    resp = client.patch("/api/users/999999", json={"full_name": "X"}, headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/users/{user_id}
# ---------------------------------------------------------------------------

def test_delete_user(client, auth_headers):
    """Admin удаляет пользователя."""
    create_resp = client.post(
        "/api/users",
        json={
            "username": _unique_username(),
            "email": _unique_email(),
            "password": "pass123",
            "role": "viewer",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/users/{user_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/users/{user_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_delete_self_forbidden(client, auth_headers):
    """Admin не может удалить себя — 400."""
    me = client.get("/api/auth/me", headers=auth_headers).json()
    resp = client.delete(f"/api/users/{me['id']}", headers=auth_headers)
    assert resp.status_code == 400


def test_delete_user_not_found(client, auth_headers):
    """Удаление несуществующего пользователя — 404."""
    resp = client.delete("/api/users/999999", headers=auth_headers)
    assert resp.status_code == 404
