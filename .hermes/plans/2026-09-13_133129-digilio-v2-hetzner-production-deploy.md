# Digilio-v2 → Hetzner Production Deploy Plan

> **For Hermes:** Execute fase demi fase, verifikasi tiap fase, jangan lanjut bila gate gagal.
> **Mode:** Deploy-only. **Tidak mengubah logika model** (`core/models/**`) sama sekali.

**Goal:** Menjalankan digilio-v2 di 1 server Hetzner untuk 20–30 concurrent user, siap produksi (HTTPS, gunicorn, Celery aktif, backup otomatis), tanpa mengubah logika bisnis aplikasi.

**Architecture:** Docker Compose full-stack di 1 host. Caddy sebagai reverse proxy + auto-TLS + penyaji frontend statis → `backend` (gunicorn 3 worker) → `postgres` + `redis`. `celery-worker` + `celery-beat` berbagi image backend yang sama.

**Tech Stack:** Django 6 + DRF (metadata-driven) · React/Vite + pnpm · PostgreSQL 16 · Redis 7 · Celery 5 · WeasyPrint 69 · Gunicorn · Caddy 2 · Docker Compose

---

## Arsitektur Target

```
Internet :80/:443
      │
  ┌───▼──────────────────────────── Caddy (container) ────────────────────────────┐
  │  /            → /srv/frontend  (hasil `pnpm build`, file statis)               │
  │  /api/*       → backend:8000                                                   │
  │  /admin/*     → backend:8000                                                   │
  │  /static/*    → volume staticfiles (hasil collectstatic)                       │
  └───┬───────────────────────────────────────────────────────────────────────────┘
      │ docker network: digilio_net (internal only, port tidak diekspos ke host)
      │
  ┌───▼────────┐   ┌───────────┐   ┌────────────────┐   ┌──────────────┐
  │  postgres  │   │   redis   │   │ celery-worker  │   │  celery-beat │
  │ 16-alpine  │   │ 7-alpine  │   │  (image backend)│   │(image backend)│
  │ vol:pgdata │   │ vol:redis │   └────────────────┘   └──────────────┘
  └────────────┘   └───────────┘
                          ▲ broker + result backend + (nanti) channel layer
```

**Yang TIDAK diekspos ke internet:** 5432 (Postgres), 6379 (Redis), 8000 (gunicorn). Hanya Caddy yang buka 80/443.

---

## Prasyarat & Asumsi

**Server:** Hetzner Cloud, Ubuntu 24.04 LTS, minimal **CX22 (2 vCPU / 4 GB / 40 GB SSD)**. Rekomendasi **CX32 (4 vCPU / 8 GB / 80 GB)** bila mau nyaman — lihat §Sizing.

**Kapasitas hasil audit (data nyata dari load test):** dengan 2 vCPU/4GB + gunicorn 3 worker + Celery, perkiraan **25–40 concurrent user** nyaman. Tanpa hardening (runserver + vite dev) hanya **~6–10 user**.

**Repo:** `git@github.com:bayukris02/digilio-v2.git`, branch `master`, status bersih.

### Fakta dari audit yang WAJIB dibereskan (blocker produksi)

| # | Temuan (terverifikasi) | Lokasi | Dampak |
|---|---|---|---|
| B1 | `DEBUG = True` | `backend/config/settings.py:11` | Stack trace + setting bocor ke publik |
| B2 | `SECRET_KEY` hardcoded di repo | `backend/config/settings.py:10` | Session/JWT bisa dipalsukan |
| B3 | `ALLOWED_HOSTS = ['*']` | `settings.py:12` | Host header attack |
| B4 | `CORS_ALLOW_ALL_ORIGINS = True` | `settings.py:~110` | CSRF/CORS terbuka |
| B5 | Kredensial DB hardcoded (`digilio/digilio`) | `settings.py:~80` | Kredensial publik di GitHub |
| B6 | Tidak ada `STATIC_ROOT` | `settings.py` | `collectstatic` gagal → admin tanpa CSS |
| B7 | **`django-channels` 0.7.0 adalah paket SALAH** — "A Django library for sending notifications" (2016, oleh ymyzk), **bukan Django Channels**. Paket aslinya `channels`. | `backend/pyproject.toml:15` | `config/asgi.py:7` `from channels.routing import ...` → **ImportError**. Paket menabrak namespace `channels/` milik lib asli (name collision). |
| B8 | `CHANNEL_LAYERS` pakai `channels_redis` yang **tidak terinstall** | `settings.py:~95` | Error saat ASGI/WebSocket dipakai |
| B9 | **Bug PDF/Print**: `render_pdf` menambah `print/` dua kali → `TemplateDoesNotExist: print/print/purchase_order.html` | `backend/reports/renderer.py:41` + `core/model_meta.py:380` | **Semua** download/print PDF gagal (sudah dibuktikan, status 500) |
| B10 | `gunicorn` belum terinstall | `pyproject.toml`, `uv.lock` | Tidak bisa serve produksi |
| B11 | `backend/backups/` menulis ke disk lokal (`dumpdata`) | `core/purge_api.py:275` | Harus di volume persisten, bukan di layer container |
| B12 | Docker container tanpa limit CPU/RAM | `docker-compose.yml` | Container bisa menghabiskan host |
| B13 | Tidak ada `CACHES` padahal Redis tersedia | `settings.py` | Metadata & `/config/` dihitung ulang tiap request |
| B14 | Frontend `ModelListPage` pakai `page_size=0` (load SEMUA record) | `frontend/src/pages/model/ModelListPage.tsx:79` | Tebing skalabilitas saat data tumbuh — **follow-up, tidak block go-live** |
| B15 | Tidak ada backup terjadwal | — | Kehilangan data tanpa pemulihan |

**Tidak dipakai aplikasi (jangan dipasang di server):** MinIO, Meilisearch. Sudah saya cek: tidak ada satu pun referensi `minio`/`meili`/`s3` di `core/`, `reports/`, `imports/`, `config/`. Di server sekarang keduanya jalan sia-sia (MinIO 184 MB RAM).

**Frontend tidak pakai WebSocket** — sudah dicek, 0 referensi `WebSocket`/`ws://` di `frontend/src`. Jadi Chromium/Channels **tidak diperlukan**; lihat Task 3.4.

