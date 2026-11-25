# Deploy steps (Render backend + Vercel frontend)

Backend = repo root (`app/`, `requirements.txt`, `render.yaml`). Frontend = `CardKholo/`.
Values come from your local `.env` / `CardKholo/.env.local`. Never paste them anywhere else.

## Order
1. Push the repo to GitHub.
2. Deploy the backend on Render, note its URL, set `APP_BASE_URL` to it.
3. Deploy the frontend on Vercel with `VITE_API_BASE_URL` = the Render URL.
4. Set `ALLOWED_ORIGINS` on Render to the exact Vercel URL, then redeploy the backend.
5. Register the Flagsmith webhook, run the checks, set up keep-warm.

## 1. Render (backend)
1. dashboard.render.com > **New** > **Blueprint** > connect GitHub > pick this repo > **Apply**.
   (Manual alternative: New > Web Service, runtime Python 3, build `pip install -r requirements.txt`,
   start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check path `/health`, plan Free.)
2. Open the service > **Environment** and fill every variable from your `.env`:
   `SARVAM_API_KEY`, `FLAGSMITH_ENV_KEY`, `FLAGSMITH_ADMIN_API_KEY`, `FLAGSMITH_ADMIN_ENV_KEY`,
   `FLAGSMITH_PROJECT_ID`, `FLAGSMITH_FEATURE_IDS`, `FLAGSMITH_SEGMENT_IDS`, `TELEGRAM_BOT_TOKEN`,
   `TELEGRAM_BOT_USERNAME`, `TELEGRAM_SECRET`, `NUDGEBEE_WEBHOOK_URL`, `HOOK_SECRET`, `DEMO_CACHE=on`.
3. `APP_BASE_URL` = `https://<service>.onrender.com` (no trailing slash). `ALLOWED_ORIGINS` = `*` for now.
4. **Save, rebuild and deploy**. Wait for "Live", then open `https://<service>.onrender.com/health` → `{"ok":true}`.
   On startup the app registers the Telegram webhook itself (needs https `APP_BASE_URL`).

## 2. Vercel (frontend)
1. vercel.com > **Add New** > **Project** > import the repo > **Root Directory** `CardKholo` > framework Vite
   (build `npm run build`, output `dist`).
2. Environment variables: `VITE_API_BASE_URL=https://<service>.onrender.com`, `VITE_USE_MOCKS=false`,
   `VITE_TELEGRAM_BOT_USERNAME=<bot username without @>`. **Deploy**.
3. Any later change to a `VITE_` variable needs **Deployments > Redeploy**.

## 3. Close the loop
1. Render > Environment: `ALLOWED_ORIGINS=https://<project>.vercel.app` (exact, no slash) > save and redeploy.
2. Flagsmith > project > environment **Development** > **Settings** > **Webhooks** > **Create webhook**:
   URL `https://<service>.onrender.com/hooks/flagsmith?token=<HOOK_SECRET>` (your HOOK_SECRET from `.env`), enabled.
3. Locally: `.\.venv\Scripts\python scripts\check_integrations.py --base-url https://<service>.onrender.com`
   then the same with `--nudgebee` and **reject** the "check-test" run in NudgeBee.
4. cron-job.org > **Create cronjob**: URL `https://<service>.onrender.com/health`, every 10 minutes, method GET.

## Notes
- Render free sleeps after 15 min idle and can lose the SQLite file on restart (pairings, incidents, feed).
  Keep-warm avoids most of it; re-link the Telegram phone after a redeploy.
- NudgeBee's callback header `X-Hook-Secret` must equal `HOOK_SECRET` on Render.
