"""
Agent Output Schema Validation Tests

Validates that agent outputs conform to expected JSON schemas.
Used to test real execution results or mock outputs.
Run with: pytest tests/test_output_schemas.py -v
"""

import json
import pytest

# ── Expected Output Schema for Unified Analyzer (from sentinel_main.yml) ──

ANALYZER_SCHEMA_REQUIRED_KEYS = {
    "overall_risk_level", "pipeline_risk", "security_risk", "delivery_risk", "summary"
}
RISK_LEVELS = {"low", "medium", "high", "critical"}

# Pipeline sub-schema
PIPELINE_RISK_KEYS = {"score", "indicators", "prediction", "predicted_failures", "health_score"}
PIPELINE_PREDICTIONS = {"pass", "likely_fail", "high_risk_fail"}

# Security sub-schema
SECURITY_RISK_KEYS = {"score", "scan_result", "findings", "security_score"}
SECURITY_SCAN_RESULTS = {"clean", "findings", "critical_findings"}
FINDING_REQUIRED_KEYS = {"severity", "type", "file", "description", "cwe", "recommendation", "auto_fixable"}
SEVERITY_LEVELS = {"critical", "high", "medium", "low"}

# Delivery sub-schema
DELIVERY_RISK_KEYS = {"score", "indicators", "recommendation"}

# Legacy triage schema (standalone agent compatibility)
TRIAGE_SCHEMA_REQUIRED_KEYS = {
    "overall_risk_level", "pipeline_risk", "security_risk", "delivery_risk", "summary"
}
RISK_DIMENSION_KEYS = {"score", "indicators", "recommendation"}


