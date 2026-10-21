import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

from pipeline_orchestrator import evaluate, extract_metrics, load_profile, validate_phases


class PipelineOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.profile = load_profile()

    def test_extracts_real_k6_metric_values(self):
        summary = {
            "metrics": {
                "http_req_duration": {"p(95)": 12.345},
                "http_reqs": {"rate": 10.2, "count": 306},
                "http_req_failed": {"value": 0.0},
                "checks": {"value": 1.0},
                "dropped_iterations": {"count": 0},
            }
        }
        metrics = extract_metrics(summary)
        self.assertEqual(metrics["p95_ms"], 12.345)
        self.assertEqual(metrics["http_request_rate_per_sec"], 10.2)
        self.assertEqual(metrics["http_error_rate_percent"], 0.0)
        self.assertEqual(metrics["checks_rate"], 1.0)
        self.assertEqual(metrics["dropped_iterations"], 0)

    def test_baseline_gate_passes_when_all_criteria_pass(self):
        metrics = {
            "p95_ms": 25.0,
            "http_request_rate_per_sec": 10.1,
            "http_error_rate_percent": 0.0,
            "checks_rate": 1.0,
            "dropped_iterations": 0,
        }
        result = evaluate(metrics, self.profile["phases"]["baseline"], self.profile["sla"])
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(result["checks"].values()))

    def test_gate_fails_if_p95_exceeds_sla(self):
        metrics = {
            "p95_ms": 2001.0,
            "http_request_rate_per_sec": 10.1,
            "http_error_rate_percent": 0.0,
            "checks_rate": 1.0,
            "dropped_iterations": 0,
        }
        result = evaluate(metrics, self.profile["phases"]["baseline"], self.profile["sla"])
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["checks"]["p95"])

    def test_intensive_phases_require_explicit_permission(self):
        with self.assertRaises(ValueError):
            validate_phases(["baseline", "load"], self.profile, allow_intensive=False)
        validate_phases(["baseline", "load"], self.profile, allow_intensive=True)

    def test_phase_order_is_enforced(self):
        with self.assertRaises(ValueError):
            validate_phases(["load", "baseline"], self.profile, allow_intensive=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
