# Deploying Specs to production

This runbook is written so that someone (or an AI assistant) with no memory of the project can follow it.
Read [README.md](README.md) first for what the project is. Current target: **a fresh install on the
production server, which has no database yet**, so there is no old data to migrate.

> **Rules for whoever runs this, human or assistant**
> - Ask before any destructive action (deleting volumes, containers, certificates, data).
> - Never paste secrets (API keys, passwords) into chats or commits. `.env*` files are git-ignored on purpose.
> - Never run `make wipe` or `make clean`. `make down` is safe (it keeps the data volumes) **only with the
>   current Makefile**: older versions ran `down --volumes` and deleted the databases. Always `git pull` before using `make`.

## What the stack is

Docker Compose services: `django`, `nginx`, `postgres`, `mongodb`, `qdrant`, `mongo-express`
(certbot is optional, under the `letsencrypt` profile). The Django image is built `FROM eavedillo/django:latest`
(public on Docker Hub, about 2 GB, already contains `mcp` and the Nebius/LlamaIndex libraries; no PyTorch).
Databases listen on `127.0.0.1` only; nginx publishes 80 and 443. Data lives in the named volumes
`postgres_data`, `mongodb_data` and `qdrant_data`.

## 1. Get the code

```bash
git pull            # or: git clone https://github.com/ErnestoAvedillo/mechanics.git
git log -1 --oneline
```

## 2. Create the production environment file

`.env_prod` is git-ignored, so it must be created on the server. Start from the example and set real values:

```bash
cp .env.example .env_prod
```

Set at least:

| Variable | Production value |
|---|---|
| `DJANGO_DEBUG` | `False` (gunicorn, real SMTP; with `True` verification codes only go to the logs) |
| `DJANGO_SECRET_KEY` | a long random string, **required**: without it Django falls back to a weak default |
| `NEBIUS_API_KEY` | Nebius Token Factory key |
| `LLAMA_CLOUD_API_KEY` | LlamaParse key (OCR for scanned PDFs) |
| `QDRANT_URL` / `QDRANT_API_KEY` | `http://qdrant:6333` and empty (Qdrant runs in the stack) |
| `POSTGRES_*`, `MONGO_*`, `ME_CONFIG_*` | new passwords; `ME_CONFIG_MONGODB_ADMINPASSWORD` and the password inside `ME_CONFIG_MONGODB_URL` must equal `MONGO_INITDB_ROOT_PASSWORD` |
| `NO_REPLY_EMAIL`, `NO_REPLY_PASSWORD`, `SMTP_HOST`, `SMTP_PORT` | sender account; Gmail needs an **app password** (needs 2-step verification); port 465 = SSL, 587 = STARTTLS |
| `RECAPTCHA_SITE_KEY` / `RECAPTCHA_SECRET_KEY` | only for the calculators' share-by-email form |

## 3. Build and start

```bash
make switch-prod
```

This copies `.env_prod` over `.env`, uses `nginx.conf.prod`, then builds and starts everything. It aborts if
`./certs/live/ernestoavedillo.com` does not exist (see "TLS certificate" below). The first start takes a few
minutes: `django` retries until PostgreSQL is ready, then `start.sh` runs `collectstatic` and `migrate`
(creates every table from scratch). Watch it with `docker compose logs -f django`.

Then publish the static files and restart Django:

```bash
make production
```

`backfill_documents`, `index_pending` and `extract_metadata` exist to migrate data from older versions. A fresh
install does not need them.

## 4. Smoke test

```bash
docker compose ps                                              # all services Up, django healthy
curl -sI https://ernestoavedillo.com | head -1                 # 200
docker logs django --since 10m 2>&1 | grep -cE "Traceback|NameError|Internal Server Error"   # 0
curl -s -o /dev/null -w "%{http_code}\n" https://ernestoavedillo.com/static/menuapp/images/specs.svg   # 200
```

Open the home page and check the four tool cards, then the language switch (Spanish/English).

## 5. Make sign-up work (email) or provide a demo account

Sign-up needs a verification code by email. Test the SMTP login from the server (prints no secrets):