---

## Sizing (Hetzner Cloud)

| Plan | vCPU | RAM | Disk | Harga | Untuk apa |
|---|---|---|---|---|---|
| CX22 | 2 | 4 GB | 40 GB | €3.79/bln | **Minimum** — cukup untuk 25–40 user setelah hardening. Butuh swapfile 2 GB. |
| CX32 | 4 | 8 GB | 80 GB | €6.80/bln | **Rekomendasi** — headroom untuk build image & Celery, tanpa swap. |
| CX42 | 8 | 16 GB | 160 GB | €16.40/bln | Nanti kalau data >5 GB atau user >80 |

Alokasi RAM budget di CX22 (4 GB): OS ~500 MB · Postgres ~250 MB · Redis ~30 MB · gunicorn 3×~200 MB ~600 MB · celery 1×~250 MB · Caddy ~40 MB · **sisa ~2,3 GB** (aman; WeasyPrint butuh ~100 MB per proses PDF).

---

# FASE 0 — Keputusan & prasyarat (butuh input user)

**Tujuan:** mengunci hal-hal yang tidak bisa ditebak sebelum menyentuh server.

**Step 0.1 — Tentukan & catat variabel berikut**

```
SERVER_IP        = <IP Hetzner>
SERVER_HOSTNAME  = digilio.example.com   (A record → SERVER_IP)
ADMIN_EMAIL      = <email untuk Let's Encrypt>
DEPLOY_USER      = deploy
APP_DIR          = /srv/digilio-v2
```

**Step 0.2 — Aktifkan swap (WAJIB di CX22, disk 40 GB)**

```bash
fallocate -l 2G /swapfile && chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
echo 'vm.swappiness=10' > /etc/sysctl.d/99-swap.conf && sysctl -p /etc/sysctl.d/99-swap.conf
```

Verify: `free -h` → baris `Swap: 2.0Gi`. `swapon --show` menampilkan `/swapfile`.

**Step 0.3 — Bangun secret baru (JANGAN pakai `SECRET_KEY` dari repo)**

```bash
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64))"
python3 -c "import secrets; print('DB_PASSWORD=' + secrets.token_urlsafe(24))"
```

Hasil disimpan di `/srv/digilio-v2/.env` (Task 5.1), **tidak pernah di-commit**.

**Gate Fase 0:** user sudah konfirmasi IP, domain, email, dan spesifikasi server.

**Rollback:** tidak ada (read-only + swap, tidak merusak apa pun).

---

# FASE 1 — Hardening server

**Tujuan:** server tidak bisa diakses sembarangan sebelum aplikasi dipasang.

**Step 1.1 — SSH key-only + user non-root**

```bash
ssh-keygen -t ed25519 -C "digilio-deploy"        # lokal, bila belum ada
ssh-copy-id root@$SERVER_IP
ssh root@$SERVER_IP
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh && cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh && chmod 700 /home/deploy/.ssh && chmod 600 /home/deploy/.ssh/authorized_keys
echo 'deploy ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/deploy
```

Verify: `ssh deploy@$SERVER_IP` berhasil **tanpa password**. `ssh -o PreferredAuthentications=password root@$SERVER_IP` **ditolak**.
⚠️ **Jangan tutup sesi root lama** sebelum login `deploy` berhasil, agar tidak terkunci.

**Step 1.2 — Firewall + fail2ban**

```bash
apt update && apt upgrade -y
apt install -y ufw fail2ban
ufw default deny incoming && ufw default allow outgoing
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp
ufw --force enable
systemctl enable --now fail2ban
```

Verify: `ufw status verbose` → `Status: active`, hanya 22/80/443 ALLOW. `fail2ban-client status` → `Jail: sshd`.

**Step 1.3 — Auto security update + timezone + locale**

```bash
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades        # pilih Yes
timedatectl set-timezone Asia/Jakarta
timedatectl set-ntp true
apt install -y curl git ca-certificates tzdata
```

Verify: `timedatectl` → `Time zone: Asia/Jakarta (WIB, +0700)`, `System clock synchronized: yes`.

**Step 1.4 — Install Docker Engine + Compose v2**

```bash
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy
systemctl enable --now docker
```

Verify: `docker compose version` (sebagai user `deploy`) → `Docker Compose version v2.x`. `docker info` jalan tanpa sudo.

**Gate Fase 1:** `deploy` bisa login tanpa password, punya akses docker, ufw aktif, timezone WIB.

**Rollback:** `ufw disable`, `rm /etc/sudoers.d/deploy`, kembalikan `sshd_config` dari `~/.ssh/sshd_config.bak` (buat backup sebelum sed).

---

# FASE 2 — Siapkan kode di server

**Tujuan:** kode ada di `/srv/digilio-v2`, siap di-build.

**Step 2.1 — Deploy key untuk GitHub (repo private)**

```bash
sudo -iu deploy
ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N ""
cat ~/.ssh/github_deploy.pub
```

→ Tambahkan public key itu di GitHub repo → **Settings → Deploy keys → Add deploy key** (read-only cukup).

**Step 2.2 — Konfigurasi SSH untuk GitHub + clone**

```bash
cat >> ~/.ssh/config <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_deploy
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
sudo mkdir -p /srv && sudo chown deploy:deploy /srv
git clone git@github.com:bayukris02/digilio-v2.git /srv/digilio-v2
cd /srv/digilio-v2 && git log --oneline -1
```

Verify: `git log --oneline -1` → commit `aafaf13 feat(inventory): Minimum Stock ...`.

**Step 2.3 — Tandai situs sebagai milik env produksi**

Buat `/srv/digilio-v2/.gitignore` **tidak perlu diubah** (sudah mengabaikan `.env`, `backend/backups/`, `frontend/dist/`). Cukup pastikan `.env` tidak masuk:

```bash
cd /srv/digilio-v2 && git status --short --ignored | grep -c "^!! "   # hanya info
```

Verify: `.env` **tidak ada** di `git status --short` setelah Fase 5 dibuat.

**Gate Fase 2:** `/srv/digilio-v2` ada, `git status` bersih, remote reachable.

**Rollback:** `sudo rm -rf /srv/digilio-v2` (tidak ada data produksi di sini).

