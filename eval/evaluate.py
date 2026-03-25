#!/usr/bin/env python3
"""
Sentinel Evaluation Runner

Usage:
    python eval/evaluate.py eval/results/scenario_a_run1.json
    python eval/evaluate.py --all eval/results/
    python eval/evaluate.py --scenario A eval/results/

Reads agent execution results and scores them against benchmark scenarios.
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.metrics import (
    EvalStatus,
    ScenarioResult,
    compute_pass_at_k,
    compute_pass_hat_k,
    eval_detection_completeness,
    eval_efficiency,
    eval_false_positive_rate,
    eval_keywords_present,
    eval_prediction_accuracy,
    eval_report_posted,
    eval_risk_score,
    eval_tool_trajectory,
)

SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def load_scenario(scenario_id: str) -> dict:
    """Load scenario definition by ID (A, B, C, D)."""
    mapping = {
        "A": "scenario_a_security.json",
        "B": "scenario_b_pipeline.json",
        "C": "scenario_c_delivery.json",
        "D": "scenario_d_false_positive.json",
    }
    filename = mapping.get(scenario_id.upper())
    if not filename:
        raise ValueError(f"Unknown scenario: {scenario_id}. Valid: {list(mapping.keys())}")
    path = SCENARIOS_DIR / filename
    with open(path) as f:
        return json.load(f)


def parse_agent_output(raw_text: str) -> dict:
    """Try to extract JSON from agent's final_answer text."""
    if not raw_text:
        return {}
    # Try direct parse
    try:
        return json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        pass
    # Try finding JSON in text
    for match in [r'\{[^{}]*\}', r'\{.*\}']:
        import re
        found = re.search(match, raw_text, re.DOTALL)
        if found:
            try:
                return json.loads(found.group())
            except json.JSONDecodeError:
                continue
    return {"_raw": raw_text}


def evaluate_scenario_a(result: dict, scenario: dict) -> ScenarioResult:
    """Evaluate Security Vulnerability Detection scenario."""
    sr = ScenarioResult(scenario_id="A", run_id=result.get("run_id", "unknown"))

    expected = scenario["expected"]

    # Triage
    triage = parse_agent_output(result.get("triage_agent", {}).get("final_answer", ""))
    if triage:
        sr.metrics.append(eval_prediction_accuracy(
            triage.get("overall_risk_level", "unknown"),
            expected["triage"]["overall_risk_level"],
        ))
        sec_score = triage.get("security_risk", {}).get("score", 0)
        sr.metrics.append(eval_risk_score(sec_score, expected_min=expected["triage"]["security_risk_score_min"]))

    # Security Scanner
    security = parse_agent_output(result.get("security_scanner", {}).get("final_answer", ""))
    if security:
        findings = security.get("findings", [])
        sr.metrics.append(eval_detection_completeness(
            findings, expected["security_scanner"]["required_findings"]
        ))
        sr.metrics.append(eval_false_positive_rate(findings, max_allowed=0))
        sr.metrics.append(eval_risk_score(
            security.get("security_score", 0),
            expected_min=expected["security_scanner"]["security_score_min"],
        ))

    # Reporter
    report = result.get("reporter", {}).get("report_text", "")
    sr.metrics.append(eval_report_posted(report))
    if report:
        sr.metrics.append(eval_keywords_present(
            report, expected["reporter"]["must_contain_keywords"]
        ))

    # Tool trajectory
    for agent_name, expected_traj in scenario.get("expected_tool_trajectory", {}).items():
        actual_calls = result.get(agent_name, {}).get("tool_calls", [])
        sr.metrics.append(eval_tool_trajectory(
            actual_calls=actual_calls,
            must_call=expected_traj.get("must_call"),
            should_call=expected_traj.get("should_call"),
            must_not_call=expected_traj.get("must_not_call"),
            max_calls=expected_traj.get("max_tool_calls"),
        ))

    # Efficiency
    sr.total_tool_calls = result.get("total_tool_calls", 0)
    sr.latency_seconds = result.get("latency_seconds", 0)
    sr.token_usage = result.get("token_usage", 0)
    sr.metrics.append(eval_efficiency(sr.total_tool_calls, sr.latency_seconds, sr.token_usage))

    return sr


def evaluate_scenario_b(result: dict, scenario: dict) -> ScenarioResult:
    """Evaluate Dependency Conflict Detection scenario."""
    sr = ScenarioResult(scenario_id="B", run_id=result.get("run_id", "unknown"))
    expected = scenario["expected"]

    # Pipeline Predictor
    pipeline = parse_agent_output(result.get("pipeline_predictor", {}).get("final_answer", ""))
    if pipeline:
        sr.metrics.append(eval_prediction_accuracy(
            pipeline.get("prediction", "unknown"),
            expected["pipeline_predictor"]["prediction"],
        ))
        full_text = json.dumps(pipeline)
        sr.metrics.append(eval_keywords_present(
            full_text, expected["pipeline_predictor"]["must_mention"]
        ))
        sr.metrics.append(eval_risk_score(
            pipeline.get("pipeline_health_score", 100),
            expected_max=expected["pipeline_predictor"]["pipeline_health_score_max"],
        ))

    # Security Scanner should NOT trigger false alarms
    security = parse_agent_output(result.get("security_scanner", {}).get("final_answer", ""))
    if security:
        critical = [f for f in security.get("findings", []) if f.get("severity", "").lower() == "critical"]
        sr.metrics.append(eval_false_positive_rate(
            [{"severity": "critical", "is_expected": False} for _ in critical],
            max_allowed=0,
        ))

    # Reporter
    report = result.get("reporter", {}).get("report_text", "")
    sr.metrics.append(eval_report_posted(report))

    sr.total_tool_calls = result.get("total_tool_calls", 0)
    sr.latency_seconds = result.get("latency_seconds", 0)
    sr.token_usage = result.get("token_usage", 0)
    sr.metrics.append(eval_efficiency(sr.total_tool_calls, sr.latency_seconds, sr.token_usage))

    return sr


