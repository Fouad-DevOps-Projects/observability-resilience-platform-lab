import http from 'k6/http';
import { check, sleep } from 'k6';

// Small, deterministic CI gate. Run only against a disposable/local lab.
const base = (__ENV.TARGET_URL || 'http://gateway:8000').replace(/\/$/, '');
export const options = {
  vus: 2,
  duration: '15s',
  thresholds: {
    http_req_failed: ['rate<0.005'],
    http_req_duration: ['p(95)<500'],
    checks: ['rate>0.99'],
  },
};

export default function () {
  const response = http.get(`${base}/checkout`, {
    tags: { endpoint: 'checkout', scenario: 'smoke' },
    timeout: '5s',
  });
  check(response, {
    'checkout returns HTTP 200': (r) => r.status === 200,
    'checkout contains success payload': (r) =>
      r.status === 200 && r.body.includes('"checkout":"ok"'),
  });
  sleep(0.2);
}
