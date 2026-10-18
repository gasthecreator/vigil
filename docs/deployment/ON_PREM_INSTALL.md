# Vigil On-Premise Installation & Air-Gapped Deployment Guide

**Document ID:** VIG-DEPLOY-001  
**Version:** 1.0.0-rc.1  
**Target Audience:** Hospital Systems Engineers, Clinical IT Administrators, Lead DevSecOps  
**Compliance Standards:** ISO 14971:2019, IEC 62304:2006/AMD 1:2015, NDPA 2023, HIPAA Security Rule  

---

## 1. Overview & Operational Context

Vigil is engineered for deployment within low-resource, intermittent-connectivity, or completely air-gapped clinical environments such as regional and tertiary oncology hospitals across Sub-Saharan Africa. The system supports full on-premise execution with zero external cloud dependencies.

### Key Deployment Characteristics
- **Air-Gapped Operation:** All Python wheels, Node dependencies, font assets, and ML model weights are vendored locally; no runtime internet access required.
- **Data Sovereignty:** All Protected Health Information (PHI) and clinical trial emulation records remain entirely within hospital-controlled perimeter boundaries.
- **Fail-Safe Persistence:** Robust dual database support (PostgreSQL 16+ for enterprise multi-workstation clusters, SQLite 3.40+ in Write-Ahead-Logging mode for single-workstation provincial facilities).

---

## 2. System Prerequisites

### Hardware Requirements
| Component | Minimum Specification | Recommended Specification |
|:---|:---|:---|
| **CPU** | 4 x86_64 or ARM64 cores | 8 cores (>= 2.5 GHz) |
| **RAM** | 8 GB ECC RAM | 16 GB ECC RAM |
| **Storage** | 50 GB SSD (ext4/ZFS) | 200 GB NVMe SSD (mirrored RAID-1) |
| **Network** | 1 Gbps Local Area Network | 1 Gbps LAN with redundant NICs |

### Operating System & Core Libraries
- **Tested Operating Systems:** Ubuntu 22.04 LTS / 24.04 LTS, Debian 12 (Bookworm)
- **Runtime Dependencies:**
  - Python 3.12 (with `libsqlite3`, `libffi-dev`, `libssl-dev`)
  - Node.js 20 LTS (only required if serving static web bundle dynamically)
  - Nginx 1.22+ or Caddy 2.7+ (for local TLS 1.3 termination)

---

## 3. Pre-Flight Security Checklist

Before initiating production deployment, ensure the following environment variables are securely generated and configured. **The installation script `scripts/install_on_prem.py` automatically validates and refuses to proceed if any insecure default is detected.**

1. `REQUIRE_AUTH=true`: Mandatory authentication enforcement.
2. `JWT_SECRET_KEY`: Cryptographically secure random 32-byte hex string (e.g., generated via `openssl rand -hex 32`). Reject generic tokens like "secret", "admin", or "change-me".
3. `FIELD_ENCRYPTION_KEY`: 32-byte AES-GCM master key used for column-level encryption of patient identifiers, contact tokens, and share credentials.
4. `CORS_ORIGINS`: Explicit hospital hostname (e.g., `https://vigil.oncology.local,https://192.168.1.100`). Wildcard `*` is strictly blocked in production.
5. `DATABASE_URL`: Production connection string (e.g. `postgresql://vigil_user:SECURE_PASS@localhost:5432/vigil_db` or absolute SQLite path).

---

## 4. Automated Step-by-Step Installation

The primary mechanism for deploying Vigil is the automated, self-validating installer `scripts/install_on_prem.py`.

### Step 1: Create Service User & Directory Hierarchy
```bash
sudo useradd -r -s /bin/bash -m -d /opt/vigil vigil
sudo mkdir -p /opt/vigil/data /opt/vigil/logs /opt/vigil/backups
sudo chown -R vigil:vigil /opt/vigil
```

### Step 2: Unpack Release Bundle
```bash
sudo -u vigil tar -xzf vigil-v1.0.0-rc.1.tar.gz -C /opt/vigil/
cd /opt/vigil
```

### Step 3: Run Automated On-Premise Installer
Execute the installation script with required target environment flags:

```bash
sudo -u vigil python3 scripts/install_on_prem.py \
  --config-file /opt/vigil/config/production.env \
  --migrate-db \
  --seed-admin \
  --verify
```

The automated installer executes the following sequence:
1. **Security Policy Audit:** Validates secret lengths, entropy, CORS confinement, and auth requirements.
2. **Virtual Environment Setup:** Installs dependencies from local offline wheel cache.
3. **Database Migration:** Executes Alembic migrations (`alembic upgrade head`) to construct schemas.
4. **Audit Ledger Genesis:** Initializes the append-only, SHA-256 hash-chained audit ledger.
5. **Admin Credential Bootstrap:** Securely provisions the root `admin` account, printing credentials to stdout once.
6. **Self-Test Verification:** Queries the internal `/health` and OpenAPI authorization schema to ensure zero leaked routes.

---

## 5. Systemd Service Configuration

Create `/etc/systemd/system/vigil-api.service`:

```ini
[Unit]
Description=Vigil Clinical Oncology Decision Support API
After=network.target postgresql.service

[Service]
Type=simple
User=vigil
Group=vigil
WorkingDirectory=/opt/vigil
EnvironmentFile=/opt/vigil/config/production.env
ExecStart=/opt/vigil/.venv/bin/uvicorn vigil_api.main:app --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers
Restart=always
RestartSec=5s
LimitNOFILE=65536
StandardOutput=append:/opt/vigil/logs/api-access.log
StandardError=append:/opt/vigil/logs/api-error.log

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vigil-api.service
sudo systemctl start vigil-api.service
```

---

## 6. Reverse Proxy & Local TLS Configuration (Nginx)

Create `/etc/nginx/sites-available/vigil`:

```nginx
server {
    listen 443 ssl http2;
    server_name vigil.hospital.local;

    ssl_certificate /etc/ssl/certs/vigil-hospital.crt;
    ssl_certificate_key /etc/ssl/private/vigil-hospital.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;

    # API Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Frontend Static Distribution
    location / {
        root /opt/vigil/apps/web/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 7. Operational Runbook & Maintenance

### Daily Automated Health Check
Run the verification check via local cron:
```bash
0 * * * * /opt/vigil/.venv/bin/python /opt/vigil/scripts/install_on_prem.py --verify-only
```

### Database & Audit Ledger Backups
Refer to `docs/resilience/DISASTER_RECOVERY.md` for daily cryptographic backup commands:
```bash
python3 scripts/backup_restore.py backup --output-dir /opt/vigil/backups/daily
```
