# Sentinel Evaluation Framework

> TDD for AI Agents: Red → Green → Refactor

## Quick Start

```bash
# Install dependencies
pip install pyyaml jsonschema

# Run YAML validation (offline, no API needed)
python -m pytest tests/ -v

# Run eval scenarios (requires live flow execution results)
python eval/evaluate.py eval/results/scenario_a_run1.json
python eval/evaluate.py --all eval/results/
```

## Directory Structure

```
eval/
├── README.md                  # This file
├── scenarios/                 # Benchmark definitions (ground truth)
│   ├── scenario_a_security.json
│   ├── scenario_b_pipeline.json
│   ├── scenario_c_delivery.json
│   └── scenario_d_false_positive.json
├── results/                   # Execution results (gitignored)
│   └── .gitkeep
├── evaluate.py                # Evaluation runner
├── metrics.py                 # Metric calculations
└── report.py                  # Generate eval summary

tests/
├── conftest.py                # Shared fixtures
├── test_yaml_validation.py    # Flow/Agent YAML structure tests
├── test_output_schemas.py     # Agent output JSON schema validation
├── test_flow_integrity.py     # Flow routing & wiring tests
└── test_prompt_quality.py     # Prompt best-practice checks
```

## Evaluation Workflow

```
1. Trigger flow on test MR → capture session output
2. Save raw output to eval/results/scenario_X_runN.json
3. Run evaluate.py → scores each metric
4. Compare against scenario ground truth
5. Iterate prompts until GREEN
```
