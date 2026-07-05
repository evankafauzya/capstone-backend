// ---------------------------------------------------------------------------
// Capacity test for the Moodle Proctoring AI backend — /detect/faces.
//
// Simulates ~250 students hitting the backend at once (e.g. an exam start
// burst) and reports real per-request latency, throughput, and error rates.
//
// PREREQUISITES
//   1. Real model files present in models_data/ (otherwise you measure the
//      stub, not inference). Do NOT set MOCK_MODELS for a latency test.
//   2. Rate limit raised so requests reach the app instead of being 429'd:
//        set RATE_LIMIT=1000000/minute in .env, then
//        docker compose up -d --build
//   3. Wait for readiness (models loaded): curl http://localhost:5000/health -> 200
//   4. Build the payload:
//        python stress/build_payload.py path/to/face.jpg
//
// RUN
//   API_KEY=<your-key> k6 run stress/stress.js
//   # tune the load:
//   API_KEY=<key> VUS=250 DURATION=3m k6 run stress/stress.js
//   # realistic polling instead of a flat-out burst (think-time seconds):
//   API_KEY=<key> SLEEP=45 k6 run stress/stress.js
// ---------------------------------------------------------------------------
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:5000';
const API_KEY = __ENV.API_KEY || '';
const VUS = parseInt(__ENV.VUS || '250', 10);       // peak concurrent "students"
const DURATION = __ENV.DURATION || '3m';            // hold time at peak
const THINK = parseFloat(__ENV.SLEEP || '0');       // seconds between a VU's calls

// {"image": "<base64>"} produced by build_payload.py
const payload = open('./payload.json');

// Custom metrics: count rate-limit rejections and track the app's own timing.
const rateLimited = new Counter('rate_limited_429');
const serverErrors = new Counter('server_errors_5xx');
const appProcessTime = new Trend('app_process_time_ms', true);

export const options = {
  scenarios: {
    exam_burst: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '30s', target: VUS },   // ramp up to peak
        { duration: DURATION, target: VUS }, // hold at peak
        { duration: '30s', target: 0 },      // ramp down
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<2000', 'p(99)<5000'], // p95 under 2s is the goal
    http_req_failed: ['rate<0.01'],                  // <1% failures
    rate_limited_429: ['count==0'],                  // any 429 => raise RATE_LIMIT
  },
};

export default function () {
  const res = http.post(`${BASE_URL}/detect/faces`, payload, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${API_KEY}`,
    },
    tags: { endpoint: 'detect_faces' },
  });

  if (res.status === 429) rateLimited.add(1);
  if (res.status >= 500) serverErrors.add(1);

  // The app stamps X-Process-Time (seconds spent inside the app) on every
  // response. Tracking it separately from http_req_duration lets you tell
  // "the app is slow" apart from "requests are queued waiting for a worker".
  const xpt = res.headers['X-Process-Time'];
  if (xpt) appProcessTime.add(parseFloat(xpt) * 1000);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'not rate-limited (429)': (r) => r.status !== 429,
    'no server error (5xx)': (r) => r.status < 500,
  });

  if (THINK > 0) sleep(THINK);
}