def evaluate_scenario_d(result: dict, scenario: dict) -> ScenarioResult:
    """Evaluate False Positive Test (all green) scenario."""
    sr = ScenarioResult(scenario_id="D", run_id=result.get("run_id", "unknown"))
    expected = scenario["expected"]

    # Triage should be LOW
    triage = parse_agent_output(result.get("triage_agent", {}).get("final_answer", ""))
    if triage:
        sr.metrics.append(eval_prediction_accuracy(
            triage.get("overall_risk_level", "unknown"),
            expected["triage"]["overall_risk_level"],
        ))
        for dim in ("pipeline_risk", "security_risk", "delivery_risk"):
            dim_score = triage.get(dim, {}).get("score", 0)
            max_key = f"{dim.split('_')[0]}_risk_score_max"
            if max_key in expected["triage"]:
                sr.metrics.append(eval_risk_score(dim_score, expected_max=expected["triage"][max_key]))

    # Pipeline should predict PASS
    pipeline = parse_agent_output(result.get("pipeline_predictor", {}).get("final_answer", ""))
    if pipeline:
        sr.metrics.append(eval_prediction_accuracy(
            pipeline.get("prediction", "unknown"),
            expected["pipeline_predictor"]["prediction"],
        ))

    # Security should be CLEAN
    security = parse_agent_output(result.get("security_scanner", {}).get("final_answer", ""))
    if security:
        sr.metrics.append(eval_prediction_accuracy(
            security.get("scan_result", "unknown"), [expected["security_scanner"]["scan_result"]]
        ))
        findings = security.get("findings", [])
        sr.metrics.append(eval_false_positive_rate(
            [{"severity": f.get("severity", "low"), "is_expected": False} for f in findings],
            max_allowed=0,
        ))

    # Reporter
    report = result.get("reporter", {}).get("report_text", "")
    sr.metrics.append(eval_report_posted(report))

    # Efficiency (should be fast for trivial change)
    sr.total_tool_calls = result.get("total_tool_calls", 0)
    sr.latency_seconds = result.get("latency_seconds", 0)
    sr.token_usage = result.get("token_usage", 0)
    sr.metrics.append(eval_efficiency(sr.total_tool_calls, sr.latency_seconds, sr.token_usage))

    return sr


EVALUATORS = {
    "A": evaluate_scenario_a,
    "B": evaluate_scenario_b,
    "C": evaluate_scenario_a,  # Reuse A's structure (generic multi-finding)
    "D": evaluate_scenario_d,
}


def evaluate(result_path: Path) -> ScenarioResult:
    """Load result file and evaluate against its scenario."""
    with open(result_path) as f:
        result = json.load(f)
    scenario_id = result.get("scenario_id", "").upper()
    scenario = load_scenario(scenario_id)
    evaluator = EVALUATORS.get(scenario_id)
    if not evaluator:
        raise ValueError(f"No evaluator for scenario {scenario_id}")
    return evaluator(result, scenario)


def main():
    parser = argparse.ArgumentParser(description="Sentinel Evaluation Runner")
    parser.add_argument("path", help="Result JSON file or directory")
    parser.add_argument("--scenario", help="Filter by scenario ID (A/B/C/D)")
    parser.add_argument("--all", action="store_true", help="Evaluate all files in directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    path = Path(args.path)
    results = []

    if path.is_file():
        results.append(evaluate(path))
    elif path.is_dir():
        for f in sorted(path.glob("*.json")):
            if f.name == ".gitkeep":
                continue
            try:
                sr = evaluate(f)
                if args.scenario and sr.scenario_id != args.scenario.upper():
                    continue
                results.append(sr)
            except Exception as e:
                print(f"Error evaluating {f.name}: {e}", file=sys.stderr)

    if not results:
        print("No results to evaluate.", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.json:
        out = []
        for r in results:
            out.append({
                "scenario_id": r.scenario_id,
                "run_id": r.run_id,
                "passed": r.passed,
                "overall_score": r.overall_score,
                "metrics": [{"name": m.name, "status": m.status.value, "score": m.score, "detail": m.detail} for m in r.metrics],
            })
        print(json.dumps(out, indent=2))
    else:
        print("=" * 60)
        print("SENTINEL EVALUATION REPORT")
        print("=" * 60)
        for r in results:
            print()
            print(r.summary())

        # Reliability summary if multiple runs of same scenario
        from collections import defaultdict
        by_scenario = defaultdict(list)
        for r in results:
            by_scenario[r.scenario_id].append(r.passed)
        print()
        print("-" * 40)
        print("RELIABILITY (pass@k / pass^k)")
        for sid, passes in by_scenario.items():
            k = len(passes)
            print(f"  Scenario {sid}: pass@{k}={compute_pass_at_k(passes):.2f}  pass^{k}={compute_pass_hat_k(passes):.2f}  ({sum(passes)}/{k} passed)")
        print("=" * 60)


if __name__ == "__main__":
    main()
