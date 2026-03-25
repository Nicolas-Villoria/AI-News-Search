# Supabase setup (step by step)

Use this once. After that, copy the same `DATABASE_URL` into GitHub **Actions** secret `DATABASE_URL` for the scheduled pipeline.

## 1. Create a project

1. Go to [supabase.com](https://supabase.com) and sign in.
2. **New project** → pick org, name, database password (save it), region close to you.
3. Wait until the project finishes provisioning.

## 2. Enable the `vector` extension (pgvector)

1. Open your project in the dashboard.
2. In the **left sidebar**, click the **Database** icon (cylinder / stack icon — *not* the gear at the bottom).
3. Open the **Extensions** tab (or sub-item, depending on UI version).
4. Search for **vector** and enable it.

(The app also runs `CREATE EXTENSION IF NOT EXISTS vector` on startup/pipeline; enabling it here avoids surprises if permissions differ.)

## 3. Get the connection string

Supabase hides the URI in a **Connect** panel.

### Use **Session pooler** for local dev and GitHub Actions (recommended)

The **Direct** host (`db.<ref>.supabase.co`) is often **IPv6-only**. Many home Wi‑Fi networks and Macs cannot resolve or reach it, which produces:

`could not translate host name ... nodename nor servname provided, or not known`

**Fix:** In the **Connect** modal, choose **Session pooler** (not “Transaction” / not port **6543**). The host looks like `aws-0-<region>.pooler.supabase.com`, port **5432**. The username is often `postgres.<project-ref>` — copy the URI exactly as Supabase shows it.

Use **Session pooler** for:

- your Mac (`uvicorn`, pipeline),
- GitHub Actions (`DATABASE_URL` secret).

It supports IPv4 and works with normal SQLAlchemy sessions and `init_db()`.

### Direct connection (optional)

Only if you know your network has working **IPv6**. Host: `db.<ref>.supabase.co`, port **5432**.

### Where to click

1. Open your **project** overview.
2. **Connect** (top of the page).
3. Pick the connection type as above and copy the **URI**.

### If you do not see **Connect**

**Project Settings** (gear, bottom of sidebar) → **Database** → connection strings.

### Finish the URI

1. Replace the password placeholder with your real database password.
2. Append `?sslmode=require` if SSL is not already in the string.

Example shapes (yours will differ):

```text
# Session pooler (IPv4-friendly) — prefer this
postgresql://postgres.<PROJECT_REF>:<PASSWORD>@aws-0-<REGION>.pooler.supabase.com:5432/postgres?sslmode=require

# Direct (IPv6-only in practice — skip on most home networks)
postgresql://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres?sslmode=require
```

## 4. Point the app at Supabase locally

1. Put a `.env` file at the **repository root** (same folder as `README.md`) or under **`backend/`**.
2. Add one line (no quotes needed unless the URL contains special characters):

   `DATABASE_URL=<your URI from step 3>`

3. The app **loads `.env` automatically** when `config.settings` is imported (`python-dotenv`). You do **not** need `export $(cat .env)` unless you prefer the shell to set variables.

4. Start the API from `backend/` as usual:

   ```bash
   cd backend
   python3 -m uvicorn api.main:app --port 8000
   ```

5. On startup you should see log lines like:
   - `Initializing database at aws-0-....pooler.supabase.com:5432/postgres` (or your host)
   - `pgvector extension enabled`
   - `All tables created successfully (SQLAlchemy create_all)`
   - `Row Level Security enabled on app tables (Data API not public)`

   If the host shows `localhost`, `DATABASE_URL` was not picked up — check `.env` path and that `pip install python-dotenv` ran.

6. There is **no Alembic migration folder** in this project: schema is applied with **SQLAlchemy `create_all`** on startup (and in the pipeline). Check tables in Supabase: **Table Editor** → `public` → `articles`, `entities`, etc.

### Row Level Security (RLS) banner in Table Editor

If Supabase says a table **“can be accessed by anyone via the Data API as RLS is disabled”**, that refers to the **auto-generated REST API** when using the **anon** key in a browser or mobile app — not your FastAPI server.

This repo turns **RLS on** for `articles`, `entities`, `topic_clusters`, and `pipeline_runs` during `init_db()`. With RLS enabled and **no policies** for `anon` / `authenticated`, those roles cannot read rows through the Data API. Your backend uses the **database password** (`DATABASE_URL`) as the `postgres` role, which **bypasses RLS**, so search and the pipeline keep working.

Restart the API once so `init_db()` runs again, or run in **SQL Editor**:

```sql
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE topic_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
```

If you later call these tables from the **Supabase JS client** with a logged-in user, you must add explicit **policies**; until then, use only your API + `DATABASE_URL`.

## 5. GitHub Actions

1. Repo → **Settings** → **Secrets and variables** → **Actions**.
2. **New repository secret** → name: `DATABASE_URL`, value: same URI as above.
3. **Actions** → workflow **Run Pipeline** → **Run workflow** to test once.
4. Cron will run on the schedule defined in `.github/workflows/pipeline.yml`.

## Troubleshooting

| Symptom | Likely fix |
|--------|------------|
| `could not translate host name` / `nodename nor servname` for `db.*.supabase.co` | Direct host is IPv6-only on many projects. Switch `DATABASE_URL` to **Session pooler** (Connect → Session pooler, port 5432). |
| SSL / connection refused | Add `?sslmode=require` to the URI. |
| Errors with **Transaction** pooler (port **6543**) | Use **Session** pooler on **5432** instead for this app, or disable prepared statements if you must use transaction mode. |
| `extension "vector" does not exist` | Enable **vector** under Database → Extensions. |
| “RLS is disabled” / anyone via Data API | Restart the API so `init_db()` enables RLS, or run the `ALTER TABLE … ENABLE ROW LEVEL SECURITY` block above. |
