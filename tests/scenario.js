import http from 'k6/http';
import { check } from 'k6';

const targetUrl = __ENV.PERF_BASE_URL || 'http://localhost:3002/products';
const rate = Number(__ENV.PERF_RATE || 10);
const duration = __ENV.PERF_DURATION || '30s';
const preAllocatedVUs = Number(__ENV.PERF_PREALLOCATED_VUS || 2);
const maxVUs = Number(__ENV.PERF_MAX_VUS || 5);

export const options = {
  scenarios: {
    selected_phase: {
      executor: 'constant-arrival-rate',
      rate,
      timeUnit: '1s',
      duration,
      preAllocatedVUs,
      maxVUs,
    },
  },
};

export default function () {
  const response = http.get(targetUrl, { tags: { endpoint: 'products' } });
  let isJsonArray = false;
  try {
    const body = response.json();
    isJsonArray = Array.isArray(body) && body.length > 0;
  } catch (_) {
    isJsonArray = false;
  }

  check(response, {
    'status is 200': (r) => r.status === 200,
    'response contains products': () => isJsonArray,
  });
}
