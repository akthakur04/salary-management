# Deployment

Production runs in two places:

```
Browser ──▶ Vercel: Next.js ──(/api/* rewrite)──▶ Render: FastAPI (Docker) ──▶ Render Postgres
```

The browser only talks to Vercel. Next.js forwards `/api/*` to the API, so the session cookie stays first-party and the API needs no CORS (see [ARCHITECTURE.md §9](ARCHITECTURE.md#9-deployment)).

| Piece | Where it's defined |
|---|---|
| API image | [backend/Dockerfile](../backend/Dockerfile). On start it runs `alembic upgrade head`, then uvicorn on `$PORT` ([start.sh](../backend/scripts/start.sh)) |
| API service and database | [render.yaml](../render.yaml), a Render Blueprint |
| Web app | [frontend/vercel.json](../frontend/vercel.json). Vercel builds it with `next build` |
| Everything locally, on Postgres | [docker-compose.yml](../docker-compose.yml) (see [Run it with Docker](#run-it-with-docker)) |

No secret is stored in the repository. Real values live only in Render's and Vercel's settings.

---

## What to set

### Render (API and database)

1. Merge `dev` into `main` first: the Blueprint deploys from `main`.
2. In the Render dashboard choose **New → Blueprint**, connect the GitHub repository, and pick `render.yaml`. It creates:
   - **salary-db**: Postgres. Its connection string is passed to the API as `DATABASE_URL` automatically.
   - **salary-api**: the API, built from `backend/Dockerfile`, health-checked at `/api/v1/health`.
3. Render asks for two values. Generate them on your machine, from `backend/` with the virtual environment active:

   ```bash
   python -m app.core.hash_password
   ```

   | Variable | Value |
   |---|---|
   | `HR_ADMIN_EMAIL` | The email the HR Manager signs in with |
   | `HR_ADMIN_PASSWORD_HASH` | The `HR_ADMIN_PASSWORD_HASH=` value the command printed (starts with `$2b$`) |

   Render generates `SESSION_SECRET` itself, and the Blueprint sets `APP_ENV=production` and `COOKIE_SECURE=true`. Leave those as they are.
4. Apply the Blueprint and wait for the first deploy. Then open `https://<your-api>.onrender.com/api/v1/health`, which should return `{"status":"ok","database":"ok"}`.

### Load the demo data (once)

The free plan has no shell or one-off jobs, so run the seed from your machine against the database's external address:

1. In Render, open **salary-db → Connect → External Database URL** and copy it.
2. From `backend/`, with the virtual environment active:

   ```bash
   DATABASE_URL='<external database URL>' python -m app.seed
   ```

   It loads 10,000 employees in one transaction. Running it again changes nothing unless you pass `--reset`, which clears the data and loads it again.

On a paid plan you can run `python -m app.seed` from the service's **Shell** tab instead.

### Vercel (web app)

1. In Vercel choose **Add New → Project** and import the repository.
2. Set **Root Directory** to `frontend`. Vercel detects Next.js; leave the build settings as they are.
3. Add one environment variable, for Production (and Preview if you use previews):

   | Variable | Value |
   |---|---|
   | `API_ORIGIN` | The API's Render address, e.g. `https://salary-api.onrender.com`, with no trailing slash |

4. Deploy, open the Vercel address, and sign in with the HR email and password.

`API_ORIGIN` is read when the app is built, so if it changes, redeploy the web app.

---

## Free plan limits

- **The API sleeps** after about 15 minutes without traffic, and the first request afterwards takes up to a minute. Before a demo, open the health URL to wake it.
- **The free Postgres database expires** after 30 days. Upgrade it, or recreate it and seed again.
- The Blueprint uses Render's `virginia` region and Vercel's `iad1` (US East), so the hop from Vercel to the API stays short. To move, change both.

## Releasing

Pushing to `main` redeploys both: Render rebuilds the API when anything under `backend/` changes and applies new migrations on start-up, and Vercel rebuilds the web app. Migrations run before the new version takes traffic, so keep each one backward compatible with the running code.

---

## Run it with Docker

To run the whole app on Postgres, as in production, without installing Python or Node:

1. Create `backend/.env` with the HR login, as in [SETUP_GUIDE.md §4](SETUP_GUIDE.md#4-backend-configure-the-login). Its `DATABASE_URL` is ignored; Compose points the API at its own Postgres.
2. From the repository root:

   ```bash
   docker compose up --build
   ```

3. In another terminal, load the demo data once:

   ```bash
   docker compose run --rm api python -m app.seed
   ```

4. Open http://localhost:3000 and sign in.

The database lives in the `db-data` volume and survives restarts. `docker compose down -v` deletes it.
