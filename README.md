# LearnWithGlinax

Curated STEM courses and structured Combo learning paths from the world's best free providers — in one place. Students browse courses (YouTube, MIT OCW, OpenStax, freeCodeCamp), follow multi-course Combo paths, track progress, and save content.

Django 6 + DRF (JWT auth) · Next.js frontend · PostgreSQL · Brevo transactional email · deployed on Render.

---

## Repository layout

```
├── apps/            Django apps (users, courses, combos, progress, notifications, analytics, ingestion)
├── common/          Shared backend utilities (incl. Brevo email backend, non-blocking task dispatch)
├── core/            Django project (settings in core/settings/{base,development,production}.py)
├── Output/          Next.js frontend (deployed with rootDir=Output)
├── requirements/    Django requirements (base/development/production)
├── render.yaml      Render blueprint — creates api + frontend + redis + postgres
└── .env.example     All backend env vars (required ones marked)
```

## Run locally

Backend (Python 3.12+, from repo root):

```bash
python -m venv .venv && .venv/Scripts/activate        # or source .venv/bin/activate
pip install -r requirements/development.txt
cp .env.example .env                                   # fill in DB_* (local Postgres) + DJANGO_SECRET_KEY
python manage.py migrate
python manage.py runserver                             # http://localhost:8000
```

Frontend (from `Output/`):

```bash
npm ci
cp .env.example .env.local                             # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
npm run dev                                            # http://localhost:3000
```

## Deploy to Render (fresh account/project)

1. Push this repo to your GitHub, then in Render: **New → Blueprint** and select the repo.
   `render.yaml` creates the web services, Redis and Postgres, and prompts you for the
   environment values — every `sync: false` entry is one prompt. See `.env.example`
   (backend, repo root) and `Output/.env.example` (frontend) for what each value means.
2. **Run migrations once** after the first deploy (Render free tier has no release task):

   ```bash
   # from your machine, against the new database's EXTERNAL URL:
   DB_HOST=<external-host>.render.com DB_PORT=5432 DB_NAME=... DB_USER=... DB_PASSWORD=... \
   PGSSLMODE=require python manage.py migrate --settings=core.settings.production
   ```

3. **Seed course content** (optional, ~190 courses): run the ingestion once from a local
   shell with the production DB env vars, per source: `youtube`, `mit_ocw`, `openstax`,
   `freecodecamp` (see `apps/ingestion/pipeline.py::run_pipeline`).
4. **Google sign-in**: in Google Cloud Console → Credentials → your OAuth client, add both
   `http://localhost:3000` and `https://your-frontend.onrender.com` as *Authorized JavaScript
   origins*. Use the same client ID in Render for both `GOOGLE_CLIENT_ID` (backend) and
   `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (frontend).
5. **Email**: Brevo account → SMTP & API → API Keys → generate a v3 API key with
   **Authorized IPs left empty**, then set `BREVO_API_KEY` and
   `DEFAULT_FROM_EMAIL=Your Name <verified-sender@example.com>` on the Render service.
6. **Verify**: register an account on the frontend → you should land on the dashboard and
   receive the welcome email within a minute.

## Production notes

- `core/settings/production.py` runs background tasks (welcome email, analytics) in
  daemon threads — no Celery worker is needed. `BREVO_API_KEY` switches email from SMTP
  to Brevo's HTTP API automatically (Render blocks raw SMTP).
- Free-tier instances sleep after ~15 min idle; the first request after idle takes
  ~30–60 s. The frontend HTTP client tolerates this (45 s timeout).
- `DJANGO_SECRET_KEY` must be 50+ random characters.
- Set `FRONTEND_URL` or the links inside the welcome email will point at localhost.
