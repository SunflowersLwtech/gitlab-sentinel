"""
Sentinel Eval Metrics — Industry-standard agent evaluation metrics.

Implements:
- pass@k / pass^k (AWS DevOps Agent pattern)
- Detection Rate / False Positive Rate
- Tool Trajectory Scoring (Google ADK / LangChain AgentEvals pattern)
- Rubric-based Scoring
- Latency & Token tracking (Green Agent Prize)
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvalStatus(Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass
class MetricResult:
    name: str
    status: EvalStatus
    score: float  # 0.0 - 1.0
    detail: str = ""
    raw_value: Any = None


@dataclass
class ScenarioResult:
    scenario_id: str
    run_id: str
    metrics: list[MetricResult] = field(default_factory=list)
    total_tool_calls: int = 0
    latency_seconds: float = 0.0
    token_usage: int = 0

    @property
    def passed(self) -> bool:
        return all(m.status == EvalStatus.PASS for m in self.metrics)

    @property
    def overall_score(self) -> float:
        if not self.metrics:
            return 0.0
        return sum(m.score for m in self.metrics) / len(self.metrics)

    def summary(self) -> str:
        lines = [f"Scenario {self.scenario_id} (run {self.run_id}): {'PASS' if self.passed else 'FAIL'}"]
        lines.append(f"  Overall score: {self.overall_score:.2f}")
        lines.append(f"  Tool calls: {self.total_tool_calls} | Latency: {self.latency_seconds:.1f}s | Tokens: {self.token_usage}")
        for m in self.metrics:
            icon = "✅" if m.status == EvalStatus.PASS else "⚠️" if m.status == EvalStatus.PARTIAL else "❌"
            lines.append(f"  {icon} {m.name}: {m.score:.2f} — {m.detail}")
        return "\n".join(lines)


# ── Detection Metrics ──


def eval_detection_completeness(findings: list[dict], required: list[dict]) -> MetricResult:
    """Check if all required vulnerabilities were detected."""
    detected = 0
    for req in required:
        req_types = req.get("type_contains", [])
        req_cwe = req.get("cwe_contains", "")
        for f in findings:
            f_type = f.get("type", "").lower()
            f_cwe = f.get("cwe", "").lower()
            type_match = any(t.lower() in f_type for t in req_types) if req_types else True
            cwe_match = req_cwe.lower() in f_cwe if req_cwe else True
            if type_match and cwe_match:
                detected += 1
                break
    total = len(required)
    score = detected / total if total > 0 else 1.0
    if detected == total:
        status = EvalStatus.PASS
    elif detected > 0:
        status = EvalStatus.PARTIAL
    else:
        status = EvalStatus.FAIL
    return MetricResult(
        name="detection_completeness",
        status=status,
        score=score,
        detail=f"{detected}/{total} required findings detected",
        raw_value={"detected": detected, "total": total},
    )


def eval_false_positive_rate(findings: list[dict], max_allowed: int = 0) -> MetricResult:
    """Count unexpected critical/high findings."""
    false_positives = sum(
        1 for f in findings
        if f.get("severity", "").lower() in ("critical", "high")
        and f.get("is_expected") is False
    )
    status = EvalStatus.PASS if false_positives <= max_allowed else EvalStatus.FAIL
    return MetricResult(
        name="false_positive_rate",
        status=status,
        score=1.0 if false_positives == 0 else max(0, 1.0 - false_positives * 0.25),
        detail=f"{false_positives} false positives (max allowed: {max_allowed})",
        raw_value=false_positives,
    )


def eval_risk_score(actual_score: float, expected_min: float = None, expected_max: float = None) -> MetricResult:
    """Check if risk score is within expected range."""
    in_range = True
    detail_parts = []
    if expected_min is not None and actual_score < expected_min:
        in_range = False
        detail_parts.append(f"score {actual_score} < min {expected_min}")
    if expected_max is not None and actual_score > expected_max:
        in_range = False
        detail_parts.append(f"score {actual_score} > max {expected_max}")
    if in_range:
        detail_parts.append(f"score {actual_score} within range")
    return MetricResult(
        name="risk_score_accuracy",
        status=EvalStatus.PASS if in_range else EvalStatus.FAIL,
        score=1.0 if in_range else 0.0,
        detail=", ".join(detail_parts),
        raw_value=actual_score,
    )


def eval_prediction_accuracy(actual: str, expected_values: list[str]) -> MetricResult:
    """Check if prediction matches expected values."""
    match = actual.lower() in [v.lower() for v in expected_values]
    return MetricResult(
        name="prediction_accuracy",
        status=EvalStatus.PASS if match else EvalStatus.FAIL,
        score=1.0 if match else 0.0,
        detail=f"'{actual}' {'in' if match else 'NOT in'} {expected_values}",
        raw_value=actual,
    )


def eval_keywords_present(text: str, must_contain: list[str]) -> MetricResult:
    """Check if output contains required keywords."""
    text_lower = text.lower()
    found = [kw for kw in must_contain if kw.lower() in text_lower]
    missing = [kw for kw in must_contain if kw.lower() not in text_lower]
    score = len(found) / len(must_contain) if must_contain else 1.0
    status = EvalStatus.PASS if not missing else EvalStatus.PARTIAL if found else EvalStatus.FAIL
    return MetricResult(
        name="keyword_presence",
        status=status,
        score=score,
        detail=f"Found {len(found)}/{len(must_contain)}, missing: {missing}" if missing else "All keywords found",
        raw_value={"found": found, "missing": missing},
    )


# ── Tool Trajectory Metrics ──


def eval_tool_trajectory(
    actual_calls: list[str],
    must_call: list[str] = None,
    should_call: list[str] = None,
    must_not_call: list[str] = None,
    max_calls: int = None,
) -> MetricResult:
    """Evaluate agent tool call trajectory against expectations.

    Inspired by Google ADK tool_trajectory_avg_score and LangChain AgentEvals.
    """
    issues = []
    score = 1.0

    # Must call
    if must_call:
        for tool in must_call:
            if tool not in actual_calls:
                issues.append(f"MISSING required: {tool}")
                score -= 0.3

    # Should call (soft requirement)
    if should_call:
        for tool in should_call:
            if tool not in actual_calls:
                issues.append(f"MISSING recommended: {tool}")
                score -= 0.1

    # Must not call
    if must_not_call:
        for tool in must_not_call:
            if tool in actual_calls:
                issues.append(f"FORBIDDEN call: {tool}")
                score -= 0.3

    # Max calls (efficiency)
    if max_calls and len(actual_calls) > max_calls:
        issues.append(f"Too many calls: {len(actual_calls)} > {max_calls}")
        score -= 0.2

    score = max(0.0, min(1.0, score))
    status = EvalStatus.PASS if score >= 0.8 else EvalStatus.PARTIAL if score >= 0.5 else EvalStatus.FAIL
    return MetricResult(
        name="tool_trajectory",
        status=status,
        score=score,
        detail="; ".join(issues) if issues else f"All checks passed ({len(actual_calls)} calls)",
        raw_value={"actual_calls": actual_calls, "call_count": len(actual_calls)},
    )


# ── Reliability Metrics (pass@k / pass^k) ──


def compute_pass_at_k(run_results: list[bool], k: int = None) -> float:
    """pass@k: probability of at least 1 pass in k attempts."""
    if k is None:
        k = len(run_results)
    successes = sum(run_results[:k])
    return 1.0 if successes > 0 else 0.0


def compute_pass_hat_k(run_results: list[bool], k: int = None) -> float:
    """pass^k (reliability): fraction of passes in k attempts."""
    if k is None:
        k = len(run_results)
    results = run_results[:k]
    return sum(results) / len(results) if results else 0.0


# ── Report Comment Metrics ──


def eval_report_posted(report_text: str) -> MetricResult:
    """Check if reporter produced a non-empty report."""
    posted = bool(report_text and len(report_text.strip()) > 50)
    return MetricResult(
        name="report_posted",
        status=EvalStatus.PASS if posted else EvalStatus.FAIL,
        score=1.0 if posted else 0.0,
        detail=f"Report length: {len(report_text)} chars" if report_text else "No report generated",
        raw_value=len(report_text) if report_text else 0,
    )


# ── Efficiency Metrics (Green Agent Prize) ──


def eval_efficiency(total_tool_calls: int, latency_s: float, token_count: int) -> MetricResult:
    """Evaluate agent efficiency for Green Agent Prize eligibility."""
    issues = []
    score = 1.0
    if total_tool_calls > 100:
        issues.append(f"Excessive tool calls: {total_tool_calls}")
        score -= 0.3
    if latency_s > 300:  # 5 min
        issues.append(f"Slow execution: {latency_s:.0f}s")
        score -= 0.3
    if token_count > 50000:
        issues.append(f"High token usage: {token_count}")
        score -= 0.2
    score = max(0.0, score)
    status = EvalStatus.PASS if score >= 0.8 else EvalStatus.PARTIAL if score >= 0.5 else EvalStatus.FAIL
    return MetricResult(
        name="efficiency",
        status=status,
        score=score,
        detail="; ".join(issues) if issues else f"Efficient: {total_tool_calls} calls, {latency_s:.0f}s, {token_count} tokens",
        raw_value={"tool_calls": total_tool_calls, "latency_s": latency_s, "tokens": token_count},
    )
