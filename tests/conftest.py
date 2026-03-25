"""Shared fixtures for Sentinel test suite."""

import json
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FLOWS_DIR = PROJECT_ROOT / "flows"
AGENTS_DIR = PROJECT_ROOT / "agents"
EVAL_SCENARIOS_DIR = PROJECT_ROOT / "eval" / "scenarios"


@pytest.fixture
def flow_yaml():
    """Load and parse sentinel_main.yml."""
    path = FLOWS_DIR / "sentinel_main.yml"
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def flow_definition(flow_yaml):
    """Extract the v1 definition block."""
    return flow_yaml.get("definition", {})


@pytest.fixture
def flow_components(flow_definition):
    """List of components from the flow."""
    return flow_definition.get("components", [])


@pytest.fixture
def flow_prompts(flow_definition):
    """List of prompts from the flow."""
    return flow_definition.get("prompts", [])


@pytest.fixture
def flow_routers(flow_definition):
    """List of routers from the flow."""
    return flow_definition.get("routers", [])


@pytest.fixture
def triage_agent_yaml():
    """Load and parse sentinel_triage.yml standalone agent."""
    path = AGENTS_DIR / "sentinel_triage.yml"
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture(params=["scenario_a_security", "scenario_b_pipeline", "scenario_c_delivery", "scenario_d_false_positive"])
def eval_scenario(request):
    """Parametrized fixture loading each eval scenario."""
    path = EVAL_SCENARIOS_DIR / f"{request.param}.json"
    with open(path) as f:
        return json.load(f)