```bash
docker exec django python -W ignore -c "
import os, smtplib
h, u, p, port = os.environ['SMTP_HOST'], os.environ['NO_REPLY_EMAIL'], os.environ['NO_REPLY_PASSWORD'], int(os.environ['SMTP_PORT'])
s = smtplib.SMTP_SSL(h, port, timeout=20) if port == 465 else smtplib.SMTP(h, port, timeout=20)
if port != 465: s.starttls()
print('login:', s.login(u, p)); s.quit()"
```

**Use port 587.** On the production host outbound port 465 is blocked (the connection times out, and the
traceback shows `OSError: [Errno 101] Network is unreachable` because Python reports the first, IPv6, error).
Port 587 (STARTTLS) connects. Check with:
`docker exec django python -c "import socket; socket.create_connection(('smtp.gmail.com', 587), 8).close(); print('587 OK')"`.
After changing `SMTP_PORT` in `.env_prod`, run `cp .env_prod .env` and `docker compose up -d --force-recreate django`
(a plain restart does not re-read the environment file).

Known issue: from the development machine Gmail closed the connection during login (no error code) with the
configured app password, so credentials are **unconfirmed**. If login fails from the server over 587, regenerate the
Gmail app password (the sender is a no-reply Gmail account), and meanwhile give the judges a ready-made account:

```bash
docker exec -w /app/src django python manage.py shell -c \
  "from django.contrib.auth.models import User; User.objects.create_user('demo', 'demo@example.com', 'CHOOSE_A_PASSWORD')"
```

Put the demo credentials in the Devpost description.

## 6. Demo content: only documents you may publish

The public demo must **not** contain OEM standards (VW, BMW, ...): they are usually confidential or licensed.
Use documents you have the right to publish (your own, public domain or openly licensed). Log in as the demo
user, upload them at *Specifications > Upload New PDF*, wait about a minute, then confirm each document's
metadata. Specs never shares documents between users, so each account only sees what it uploaded.

## 7. Backups

```bash
make backup                       # writes backups/<timestamp>/ (Postgres, MongoDB, Qdrant); keeps the newest 14
make restore DIR=backups/<timestamp>   # asks for a typed confirmation, REPLACES current data
```

Backups are git-ignored and stay on the same disk: copy them off the server (`scp`/`rsync`) after each important
change. `scripts/backup.sh` needs `python3` on the host.

## 8. TLS certificate: renew before it expires

The certificate served at the time of writing was issued 2026-08-12 and **expires 2026-11-10**. The hackathon
judging window (reported by third-party listings as 2026-12-01 to 12-15) is after that, so it **must be renewed**.
Check: `echo | openssl s_client -connect ernestoavedillo.com:443 -servername ernestoavedillo.com 2>/dev/null | openssl x509 -noout -enddate`

Warning: the `setup-letsencrypt` target in the `Makefile` passes `--staging` to certbot. Staging certificates are
**not trusted by browsers**. Remove that flag (and the `rm-letsencrypt` side effects must be understood) before
running `make renew-certificates`, or the site will show a certificate warning to the judges.

## 9. Rollback

Code: `git checkout <previous-commit>` then `make build`. Data: `make restore DIR=backups/<timestamp>`.
Take a `make backup` before every update once there is real data.

## 10. Working conventions for the project

- Code, identifiers and comments are in English. Every user-facing message must exist in Spanish and English:
  Spanish `msgid` in `_()` / `{% trans %}`, plus an entry in both `src/locale/{es,en}/LC_MESSAGES/django.po`,
  then `make compilemessages` (inside the container) and restart `django`.
- After editing several files, restart the dev server (`docker compose restart django`): its auto-reloader can
  keep a half-edited version of a module.
- Tests (they use a separate test database, so they are safe to run anywhere):
  `docker exec -w /app/src django python manage.py test specs`
- Project documents: [README.md](README.md) (what it is, how to run), [DEVPOST.md](DEVPOST.md) (hackathon
  submission text), this file (deployment).
- Hackathon: Nebius x NVIDIA Global AI Hackathon on Devpost, deadline **2026-10-30 10:00 PDT (18:00 in Spain)**.
  The demo video is done (https://youtu.be/cFhAQLos_HY). Still to do at the time of writing: public demo URL,
  product feedback on the Nebius/NVIDIA tools, and the submission form.
