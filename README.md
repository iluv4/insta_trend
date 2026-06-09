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

```bash
docker build -t insta-trend-monitor .
docker run -p 8000:8000 --env-file .env insta-trend-monitor
```

For production set `DATABASE_URL` to PostgreSQL (e.g. `postgresql+psycopg://…`).