---

# FASE 3 — Perbaikan kode (file non-model, minimal diff)

**Tujuan:** menutup blocker B7–B10 + B9 (bug PDF) sebelum build pertama.

⚠️ **Catatan aturan:** sesuai preferensi Anda, perubahan **hanya menyentuh config/infra + 1 baris bug renderer**. **Tidak ada file di `core/models/**` yang disentuh.** Semua tugas di fase ini adalah infra/konfigurasi, bukan fitur.

## Task 3.1 — Tambah dependency produksi (`gunicorn`)

**File:** Modify `backend/pyproject.toml:14-25`

```toml
dependencies = [
    "celery>=5.6.3",
    "django>=6.0.6",
    "django-cors-headers>=4.9.0",
    "django-filter>=25.2",
    "djangorestframework>=3.17.1",
    "djangorestframework-simplejwt>=5.5.1",
    "gunicorn>=23.0.0",
    "openpyxl>=3.1.5",
    "psycopg2-binary>=2.9.12",
    "redis>=8.0.0",
    "weasyprint>=69.0",
]
```

**Perubahan:** hapus `"django-channels>=0.7.0"` (B7) + tambah `"gunicorn>=23.0.0"` (B10).

**Step:** `cd /srv/digilio-v2/backend && uv lock && uv sync`

Verify: `uv run gunicorn --version` → `gunicorn (version 23.x)`. `uv run python -c "import channels"` → **ModuleNotFoundError** (paket palsu sudah tersingkir).

**Commit:** `chore(deps): add gunicorn, drop wrong django-channels (0.7.0 is an unrelated 2016 lib)`

## Task 3.2 — Lepas Channels yang tidak terpakai dari settings

**File:** Modify `backend/config/settings.py`

- Baris 20 area `INSTALLED_APPS`: **hapus** `'channels',`
- Blok `CHANNEL_LAYERS = {...}` (~baris 95): **hapus seluruh blok**

**Alasan:** `channels` yang terpasang adalah library notifikasi 2016 (B7) dan `channels_redis` tidak ada (B8). Frontend tidak memakai WebSocket (0 referensi di `frontend/src`) → YAGNI.

**File:** Modify `backend/config/asgi.py` → ganti isi menjadi:

```python
"""ASGI config for config project (HTTP only — WebSocket belum dipakai)."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
```

Verify:
```bash
cd /srv/digilio-v2/backend && uv run python -c "
import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); django.setup()
from django.conf import settings; print('channels' in settings.INSTALLED_APPS, hasattr(settings,'CHANNEL_LAYERS'))"
```
Expected: `False False`

**Commit:** `chore(settings): remove broken channels app + channel layers (unused, wrong package)`

## Task 3.3 — Fix bug PDF/Print (B9)

**File:** Modify `backend/reports/renderer.py:41`

**Akar masalah:** `core/model_meta.py:380 get_printouts()` sudah mengembalikan path **lengkap** (`print/purchase_order.html` — diverifikasi lewat `_print_template_exists`), lalu `render_pdf` menambah `print/` lagi → `print/print/purchase_order.html`.

```python
# SEBELUM (baris 41)
    html_str = render_to_string(f'print/{template_name}', context)

# SESUDAH
    html_str = render_to_string(template_name, context)
```

**Verifikasi (harus lulus sebelum lanjut):**
```bash
cd /srv/digilio-v2/backend && uv run python -c "
import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); django.setup()
from core.model_api import get_model_class
from reports.renderer import render_pdf
cls = get_model_class('purchase.order')
tpl = cls.get_printouts()[0]['template']
print('template =', tpl)
pdf = render_pdf(tpl, {'record': cls.objects.filter(is_deleted=False).first()})
print('PDF bytes =', len(pdf), 'header =', pdf[:5])
assert len(pdf) > 1000 and pdf[:5] == b'%PDF-'
print('OK')
"
```
Expected: `template = print/purchase_order.html`, `PDF bytes = <angka>`, `header = b'%PDF-'`, `OK`.

⚠️ Kalau `get_printouts()` ternyata mengembalikan `print/_generic.html`, itu **tetap benar** — yang penting path tidak di-dobel.

**Commit:** `fix(reports): PDF render failed with TemplateDoesNotExist print/print/...`

## Task 3.4 — Tambah `STATIC_ROOT` + cache Redis (B6, B13)

**File:** Modify `backend/config/settings.py`, blok Static files di akhir file

```python
# ──────────────────────────────────────────────
# Static files
# ──────────────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'      # untuk collectstatic

# ──────────────────────────────────────────────
# Cache — Redis (dipakai metadata /config/ yang jarang berubah)
# ──────────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
    }
}
```

Tambahkan `import os` di bagian atas file bila belum ada.

**Verifikasi:**
```bash
cd /srv/digilio-v2/backend && uv run python manage.py collectstatic --noinput | tail -3
```
Expected: `xxx static files copied to '/srv/digilio-v2/backend/staticfiles'.` (angka > 100)

**Commit:** `chore(settings): add STATIC_ROOT for collectstatic + Redis cache backend`

## Task 3.5 — Konfigurasi Gunicorn

**File:** Create `backend/deploy/gunicorn.conf.py`

```python
"""Gunicorn config produksi digilio-v2."""
import multiprocessing

bind = "0.0.0.0:8000"
workers = int(__import__("os").environ.get("GUNICORN_WORKERS", 3))
worker_class = "sync"
threads = 1
timeout = 120            # PDF/WeasyPrint bisa lambat sebelum dipindah ke Celery
graceful_timeout = 30
keepalive = 5
max_requests = 1000      # recycle worker → cegah memory creep (WeasyPrint naikkan RSS)
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
loglevel = "info"
# WAJIB di Docker: jangan pakai /tmp default (masalah gunicorn + container)
worker_tmp_dir = "/dev/shm"
forwarded_allow_ips = "*"
```

**Verifikasi:** file ada; `python3 -c "compile(open('backend/deploy/gunicorn.conf.py').read(),'g','exec')"` → tanpa error.

**Commit:** `chore(deploy): add gunicorn production config`

## Task 3.6 — Wiring Celery: worker, beat, dan schedule kosong

