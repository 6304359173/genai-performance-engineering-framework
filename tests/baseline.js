
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    baseline: {
      executor: 'constant-arrival-rate',
      rate: 10,
      timeUnit: '1s',
      duration: '30s',
      preAllocatedVUs: 2,
      maxVUs: 5,
    },
  },

  thresholds: {
    http_req_duration: ['p(95)<2000'],
    http_req_failed: ['rate<0.01'],
    checks: ['rate>0.99'],
    dropped_iterations: ['count==0'],
  },
};

export default function () {
  const response = http.get('http://localhost:3002/products');

  check(response, {
    'status is 200': (r) => r.status === 200,
    'response contains products': (r) =>
      Array.isArray(r.json()) && r.json().length > 0,
  });
}