def parse_output(text: str) -> dict:
    """Parse JSON from agent output text."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


# ── Sample outputs for offline testing ──

SAMPLE_ANALYZER_GOOD = json.dumps({
    "overall_risk_level": "high",
    "pipeline_risk": {
        "score": 6,
        "indicators": ["dependency version conflict"],
        "prediction": "likely_fail",
        "predicted_failures": [
            {"type": "dependency", "description": "Flask 3.x vs werkzeug 2.x pinned", "prevention": "Pin werkzeug>=3.0", "auto_fixable": True}
        ],
        "health_score": 35
    },
    "security_risk": {
        "score": 9,
        "scan_result": "critical_findings",
        "findings": [
            {"severity": "critical", "type": "hardcoded_secret", "file": "app.py", "line": "42", "description": "API key in source", "cwe": "CWE-798", "recommendation": "Use env vars", "auto_fixable": True},
            {"severity": "critical", "type": "sql_injection", "file": "db.py", "line": "15", "description": "Unsanitized query", "cwe": "CWE-89", "recommendation": "Use parameterized queries", "auto_fixable": True},
        ],
        "security_score": 15
    },
    "delivery_risk": {
        "score": 3,
        "indicators": ["moderate diff size"],
        "recommendation": "Add unit tests for new endpoints"
    },
    "summary": "Critical security vulnerabilities and pipeline risk detected",
    "mr_iid": 3,
    "tool_calls_used": 6
})

SAMPLE_ANALYZER_LOW_RISK = json.dumps({
    "overall_risk_level": "low",
    "pipeline_risk": {
        "score": 0,
        "indicators": [],
        "prediction": "pass",
        "predicted_failures": [],
        "health_score": 100
    },
    "security_risk": {
        "score": 0,
        "scan_result": "clean",
        "findings": [],
        "security_score": 100
    },
    "delivery_risk": {
        "score": 1,
        "indicators": [],
        "recommendation": "No concerns"
    },
    "summary": "Trivial documentation change, no risks detected",
    "mr_iid": 5,
    "tool_calls_used": 2
})

# Legacy standalone agent sample
SAMPLE_TRIAGE_GOOD = json.dumps({
    "overall_risk_level": "high",
    "pipeline_risk": {"score": 3, "indicators": ["dependency change"], "recommendation": "Check versions"},
    "security_risk": {"score": 9, "indicators": ["hardcoded key"], "recommendation": "Remove secret"},
    "delivery_risk": {"score": 2, "indicators": [], "recommendation": "Low risk"},
    "summary": "High security risk due to hardcoded credentials"
})


class TestAnalyzerOutputSchema:
    """Validate unified analyzer output structure."""

    @pytest.mark.parametrize("output_text", [SAMPLE_ANALYZER_GOOD, SAMPLE_ANALYZER_LOW_RISK])
    def test_has_required_keys(self, output_text):
        data = parse_output(output_text)
        missing = ANALYZER_SCHEMA_REQUIRED_KEYS - set(data.keys())
        assert not missing, f"Missing keys: {missing}"

    @pytest.mark.parametrize("output_text", [SAMPLE_ANALYZER_GOOD, SAMPLE_ANALYZER_LOW_RISK])
    def test_risk_level_valid(self, output_text):
        data = parse_output(output_text)
        level = data.get("overall_risk_level", "")
        assert level.lower() in RISK_LEVELS, f"Invalid risk level: {level}"

    @pytest.mark.parametrize("output_text", [SAMPLE_ANALYZER_GOOD, SAMPLE_ANALYZER_LOW_RISK])
    def test_pipeline_risk_structure(self, output_text):
        data = parse_output(output_text)
        pr = data.get("pipeline_risk", {})
        assert isinstance(pr.get("score"), (int, float)), "pipeline_risk.score must be numeric"
        assert 0 <= pr["score"] <= 10, f"pipeline_risk.score {pr['score']} out of range 0-10"
        assert pr.get("prediction") in PIPELINE_PREDICTIONS, f"Invalid prediction: {pr.get('prediction')}"
        assert isinstance(pr.get("predicted_failures"), list), "predicted_failures must be list"
        for failure in pr.get("predicted_failures", []):
            for key in ("type", "description", "prevention", "auto_fixable"):
                assert key in failure, f"Failure missing key: {key}"
        assert isinstance(pr.get("health_score"), (int, float)), "health_score must be numeric"
        assert 0 <= pr["health_score"] <= 100, f"health_score {pr['health_score']} out of range"

    @pytest.mark.parametrize("output_text", [SAMPLE_ANALYZER_GOOD, SAMPLE_ANALYZER_LOW_RISK])
    def test_security_risk_structure(self, output_text):
        data = parse_output(output_text)
        sr = data.get("security_risk", {})
        assert isinstance(sr.get("score"), (int, float)), "security_risk.score must be numeric"
        assert 0 <= sr["score"] <= 10, f"security_risk.score {sr['score']} out of range 0-10"
        assert sr.get("scan_result") in SECURITY_SCAN_RESULTS, f"Invalid scan_result: {sr.get('scan_result')}"
        assert isinstance(sr.get("findings"), list), "findings must be list"
        for finding in sr.get("findings", []):
            missing = FINDING_REQUIRED_KEYS - set(finding.keys())
            assert not missing, f"Finding missing keys: {missing}"
            assert finding["severity"].lower() in SEVERITY_LEVELS, f"Invalid severity: {finding['severity']}"
        assert isinstance(sr.get("security_score"), (int, float)), "security_score must be numeric"
        assert 0 <= sr["security_score"] <= 100, f"security_score {sr['security_score']} out of range"

    @pytest.mark.parametrize("output_text", [SAMPLE_ANALYZER_GOOD, SAMPLE_ANALYZER_LOW_RISK])
    def test_delivery_risk_structure(self, output_text):
        data = parse_output(output_text)
        dr = data.get("delivery_risk", {})
        assert isinstance(dr.get("score"), (int, float)), "delivery_risk.score must be numeric"
        assert 0 <= dr["score"] <= 10, f"delivery_risk.score {dr['score']} out of range 0-10"
        assert isinstance(dr.get("indicators"), list), "indicators must be list"

    @pytest.mark.parametrize("output_text", [SAMPLE_ANALYZER_GOOD])
    def test_has_mr_iid(self, output_text):
        data = parse_output(output_text)
        assert "mr_iid" in data, "Analyzer output should include mr_iid"
        assert isinstance(data["mr_iid"], (int, float)), "mr_iid must be numeric"


class TestTriageOutputSchema:
    """Validate standalone triage agent output structure (backwards compatibility)."""

    @pytest.mark.parametrize("output_text", [SAMPLE_TRIAGE_GOOD])
    def test_has_required_keys(self, output_text):
        data = parse_output(output_text)
        missing = TRIAGE_SCHEMA_REQUIRED_KEYS - set(data.keys())
        assert not missing, f"Missing keys: {missing}"

    @pytest.mark.parametrize("output_text", [SAMPLE_TRIAGE_GOOD])
    def test_risk_level_valid(self, output_text):
        data = parse_output(output_text)
        level = data.get("overall_risk_level", "")
        assert level.lower() in RISK_LEVELS, f"Invalid risk level: {level}"

    @pytest.mark.parametrize("output_text", [SAMPLE_TRIAGE_GOOD])
    def test_risk_dimensions_structure(self, output_text):
        data = parse_output(output_text)
        for dim in ("pipeline_risk", "security_risk", "delivery_risk"):
            assert dim in data, f"Missing dimension: {dim}"
            dim_data = data[dim]
            missing = RISK_DIMENSION_KEYS - set(dim_data.keys())
            assert not missing, f"{dim} missing keys: {missing}"
            assert isinstance(dim_data["score"], (int, float)), f"{dim} score must be numeric"
            assert 0 <= dim_data["score"] <= 10, f"{dim} score {dim_data['score']} out of range 0-10"
            assert isinstance(dim_data["indicators"], list), f"{dim} indicators must be list"