**File:** Modify `backend/config/settings.py` — tambahkan di blok Celery yang sudah ada:

```python
CELERY_TASK_TIME_LIMIT = 600          # hard limit — task nyangkut dibunuh
CELERY_TASK_SOFT_TIME_LIMIT = 540
CELERY_WORKER_PREFETCH_MULTIPLIER = 1 # adil untuk task berat (PDF/import)
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50  # recycle → cegah kebocoran memori WeasyPrint
CELERY_BEAT_SCHEDULE = {
    # Diisi di Fase 10 (fitur scheduler). Kosong = beat jalan tapi tidak ada job.
}
```

**File:** Create `backend/core/tasks.py`

```python
"""Celery tasks untuk app core.

Task di sini dijalankan oleh `celery-worker`, terpisah dari proses web,
sehingga pekerjaan berat (PDF, import, report) tidak memblokir user lain.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='core.ping')
def ping():
    """Task health-check — dipakai untuk memverifikasi worker hidup."""
    logger.info('celery ping ok')
    return 'pong'
```

**Verifikasi (setelah stack naik, Fase 5):**
```bash
docker compose exec backend python -c "
from core.tasks import ping; print(ping.delay().get(timeout=15))"
```
Expected: `pong`

**Commit:** `feat(celery): add worker lifecycle settings + first shared_task for healthcheck`

**Gate Fase 3:** `uv sync` bersih, `collectstatic` sukses, `render_pdf` menghasilkan PDF valid, test Celery ping lulus.

**Rollback:** `git revert <sha>` per task — tiap task punya commit sendiri.

---

# FASE 4 — Image Docker backend

**Tujuan:** image yang punya WeasyPrint (pango/cairo) + gunicorn + celery.

**File:** Create `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# ── System deps ───────────────────────────────────────────────────────────
# WeasyPrint butuh Pango/Cairo (bukan paket pip) + font utk PDF berbahasa Indonesia.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 \
        libgdk-pixbuf-2.0-0 libffi8 shared-mime-info \
        fonts-dejavu-core fontconfig \
        postgresql-client curl \
    && rm -rf /var/lib/apt/lists/*

# ── uv ────────────────────────────────────────────────────────────────────
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /usr/local/bin/

WORKDIR /app

# Layer cache: dependency dulu, kode belakangan
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8000
CMD ["gunicorn", "-c", "deploy/gunicorn.conf.py", "config.wsgi:application"]
```

**File:** Create `backend/.dockerignore`

```
.venv/
__pycache__/
*.py[cod]
backups/
staticfiles/
.git/
*.log
.env
```

**Verifikasi build + WeasyPrint benar-benar jalan di dalam image:**
```bash
cd /srv/digilio-v2/backend
docker build -t digilio-backend:test .
docker run --rm digilio-backend:test python -c "
from weasyprint import HTML
pdf = HTML(string='<h1>Tes PDF Digilio</h1>').write_pdf()
print('PDF', len(pdf), pdf[:5]); assert pdf[:5] == b'%PDF-'
"
```
Expected: `PDF <bytes> b'%PDF-'` — **kalau ini gagal, semua PDF produksi akan gagal; jangan lanjut.**

**Commit:** `chore(deploy): add backend Dockerfile with WeasyPrint system deps + uv`

**Gate Fase 4:** image ter-build, tes WeasyPrint lulus di dalam container.

**Rollback:** `docker image rm digilio-backend:test`.

---

# FASE 5 — Docker Compose produksi + environment

**Tujuan:** seluruh stack jalan, port sensitif tidak terekspos.

**File:** Create `/srv/digilio-v2/.env` (chmod 600, **tidak di-commit**)

```ini
# ── Django ──
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<hasil Step 0.3>
DJANGO_ALLOWED_HOSTS=digilio.example.com,www.digilio.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://digilio.example.com
DJANGO_CORS_ALLOWED_ORIGINS=https://digilio.example.com

# ── Database ──
POSTGRES_DB=digilio
POSTGRES_USER=digilio
POSTGRES_PASSWORD=<hasil Step 0.3>
DATABASE_URL=postgresql://digilio:<POSTGRES_PASSWORD>@postgres:5432/digilio

# ── Redis / Celery ──
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# ── Gunicorn ──
GUNICORN_WORKERS=3
```

**File:** Create `.env.example` (versi placeholder, **boleh di-commit**)

```ini
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=change-me
DJANGO_ALLOWED_HOSTS=example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com
DJANGO_CORS_ALLOWED_ORIGINS=https://example.com
POSTGRES_DB=digilio
POSTGRES_USER=digilio
POSTGRES_PASSWORD=change-me
DATABASE_URL=postgresql://digilio:change-me@postgres:5432/digilio
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
GUNICORN_WORKERS=3
```

**File:** Create `docker-compose.prod.yml`

```yaml
name: digilio-v2

x-backend-common: &backend-common
  build:
    context: ./backend
  image: digilio-backend:latest
  restart: unless-stopped
  env_file: .env
  volumes:
    - staticfiles:/app/staticfiles
    - backups:/app/backups
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy

services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    env_file: .env
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./deploy/postgres-tuning.conf:/etc/postgresql/conf.d/tuning.conf:ro
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 10s
      timeout: 5s
      retries: 10
    deploy:
      resources:
        limits: { memory: 1g }        # host 4 GB → Postgres max 1 GB

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --save 60 1 --loglevel warning --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 10
    deploy:
      resources:
        limits: { memory: 320m }

  backend:
    <<: *backend-common
    command: >
      sh -c "python manage.py migrate --noinput &&
             python manage.py collectstatic --noinput &&
             gunicorn -c deploy/gunicorn.conf.py config.wsgi:application"
    expose: ["8000"]                 # TIDAK di-publish ke host
    deploy:
      resources:
        limits: { memory: 1500m }

  celery-worker:
    <<: *backend-common
    command: celery -A config worker -l info --concurrency=2
    deploy:
      resources:
        limits: { memory: 800m }

  celery-beat:
    <<: *backend-common
    command: celery -A config beat -l info
    deploy:
      resources:
        limits: { memory: 256m }

  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports: ["80:80", "443:443"]
    volumes:
      - ./deploy/Caddyfile:/etc/caddy/Caddyfile:ro
      - ./frontend/dist:/srv/frontend:ro
      - staticfiles:/srv/static:ro
      - caddydata:/data
      - caddyconfig:/config
    depends_on: [backend]
    deploy:
      resources:
        limits: { memory: 192m }

volumes:
  pgdata:
  redisdata:
  staticfiles:
  backups:
  caddydata:
  caddyconfig:
```

