import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 3,
  duration: '30s',
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<1000'],
  },
};

const base = __ENV.TARGET_URL || 'http://gateway:8000';

export default function () {
  const res = http.get(`${base}/checkout`);
  check(res, { 'checkout succeeded': (r) => r.status === 200 });
  sleep(0.3);
}
