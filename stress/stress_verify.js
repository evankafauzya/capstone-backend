// ---------------------------------------------------------------------------
// Capacity test for the FULL recognition path — POST /verify/face.
//
// Unlike stress.js (which tests /detect/faces), this exercises detect + align
// + ArcFace embedding + SQLite lookup + cosine similarity, i.e. the real
// proctoring verification pipeline. It is heavier per request than detection.
//
// PREREQUISITES
//   1. Real model files present in models_data/.
//   2. Rate limit raised (RATE_LIMIT=1000000/minute in .env) + rebuild.
//   3. Build payloads + enroll the load-test user ONCE:
//        python stress/build_verify_payload.py path/to/face.jpg --user-id loadtest_user
//        curl -X POST http://localhost:5000/enroll/face \
//          -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
//          -d @stress/enroll_payload.json
//
// RUN
//   API_KEY=<key> VUS=250 DURATION=1m SLEEP=45 k6 run stress/stress_verify.js   # realistic
//   API_KEY=<key> VUS=250 DURATION=1m k6 run stress/stress_verify.js            # burst / ceiling
// ---------------------------------------------------------------------------
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:5000';
const API_KEY = __ENV.API_KEY || '';
const VUS = parseInt(__ENV.VUS || '250', 10);
const DURATION = __ENV.DURATION || '1m';
const THINK = parseFloat(__ENV.SLEEP || '0');

// {"current_face": "<base64>", "user_id": "..."} from build_verify_payload.py
const payload = open('./verify_payload.json');

const rateLimited = new Counter('rate_limited_429');
const serverErrors = new Counter('server_errors_5xx');
const notMatched = new Counter('verify_not_matched');
const appProcessTime = new Trend('app_process_time_ms', true);

export const options = {
  scenarios: {
    verify_load: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '30s', target: VUS },
        { duration: DURATION, target: VUS },
        { duration: '30s', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<2000', 'p(99)<5000'],
    http_req_failed: ['rate<0.01'],
    rate_limited_429: ['count==0'],
  },
};

export default function () {
  const res = http.post(`${BASE_URL}/verify/face`, payload, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${API_KEY}`,
    },
    tags: { endpoint: 'verify_face' },
  });

  if (res.status === 429) rateLimited.add(1);
  if (res.status >= 500) serverErrors.add(1);

  const xpt = res.headers['X-Process-Time'];
  if (xpt) appProcessTime.add(parseFloat(xpt) * 1000);

  // Sanity: a correct 200 should report is_match=true for the enrolled user.
  let matched = false;
  try { matched = res.status === 200 && JSON.parse(res.body).is_match === true; } catch (e) { /* ignore */ }
  if (res.status === 200 && !matched) notMatched.add(1);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'not rate-limited (429)': (r) => r.status !== 429,
    'no server error (5xx)': (r) => r.status < 500,
    'identity matched': () => matched,
  });

  if (THINK > 0) sleep(THINK);
}