**File:** Create `deploy/postgres-tuning.conf` (B12 — Postgres belum dituning sama sekali)

```ini
# Tuning untuk host 4 GB (CX22). Naikkan bila RAM lebih besar.
shared_buffers = 512MB
effective_cache_size = 1536MB
work_mem = 16MB
maintenance_work_mem = 128MB
max_connections = 60
random_page_cost = 1.1          # SSD, bukan HDD (default 4.0 = asumsi HDD)
effective_io_concurrency = 200
wal_compression = on
log_min_duration_statement = 1000   # catat query >1 detik
```

**File:** Create `deploy/Caddyfile`

```
{$DOMAIN} {
    encode gzip zstd

    handle /api/* {
        reverse_proxy backend:8000
    }
    handle /admin/* {
        reverse_proxy backend:8000
    }
    handle /static/* {
        root * /srv/static
        file_server
    }

    handle {
        root * /srv/frontend
        try_files {path} /index.html     # SPA fallback (react-router)
        file_server
    }

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        -Server
    }

    log {
        output file /data/access.log {
            roll_size 20mb
            roll_keep 10
        }
    }
}
```

Tambahkan `DOMAIN=digilio.example.com` ke `.env`.

**Step 5.2 — Modifikasi settings.py untuk membaca env (B1–B5)**

**File:** Modify `backend/config/settings.py` — ganti baris 10–12:

```python
# SEBELUM
SECRET_KEY='django...tion'
DEBUG = True
ALLOWED_HOSTS = ['*']

# SESUDAH
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-only-insecure-key')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes')
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',') if h.strip()
]
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()
]
```

**Catatan penting:** default `DEBUG='True'` → **dev lokal Anda tidak berubah perilakunya**. Produksi memaksa `False` lewat `.env`. Ini menjaga alur kerja Anda sekarang tetap jalan.

**File:** Modify `backend/config/settings.py` — blok DATABASES:

```python
import urllib.parse

_db = urllib.parse.urlparse(os.environ.get('DATABASE_URL', ''))
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _db.path.lstrip('/') or os.environ.get('POSTGRES_DB', 'digilio'),
        'USER': _db.username or os.environ.get('POSTGRES_USER', 'digilio'),
        'PASSWORD': _db.password or os.environ.get('POSTGRES_PASSWORD', 'digilio'),
        'HOST': _db.hostname or os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': _db.port or int(os.environ.get('POSTGRES_PORT', 5432)),
        'CONN_MAX_AGE': 60,          # reuse koneksi → hemat ~30% waktu per request
        'CONN_HEALTH_CHECKS': True,
    }
}
```

**File:** Modify `backend/config/settings.py` — CORS:

```python
CORS_ALLOW_ALL_ORIGINS = DEBUG        # dev: bebas; prod: False
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get('DJANGO_CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()
]
```

**File:** Modify `backend/config/settings.py` — Celery + Redis, ganti yang hardcoded `localhost`:

```python
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
```

**Step 5.3 — Jalankan stack**

```bash
cd /srv/digilio-v2
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
docker compose -f docker-compose.prod.yml ps
```

**Verifikasi:**
```bash
# semua harus "running"/"healthy"
docker compose -f docker-compose.prod.yml ps
# backend merespons di dalam network
docker compose -f docker-compose.prod.yml exec backend curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/access/me/
# harus 401 (server hidup, tanpa token)
```
Expected: 6 container `Up`, `/api/access/me/` → `401`.
Pastikan port TIDAK terbuka di host: `ss -tlnp | grep -E ':5432|:6379|:8000'` → **kosong** (hanya 80/443).

**Commit:** `chore(deploy): add production compose stack, caddy, pg tuning, env-driven settings`

**Gate Fase 5:** 6 container sehat, 5432/6379/8000 tidak terekspos, `DEBUG=False` terkonfirmasi:
```bash
docker compose exec backend python -c "
import os,django; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); django.setup()
from django.conf import settings as s; print('DEBUG', s.DEBUG, '| HOSTS', s.ALLOWED_HOSTS)"
```
Expected: `DEBUG False | HOSTS ['digilio.example.com', ...]`

**Rollback:** `docker compose -f docker-compose.prod.yml down` lalu `git revert`.

---

# FASE 6 — Frontend produksi

**Tujuan:** frontend jadi file statis (bukan vite dev server yang makan 358 MB RAM).

**Step 6.1 — Build di server**

```bash
cd /srv/digilio-v2/frontend
corepack enable && corepack prepare pnpm@latest --activate
pnpm install --frozen-lockfile
pnpm build          # = tsc -b && vite build
ls -la dist/ && du -sh dist
```

Verify: `dist/index.html` + `dist/assets/` ada. Ukuran ±4–5 MB.

**Catatan:** `frontend/dist/` **di-gitignore** → `git pull` di server **tidak** membawa build lama. Setelah tiap `git pull` yang menyentuh frontend, jalankan ulang `pnpm build`.

**Step 6.2 — Tambahkan API base di build produksi**

**File:** Modify `frontend/src/api/client.ts:4` — biarkan `baseURL: '/api'` **tanpa perubahan**. Karena Caddy menyajikan frontend dan `/api` di **origin yang sama**, tidak perlu ubah URL dan tidak ada CORS. ✅ **Tidak ada file frontend yang diubah** untuk deploy.

**Step 6.3 — Reload Caddy agar membaca dist baru**

```bash
cd /srv/digilio-v2 && docker compose -f docker-compose.prod.yml restart caddy
```

**Verifikasi:**
```bash
curl -sI https://digilio.example.com/ | head -3
curl -s https://digilio.example.com/ | grep -o '<title>[^<]*</title>'
curl -sI https://digilio.example.com/assets/$(ls frontend/dist/assets | grep '\.js$' | head -1) | grep -i cache-control
```
Expected: HTTP 200, title aplikasi tampil, asset punya `cache-control: public, max-age=...`.

