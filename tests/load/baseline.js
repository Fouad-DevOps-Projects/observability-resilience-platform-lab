import http from 'k6/http';
import { check } from 'k6';

// Controlled capacity check; NOT a production load-testing configuration.
// Explicit user opt-in is required via RUN_LOAD_TEST=yes.
const base = (__ENV.TARGET_URL || 'http://gateway:8000').replace(/\/$/, '');
if (__ENV.RUN_LOAD_TEST !== 'yes') {
  throw new Error('Set RUN_LOAD_TEST=yes only for an authorized disposable lab');
}
export const options = {
  scenarios: {
    checkout_baseline: {
      executor: 'constant-arrival-rate',
      rate: 3,
      timeUnit: '1s',
      duration: '60s',
      preAllocatedVUs: 5,
      maxVUs: 10,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.005'],
    http_req_duration: ['p(95)<500'],
    checks: ['rate>0.99'],
    dropped_iterations: ['count==0'],
  },
};

export default function () {
  const response = http.get(`${base}/checkout`, {
    tags: { endpoint: 'checkout', scenario: 'baseline' },
    timeout: '5s',
  });
  check(response, {
    'checkout status 200': (r) => r.status === 200,
    'checkout JSON succeeded': (r) =>
      r.status === 200 && r.body.includes('"checkout":"ok"'),
  });
}
