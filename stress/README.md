# Capacity / load test

Answers one question: **how many students can one container serve before latency degrades?**

Targets `POST /detect/faces` with a real base64 image, ramping to a configurable
number of concurrent "students" (default 250).

## 1. Prerequisites

- [k6](https://k6.io/docs/get-started/installation/) installed on the host.
- **Real model files** in `models_data/` — do *not* set `MOCK_MODELS`, or you
  measure the stub instead of real inference.
- A sample face image to send.

## 2. Raise the rate limit (test only)

The app caps each API token/IP at `600/minute` (~10 req/s) and returns `429`
past that. A load test would otherwise measure the rate limiter, not the app.
Temporarily raise it in `.env`:

```
RATE_LIMIT=1000000/minute
```

then rebuild and wait for readiness:

```bash
docker compose up -d --build
until curl -sf http://localhost:5000/health >/dev/null; do sleep 2; done
```

**Revert `RATE_LIMIT` to `600/minute` before deploying for real.**

## 3. Build the payload

```bash
python stress/build_payload.py path/to/face.jpg
```

Writes `stress/payload.json` = `{"image": "<base64>"}`.

## 4. Run

```bash
# default: burst to 250 concurrent, hold 3 min
API_KEY=<your-key> k6 run stress/stress.js

# tune load
API_KEY=<key> VUS=200 DURATION=2m k6 run stress/stress.js

# realistic polling (45 s think-time between each student's calls) instead of
# a flat-out burst
API_KEY=<key> SLEEP=45 k6 run stress/stress.js
```

While it runs, watch the container: `docker stats` and `docker compose logs -f app`.

## 5. Reading the results

| Metric | Meaning / what to watch |
| --- | --- |
| `rate_limited_429` | Must be **0**. Non-zero → `RATE_LIMIT` not raised enough; results invalid. |
| `http_req_duration` p95/p99 | End-to-end latency incl. time queued for the single worker. |
| `app_process_time_ms` | Time *inside* the app (from `X-Process-Time`). If this is low but `http_req_duration` is high → requests are queuing → worker saturated. |
| `http_req_failed` | Timeouts / errors. |
| `server_errors_5xx` | Model crash / OOM — check `docker compose logs`. |
| `docker stats` CPU | Pegged ~one core → single-worker/GIL bound. Fix = more workers (more RAM) or a GPU. |
| `docker stats` MEM | Should stay flat; creeping up across the run = possible leak. |

**Verdict:** if p95 stays acceptable at your real peak concurrency, one container
is enough. If not, that's your concrete signal to scale workers or move to GPU
*before* exam day.