**Gate Fase 6:** halaman login termuat via HTTPS (belum login).

**Rollback:** `git checkout -- frontend/` + `pnpm build` ulang.

---

# FASE 7 — HTTPS & DNS

**Step 7.1 — Arahkan DNS**

Di panel DNS domain: buat **A record** `digilio.example.com` → `$SERVER_IP` (dan `www` bila perlu). Tunggu propagasi (`dig +short digilio.example.com` → IP server).

**Step 7.2 — Caddy ambil sertifikat**

```bash
docker compose -f docker-compose.prod.yml logs caddy | grep -i "certificate obtained"
```

Verify: log memuat `certificate obtained successfully`, lalu:
```bash
curl -sI https://digilio.example.com | head -5
echo | openssl s_client -servername digilio.example.com -connect digilio.example.com:443 2>/dev/null | openssl x509 -noout -dates -issuer
```
Expected: HTTP/2 200, `HSTS` header ada, sertifikat dari Let's Encrypt dengan masa berlaku ±90 hari.

**Step 7.3 — Paksa HTTPS + www→apex (sudah otomatis di Caddy)**

Verify: `curl -sI http://digilio.example.com | head -2` → `308 Permanent Redirect` ke `https://...`.

**Gate Fase 7:** HTTPS valid, HTTP redirect, HSTS aktif.

**Rollback:** perbaiki DNS; hapus `caddydata` volume untuk memaksa ambil ulang sertifikat (`docker compose down && docker volume rm digilio-v2_caddydata`).

---

# FASE 8 — Migrasi data dari server lama

**Tujuan:** memindahkan data sekarang (21 MB, 91 tabel) ke Postgres produksi.

**Step 8.1 — Dump dari lokal (di mesin ini)**

```bash
docker exec digilio-postgres pg_dump -U digilio -d digilio \
  --format=custom --no-owner --no-privileges \
  > /tmp/digilio-$(date +%Y%m%d-%H%M%S).dump
ls -lh /tmp/digilio-*.dump
```

Verify: file dump ada, ukuran masuk akal (>1 MB).

**Step 8.2 — Kirim ke server**

```bash
scp /tmp/digilio-*.dump deploy@$SERVER_IP:/tmp/
```

**Step 8.3 — Restore**

```bash
cd /srv/digilio-v2
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_restore -U digilio -d digilio --clean --if-exists --no-owner </tmp/digilio-<stamp>.dump
```

**Verifikasi (WAJIB cocok dengan sumber):**
```bash
docker compose -f docker-compose.prod.yml exec -T postgres psql -U digilio -d digilio -c "
SELECT (SELECT count(*) FROM auth_user) AS users,
       (SELECT count(*) FROM core_purchaseorder) AS po,
       (SELECT count(*) FROM core_salesorder) AS so,
       (SELECT count(*) FROM core_product) AS produk,
       (SELECT count(*) FROM core_sequence) AS seq;"
```
Bandingkan dengan sumber (data sekarang: `core_product`=5, `core_sequence`=7, `chatter_log`=235, 360 permission).

**Step 8.4 — Reset urutan PK (penting setelah pg_restore)**

```bash
docker compose -f docker-compose.prod.yml exec -T backend python manage.py shell -c "
from django.core.management import call_command; call_command('sqlsequencereset','core');" \
| docker compose -f docker-compose.prod.yml exec -T postgres psql -U digilio -d digilio
```

Verify: buat 1 record baru lewat UI (mis. Customer) → **tidak** error `duplicate key value violates unique constraint`.

**Gate Fase 8:** jumlah baris tabel utama cocok dengan sumber; create record baru sukses.

**Rollback:** `docker compose stop backend celery-worker celery-beat` → restore ulang dari dump; data produksi belum pernah ditulis user.

---

# FASE 9 — Backup, monitoring, operasional

**Tujuan:** bisa pulih dari kegagalan; tahu saat ada masalah.

**File:** Create `deploy/backup.sh`

```bash
#!/usr/bin/env bash
# Backup Postgres harian + retensi 14 hari. Dipasang sebagai cron di host.
set -euo pipefail
cd /srv/digilio-v2
STAMP=$(date +%Y%m%d-%H%M%S)
OUT=/srv/backups
mkdir -p "$OUT"

docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U digilio -d digilio --format=custom --no-owner \
  > "$OUT/digilio-$STAMP.dump"

# Verifikasi dump tidak kosong/rusak (gagal → exit non-zero → cron kirim alert)
test -s "$OUT/digilio-$STAMP.dump"
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_restore --list < "$OUT/digilio-$STAMP.dump" > /dev/null

find "$OUT" -name 'digilio-*.dump' -mtime +14 -delete
echo "$(date -Is) backup ok: digilio-$STAMP.dump ($(stat -c%s "$OUT/digilio-$STAMP.dump") bytes)"
```

**File:** Modify `deploy/backup.sh` → `chmod +x` lalu pasang cron:

```bash
sudo mkdir -p /srv/backups && sudo chown deploy:deploy /srv/backups
chmod +x /srv/digilio-v2/deploy/backup.sh
crontab -e
# tambahkan:
0 2 * * * /srv/digilio-v2/deploy/backup.sh >> /var/log/digilio-backup.log 2>&1
```

Verify: `bash /srv/digilio-v2/deploy/backup.sh` → cetak `backup ok: ...` dan file >1 MB muncul di `/srv/backups/`.

**Step 9.2 — Backup off-site (WAJIB — server mati ≠ data aman)**

Opsi termurah: **Hetzner Storage Box** (BX11, 1 TB, ±€3.81/bln) via SSH/rclone.

```bash
apt install -y rclone
rclone config       # buat remote "hetzner-storage" (SFTP ke Storage Box)
# tambahkan ke crontab:
30 2 * * * rclone copy /srv/backups hetzner-storage:digilio-backups --max-age 30d
```

**Step 9.3 — Healthcheck endpoint**

**File:** Modify `backend/core/urls.py` — tambahkan sebelum baris terakhir `urlpatterns`:

```python
    # Health check (tanpa auth) untuk monitoring & rolling restart
    path('healthz/', health_check, name='health-check'),
```

