# Deploy sem Docker

## 1. Dependencias

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip nginx
```

## 2. Aplicacao

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -e .[prod]
cp .env.example .env
python -m app.bootstrap
```

## 3. systemd

Copie `app/templates/mayacorp_crm.service` para `/etc/systemd/system/mayacorp_crm.service` e ajuste os caminhos.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mayacorp_crm
sudo systemctl status mayacorp_crm
```

## 4. Nginx

Copie `deploy/nginx.mayacorp_crm.conf` para `/etc/nginx/sites-available/mayacorp_crm`.

```bash
sudo ln -s /etc/nginx/sites-available/mayacorp_crm /etc/nginx/sites-enabled/mayacorp_crm
sudo nginx -t
sudo systemctl reload nginx
```
