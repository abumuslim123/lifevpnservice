# VPN Service — Панель управления

Полнофункциональный VPN-сервис с веб-дашбордом. Поддерживает все популярные протоколы VPN, управление серверами, клиентами, прокси и генерацию конфигураций для всех клиентских приложений.

## Возможности

- **Протоколы VPN**: WireGuard, AmneziaWG, OpenVPN, IKEv2/IPSec, L2TP/IPSec, PPTP, VLESS, VMess, Trojan, Shadowsocks (Xray-core)
- **Генерация конфигов** для: Amnezia VPN, v2rayTUN/v2rayNG, Clash/Clash Meta, Sing-box, WireGuard App, OpenVPN Connect, Shadowrocket
- **Горячее переключение протокола** для профиля без удаления данных
- **База клиентов** с привязкой VPN профилей и прокси
- **Управление пользователями** с ролями (admin / manager / viewer)
- **Прокси**: HTTP, HTTPS, SOCKS5, Shadowsocks, Trojan с QR-кодами и share-ссылками
- **Управление серверами** через SSH (пароль или приватный ключ)
- **Тёмная и светлая тема**

## Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| База данных | PostgreSQL 15 |
| Кеш | Redis |
| SSH | Paramiko |
| Аутентификация | JWT (python-jose) |

## Установка на сервер (Ubuntu 22.04 / Debian 12)

### 1. Системные зависимости

```bash
apt-get update && apt-get install -y \
  python3.11 python3.11-venv python3-pip \
  postgresql postgresql-contrib \
  redis-server \
  nodejs npm \
  git curl

# Обновить npm
npm install -g npm@latest
```

### 2. База данных

```bash
sudo -u postgres psql <<EOF
CREATE USER vpnuser WITH PASSWORD 'vpnpassword';
CREATE DATABASE vpnservice OWNER vpnuser;
GRANT ALL PRIVILEGES ON DATABASE vpnservice TO vpnuser;
EOF

systemctl enable --now postgresql redis-server
```

### 3. Клонирование и настройка

```bash
git clone <your-repo-url> /opt/vpnservice
cd /opt/vpnservice
```

### 4. Backend

```bash
cd /opt/vpnservice/backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройте переменные окружения
cp .env .env.local
nano .env.local  # Измените SECRET_KEY, пароли и т.д.

# Применить миграции / создать таблицы (запуск автоматически при старте)
```

Файл `.env` (обязательно смените `SECRET_KEY`):
```env
DATABASE_URL=postgresql+asyncpg://vpnuser:vpnpassword@localhost:5432/vpnservice
DATABASE_SYNC_URL=postgresql://vpnuser:vpnpassword@localhost:5432/vpnservice
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=YOUR_RANDOM_SECRET_KEY_MIN_32_CHARS
FIRST_ADMIN_USERNAME=admin
FIRST_ADMIN_PASSWORD=your_strong_password
FIRST_ADMIN_EMAIL=admin@yourdomain.com
```

### 5. Frontend

```bash
cd /opt/vpnservice/frontend
npm install
npm run build
```

### 6. Systemd сервисы

**Backend** — `/etc/systemd/system/vpnservice-backend.service`:
```ini
[Unit]
Description=VPN Service Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/vpnservice/backend
Environment="PATH=/opt/vpnservice/backend/venv/bin"
ExecStart=/opt/vpnservice/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now vpnservice-backend
```

### 7. Nginx (реверс-прокси)

```bash
apt-get install -y nginx
```

`/etc/nginx/sites-available/vpnservice`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend (статика)
    location / {
        root /opt/vpnservice/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/vpnservice /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

### 8. HTTPS (Let's Encrypt)

```bash
apt-get install -y certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com
```

### 9. Первый вход

Откройте браузер: `https://yourdomain.com`

- Логин: `admin` (или значение `FIRST_ADMIN_USERNAME`)
- Пароль: `admin123` (или значение `FIRST_ADMIN_PASSWORD`)

**Сразу смените пароль после первого входа!**

## Структура проекта

```
vpnservice/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, lifespan
│   │   ├── config.py            # Настройки (pydantic-settings)
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── models/              # ORM модели
│   │   ├── routers/             # FastAPI роутеры
│   │   ├── services/            # Бизнес-логика протоколов
│   │   └── schemas/             # Pydantic схемы
│   ├── alembic/                 # Миграции БД
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── pages/               # Страницы дашборда
    │   ├── components/          # UI компоненты
    │   ├── api/                 # Axios API клиент
    │   ├── hooks/               # React хуки (auth, theme)
    │   └── types/               # TypeScript типы
    └── package.json
```

## API Документация

После запуска бэкенда Swagger UI доступен по адресу: `http://localhost:8000/docs`

## Горячее переключение протокола

```
PATCH /api/vpn-profiles/{id}/switch-protocol
Body: { "protocol": "xray_vless" }
```

При переключении автоматически генерируются новые учётные данные для выбранного протокола. Старые данные заменяются.

## Поддерживаемые форматы экспорта конфигов

| Приложение | Формат | Endpoint |
|-----------|--------|----------|
| WireGuard App | `.conf` | `?app=wireguard` |
| Amnezia VPN | `vpn://` link | `?app=amnezia` |
| OpenVPN Connect | `.ovpn` | `?app=openvpn` |
| v2rayTUN / v2rayNG | `.json` | `?app=v2raytun` |
| Clash / Clash Meta | `.yaml` | `?app=clashyaml` |
| Sing-box | `.json` | `?app=singbox` |
| Shadowrocket | URI | `?app=shadowrocket` |

Endpoint: `GET /api/vpn-profiles/{id}/download-config?app={app}`