**File:** Modify `backend/core/dashboard_api.py` — tambahkan di akhir file:

```python
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Liveness+readiness: cek koneksi DB & Redis. Tidak butuh auth."""
    from django.core.cache import cache
    from django.db import connection

    status = {'db': False, 'cache': False}
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
        status['db'] = True
    except Exception as exc:
        status['db_error'] = str(exc)[:200]
    try:
        cache.set('healthz', '1', 10)
        status['cache'] = cache.get('healthz') == '1'
    except Exception as exc:
        status['cache_error'] = str(exc)[:200]

    ok = status['db'] and status['cache']
    return Response({'ok': ok, **status}, status=200 if ok else 503)
```

Tambahkan juga import di `core/urls.py`: `from core.dashboard_api import dashboard_data, health_check` dan `from rest_framework.permissions import AllowAny` di `dashboard_api.py`.

Verify:
```bash
curl -s https://digilio.example.com/api/healthz/ | python3 -m json.tool
```
Expected: `{"ok": true, "db": true, "cache": true}` dengan HTTP 200.

**Step 9.4 — Rotasi log Docker + Uptime monitoring**

Tambah ke `docker-compose.prod.yml` pada tiap service (atau lewat `/etc/docker/daemon.json`):

```yaml
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "5" }
```

Untuk monitoring eksternal: daftarkan `https://digilio.example.com/api/healthz/` di **Uptime Kuma** (self-host, container tambahan) atau layanan gratis seperti BetterStack/Healthchecks.io → alert ke email/Telegram bila HTTP ≠ 200.

**Commit:** `chore(ops): add db backup script, healthz endpoint, log rotation`

**Gate Fase 9:** backup manual sukses + terverifikasi, cron terpasang, `/api/healthz/` → 200.

---

# FASE 10 — Celery aktif untuk beban berat (follow-up)

**Status:** **tidak menghambat go-live.** Kerjakan setelah aplikasi stabil, karena ini menyentuh `imports/views.py` dan `reports/views.py` (bukan model).

**Tujuan:** memindahkan pekerjaan berat dari proses web → worker, menghapus batas 100 baris import.

**Task 10.1 — `imports/tasks.py`**
```python
from celery import shared_task
from .importer import execute_import


@shared_task(name='imports.execute', bind=True, max_retries=2)
def execute_import_task(self, model_name, valid_rows, error_rows, field_mapping,
                        unmapped_headers, child_groups):
    return execute_import(model_name, valid_rows, error_rows, field_mapping,
                          unmapped_headers, child_groups)
```
Lalu di `imports/views.py`: **hapus** blok `if total > 100: return Response(...)` dan panggil `.delay(...)` + kembalikan `task_id`.

**Task 10.2 — `reports/tasks.py`**: `render_pdf_task(model_name, record_id, template_key, fmt)` → simpan hasil ke volume `backups`/`media`, endpoint status `GET /api/print/task/<task_id>/`.

**Task 10.3 — Scheduler fitur**: isi `CELERY_BEAT_SCHEDULE` untuk tugas periodik yang Anda mau (mis. aging report harian, refresh dashboard cache, reminder jatuh tempo).

Verify tiap task: kirim task → `GET /api/print/task/<id>/` → `{"status":"SUCCESS"}`; cek CPU worker naik sementara **tanpa** menaikkan latency endpoint lain (`ab`/load test paralel).

---

# FASE 11 — Auto-start & deploy berikutnya

**File:** Create `/etc/systemd/system/digilio-v2.service`

```ini
[Unit]
Description=Digilio v2 (Docker Compose production stack)
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=deploy
WorkingDirectory=/srv/digilio-v2
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d --remove-orphans
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now digilio-v2.service
sudo reboot
# setelah reboot:
systemctl is-active digilio-v2 && curl -s -o /dev/null -w "%{http_code}\n" https://digilio.example.com/api/healthz/
```
Expected: `active`, `200` — aplikasi hidup sendiri setelah reboot.

**File:** Create `deploy/deploy.sh`

```bash
#!/usr/bin/env bash
# Deploy rilis baru. Jalankan sebagai user deploy.
set -euo pipefail
cd /srv/digilio-v2

echo "==> backup sebelum deploy"
bash deploy/backup.sh

echo "==> ambil kode terbaru"
git fetch --all --prune
git log --oneline HEAD..origin/master | head -20
read -rp "Lanjut deploy commit di atas? [y/N] " ok
[[ "$ok" == "y" ]] || exit 1
git pull --ff-only origin master

echo "==> build ulang backend"
docker compose -f docker-compose.prod.yml build backend

echo "==> frontend (hanya bila berubah)"
if git diff --name-only HEAD@{1} HEAD | grep -q '^frontend/'; then
  (cd frontend && pnpm install --frozen-lockfile && pnpm build)
fi

echo "==> restart rolling"
docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker compose -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml restart caddy

echo "==> verifikasi"
sleep 5
curl -fsS https://digilio.example.com/api/healthz/ && echo " DEPLOY OK"
```

**Rollback:** `git revert <sha> && bash deploy/deploy.sh` · DB: `docker compose exec -T postgres pg_restore -U digilio -d digilio --clean --if-exists < /srv/backups/<dump>` · image sebelumnya: `docker tag digilio-backend:prev digilio-backend:latest`.

---

# Expected Results

