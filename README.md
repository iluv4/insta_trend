# 📈 Instagram Reference Monitor

> 인스타그램 **레퍼런스 계정을 시계열로 추적·분석**하는 모니터링 서비스.
> 팔로워·게시물·인게이지먼트 지표를 주기적으로 스냅샷하고, 추세/모멘텀/이상치/예측을 계산해 대시보드로 보여줍니다.

| | |
| :-- | :-- |
| Stack | FastAPI · SQLAlchemy · APScheduler · pandas/NumPy · Chart.js |
| Data source | Instagram (RapidAPI `instagram120`) |
| Storage | SQLite (default) / PostgreSQL |
| Focus | **시계열 데이터 분석** (smoothing · growth · momentum · anomaly · forecast) |

---

## What it does

1. **Track** any number of Instagram accounts ("references" — competitors, inspiration, your own brand).
2. **Collect** a timestamped metric snapshot per account on a schedule (or on demand).
   Captured metrics: `followers`, `following`, `posts_count`, `avg_likes`, `avg_comments`, `engagement_rate`.
3. **Analyse** each metric as a time series and surface:
   - **Smoothing** — simple & exponential moving averages
   - **Growth** — absolute / %, average daily growth, daily CAGR
   - **Momentum** — rate-of-change vs N periods ago (is it heating up?)
   - **Anomalies** — trailing rolling z-score detection of spikes / drops (e.g. a viral post)
   - **Forecast** — Holt's linear (double exponential smoothing), implemented in NumPy
   - **Trend label** — rising / falling / flat from a least-squares slope
4. **Visualise** everything in a single-page dashboard (`/`).

The analytics core lives in [`app/timeseries.py`](app/timeseries.py) and is completely
decoupled from the web/DB layers, so it's deterministic and unit-tested.

---

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env            # add RAPIDAPI_KEY for live data (optional)

# Option A — explore immediately with synthetic data (no API key needed)
python -m scripts.seed_demo

# Run
uvicorn app.main:app --reload   # → http://localhost:8000
```

Open <http://localhost:8000>, pick an account, and explore the charts.

### With live Instagram data

1. Subscribe to the [instagram120 API on RapidAPI](https://rapidapi.com/) and set `RAPIDAPI_KEY` in `.env`.
2. Add an account in the UI (or `POST /api/accounts`).
3. Click **Collect now**, or let the background scheduler snapshot every
   `COLLECT_INTERVAL_MINUTES` (default 6h). Time-series analysis becomes
   meaningful once a few snapshots have accumulated.

---

## API

| Method | Path | Description |
| :-- | :-- | :-- |
| `GET` | `/api/health` | Liveness probe |
| `GET` | `/api/accounts` | List tracked accounts |
| `POST` | `/api/accounts` | Add an account `{username, label?}` |
| `DELETE` | `/api/accounts/{id}` | Stop tracking (cascades snapshots) |
| `GET` | `/api/accounts/{id}/snapshots` | Raw time-series rows |
| `POST` | `/api/accounts/{id}/collect` | Collect a snapshot now (live API) |
| `GET` | `/api/analytics/metrics` | Analysable metric names |
| `GET` | `/api/analytics/{id}?metric=&freq=&horizon=` | Full time-series analysis |

Interactive docs at `/docs`.

Example:

```bash
curl "localhost:8000/api/analytics/1?metric=followers&freq=1D&horizon=7"
```

```jsonc
{
  "metric": "followers",
  "trend": "rising",
  "growth": { "current": 16500, "percent_change": 65.0, "avg_daily_growth": 500, "cagr_daily_pct": 2.6 },
  "latest_momentum_pct": 3.4,
  "anomalies": [{ "timestamp": "...", "value": 30000, "zscore": 4.1, "direction": "spike" }],
  "forecast": { "method": "holt_linear", "values": [...], "timestamps": [...] },
  "series": [...], "moving_average": [...], "ema": [...], "momentum": [...]
}
```

---

## Architecture

```
RapidAPI ──> instagram.py ──> collector.py ──> MetricSnapshot (DB)
                                                      │
scheduler.py (APScheduler, every N min) ─────────────┘
                                                      │
                                            analytics.py  ──reads series──┐
                                                      │                   │
                                              timeseries.py  ◄────────────┘  (pure pandas/NumPy)
                                                      │
                                       FastAPI routers ──> /static dashboard (Chart.js)
```

- **`app/timeseries.py`** — analytics engine (no I/O). Entry point: `analyze(points, ...)`.
- **`app/analytics.py`** — loads snapshots from the DB and feeds the engine.
- **`app/collector.py`** — fetch → persist a snapshot; `fetch_fn` is injectable for tests.
- **`app/scheduler.py`** — periodic background collection.

---

## Tests

```bash
pytest
```

Covers the time-series math deterministically (`tests/test_timeseries.py`) and the
API + collection flow with a fake Instagram source (`tests/test_api.py`) — no
network access required.

---

## Deployment

The app is a standard FastAPI + Docker service — **no Node.js or build step**
(the dashboard is a single static page using Chart.js from a CDN). It listens
on `$PORT` if the host sets one, otherwise `8000`.

### Docker (any host)

```bash
docker build -t insta-trend-monitor .
docker run -p 8000:8000 --env-file .env insta-trend-monitor
# → http://localhost:8000
```

### Render (one click, free tier)

A [`render.yaml`](render.yaml) Blueprint is included, so deployment is:

1. Push this repo to GitHub.
2. In Render, **New + → Blueprint**, and select the repo.
3. Render builds the Dockerfile, provisions a free Postgres database, and wires
   `DATABASE_URL` automatically. Add your `RAPIDAPI_KEY` in the dashboard for
   live collection (optional — the app runs on seeded/demo data without it).
4. Open the generated `*.onrender.com` URL.

The `/api/health` endpoint is configured as the health check.

### Other hosts (Fly.io, Railway, Cloud Run, …)

Any platform that runs a Dockerfile works the same way — point it at this repo,
set the env vars from [`.env.example`](.env.example), and expose the port. These
hosts inject `$PORT`, which the container already honours.

### Production notes

- **Database:** SQLite (the default) lives on the container's ephemeral disk and
  is wiped on every redeploy. For anything persistent set `DATABASE_URL` to
  Postgres — e.g. `postgresql://user:pass@host:5432/db`. The app rewrites
  `postgres://` / `postgresql://` URLs to the bundled psycopg 3 driver
  automatically, so the connection string from most managed Postgres providers
  works as-is.
- **Scheduler:** `ENABLE_SCHEDULER=true` runs in-process background collection
  every `COLLECT_INTERVAL_MINUTES`. On multi-instance deployments, run the
  scheduler on a single worker (or set it to `false` and trigger collection out
  of band) to avoid duplicate snapshots.
- **Live data:** without `RAPIDAPI_KEY`, `POST /collect` returns 502; seed
  synthetic data with `python -m scripts.seed_demo` to explore the dashboard.
- **No shell access?** (e.g. Render free tier) Set `SEED_DEMO_ON_STARTUP=true`
  and the app seeds the same synthetic demo data on boot whenever the DB is
  empty — no shell needed. Already-populated databases are left untouched.