| Fase | Yang Anda dapat |
|---|---|
| 0–1 | Server Hetzner ter-hardening: SSH key-only, ufw (22/80/443), fail2ban, swap 2 GB, timezone WIB, Docker |
| 2 | Repo ter-clone di `/srv/digilio-v2` via deploy key read-only |
| 3 | `gunicorn` terpasang · paket `django-channels` palsu dibuang · **bug PDF/print diperbaiki** (PDF valid, terverifikasi) · `STATIC_ROOT` + cache Redis · config gunicorn · Celery siap dengan `core.ping` |
| 4 | Image `digilio-backend` dengan Pango/Cairo → WeasyPrint terbukti jalan di dalam container |
| 5 | 6 container sehat (postgres, redis, backend, celery-worker, celery-beat, caddy) · `.env` berisi semua secret baru · `DEBUG=False` · port 5432/6379/8000 **tertutup** dari internet · Postgres tertuning untuk SSD |
| 6 | Frontend jadi file statis ±4–5 MB (hemat ~358 MB RAM vs vite dev) |
| 7 | HTTPS Let's Encrypt otomatis (+auto-renew), HTTP→HTTPS redirect, header keamanan (HSTS, nosniff, DENY frame) |
| 8 | Data produksi = data sekarang (21 MB, 91 tabel), baris terverifikasi cocok, PK sequence direset |
| 9 | Backup harian 02:00 + retensi 14 hari + **verifikasi dump** + salinan off-site · `/api/healthz/` untuk monitoring |
| 10 | (Follow-up) Import tanpa batas 100 baris · PDF asinkron lewat worker · scheduler `CELERY_BEAT_SCHEDULE` siap |
| 11 | Auto-start setelah reboot · script deploy 1 perintah dengan backup otomatis di awal |

**Hasil akhir:** https://digilio.example.com melayani 25–40 concurrent user di 1 server, dengan rollback, backup terverifikasi, dan worker terpisah untuk beban berat.

---

# Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| **PDF masih sinkron saat go-live** → user menunggu 0,2–0,7 s/proses PDF dan menahan 1 gunicorn worker | `timeout=120` di gunicorn + 3 worker. Fase 10 memindahkannya ke Celery. Jika PDF dipakai intens, naikkan `GUNICORN_WORKERS` ke 4–5 (di CX32). |
| **WeasyPrint menaikkan RSS tiap render** (terukur +3–5 MB/render) | `max_requests=1000` + `max_requests_jitter=100` di gunicorn; `CELERY_WORKER_MAX_TASKS_PER_CHILD=50`. Alternatif jangka panjang: pre-render ke cache/S3. |
| **`page_size=0` (load semua record)** menjadi masalah saat data tumbuh (B14) | Pantau `log_min_duration_statement=1000`. Follow-up terpisah: pagination server-side + AG Grid server-side row model. **Tidak menghambat go-live** karena data sekarang hanya 21 MB. |
| **`CONN_MAX_AGE=60` × 3 worker + 2 celery** = ~5–10 koneksi; `max_connections=60` di tuning | Cukup, tapi bila nanti tambah worker hitung ulang (worker × 1 + cadangan 20). |
| **Migrasi data salah / urutan PK bentrok** | Fase 8 punya verifikasi jumlah baris **wajib cocok** + uji create record baru sebelum go-live. |
| **Data hilang karena server mati** | Backup harian terverifikasi + off-site (Fase 9.2). |
| **Deploy merusak produksi** | `deploy.sh` mem-backup dulu; tag image `digilio-backend:prev` untuk rollback cepat; `git revert` untuk kode. |
| **`git pull` membawa build frontend basi** | `frontend/dist` di-gitignore → `deploy.sh` otomatis `pnpm build` bila ada perubahan di `frontend/`. |
| **Build image kehabisan RAM di CX22 (4 GB)** | Butuh swap (Fase 0.2). Kalau build gagal: build di lokal lalu `docker save | ssh docker load`, atau pakai Hetzner Container Registry. |
| **Ini deploy pertama — banyak file infra baru** | Perubahan **tidak menyentuh `core/models/**`**. Semua commit terpisah per task → `git revert` per task bila ada masalah. |

---

# Open Questions (butuh jawaban Anda sebelum Fase 0 dijalankan)

1. **Spesifikasi server Hetzner yang dibeli?** (CX22 2vCPU/4GB · CX32 4vCPU/8GB · CX42 …) — menentukan `GUNICORN_WORKERS` (3 untuk CX22, 5 untuk CX32) dan `shared_buffers`.
2. **Domain & DNS:** pakai `digilio.online` (yang sudah Anda punya, sekarang untuk landing page) atau subdomain baru seperti `app.digilio.online`? Landing page lama tetap harus jalan, atau digantikan?
3. **Akses untuk saya deploy:** apakah saya boleh SSH ke server itu? Kalau ya, saya butuh salah satu: (a) IP + private key, atau (b) Anda jalankan sendiri perintahnya dan saya arahkan. Repo di GitHub private — perlu akses baca.
4. **MinIO/Meilisearch:** sudah dikonfirmasi tidak dipakai. **Jangan** dipasang di server baru — setuju?
5. **Email notifikasi:** mau ada alert email (backup gagal, healthz down)? Kalau ya, perlu SMTP/Resend — kalau tidak, alert ke Telegram saja (gratis, via webhook).
6. **Jam backup:** default 02:00 WIB. OK?
7. **Fitur scheduler yang Anda maksud** untuk `CELERY_BEAT_SCHEDULE` — apa saja? (Untuk Fase 10.)

---

# Verification Checklist Go-Live

- [ ] `https://<domain>/` → halaman login tampil, sertifikat valid, HSTS ada
- [ ] Login `admin` (atau user produksi) sukses → dashboard termuat
- [ ] Buka 1 modul list (mis. Purchase Order) → data muncul, kolom rapi
- [ ] Buka 1 form → simpan → data tersimpan
- [ ] **Download PDF Purchase Order → file PDF terbuka dengan isi benar** (bug B9 sudah beres)
- [ ] Import CSV ≤100 baris → sukses; >100 baris → sukses (Fase 10) atau pesan batas jelas
- [ ] `curl https://<domain>/api/healthz/` → `{"ok": true}`
- [ ] `ss -tlnp | grep -E ':5432|:6379|:8000'` → **kosong**
- [ ] `docker compose ps` → 6 container sehat, `restart: unless-stopped` semua
- [ ] Reboot server → aplikasi hidup sendiri dalam <60 detik
- [ ] `sudo /srv/digilio-v2/deploy/backup.sh` → `backup ok`, file terverifikasi `< 3 MB` untuk DB 21 MB
- [ ] Load test 20 concurrent → `p95 < 1.5 s`, 0 error (baseline sekarang: 20 conc = `p95 1,9 s`)
- [ ] `docker compose logs backend | grep -c "Internal Server Error"` → `0`
- [ ] Cek `DEBUG False` via shell
- [ ] `git log --oneline` di server → commit Fase 3 sudah ada semua
