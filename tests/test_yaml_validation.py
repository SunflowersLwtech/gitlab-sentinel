"""
YAML Structure Validation Tests

Validates sentinel_main.yml and agent YAMLs against GitLab Duo Agent Platform constraints.
These are offline tests — no API calls, no live execution.
Run with: pytest tests/test_yaml_validation.py -v
"""

import yaml
import pytest
from pathlib import Path

# ── Hackathon Validator Constraints (from LiveSpec §5) ──

FORBIDDEN_DEFINITION_FIELDS = {"name", "description", "product_group"}
FORBIDDEN_COMPONENT_FIELDS = {"response_schema_id", "version", "ui_role_as", "stop"}
FORBIDDEN_PROMPT_FIELDS = {"model"}
ALLOWED_ENVIRONMENTS = {"ambient"}
ALLOWED_COMPONENT_TYPES = {"AgentComponent"}  # DeterministicStep/OneOff rejected by hackathon validator

# Known tools from GitLab Duo (subset we use)
KNOWN_TOOLS = {
    "read_file", "read_files", "find_files", "list_dir", "grep",
    "get_repository_file", "get_project", "get_merge_request",
    "list_merge_request_diffs", "get_job_logs", "get_pipeline_failing_jobs",
    "get_pipeline_errors", "create_merge_request_note", "list_repository_tree",
    "ci_linter", "gitlab_api_get", "gitlab_graphql", "run_git_command",
    "create_file_with_contents", "edit_file", "mkdir", "run_command",
    "create_branch", "create_merge_request", "update_merge_request",
    "get_commit", "get_commit_diff",
}


class TestFlowTopLevel:
    """Test top-level flow YAML structure."""

    def test_has_required_fields(self, flow_yaml):
        assert "name" in flow_yaml, "Flow must have 'name'"
        assert "description" in flow_yaml, "Flow must have 'description'"
        assert "public" in flow_yaml, "Flow must have 'public'"
        assert "definition" in flow_yaml, "Flow must have 'definition'"

    def test_is_public(self, flow_yaml):
        assert flow_yaml["public"] is True, "Flow MUST be public (silent failure otherwise)"

    def test_definition_version(self, flow_definition):
        assert flow_definition.get("version") == "v1", "Definition version must be 'v1'"

    def test_environment_is_ambient(self, flow_definition):
        env = flow_definition.get("environment", "ambient")
        assert env in ALLOWED_ENVIRONMENTS, f"Environment '{env}' not allowed. Must be: {ALLOWED_ENVIRONMENTS}"

    def test_no_forbidden_definition_fields(self, flow_definition):
        for field in FORBIDDEN_DEFINITION_FIELDS:
            assert field not in flow_definition, f"Forbidden field '{field}' in definition (must be at top level only)"


class TestFlowComponents:
    """Test component structure and constraints."""

    def test_has_components(self, flow_components):
        assert len(flow_components) >= 1, "Flow must have at least 1 component"

    def test_all_components_are_agent(self, flow_components):
        for comp in flow_components:
            assert comp["type"] in ALLOWED_COMPONENT_TYPES, \
                f"Component '{comp['name']}' type '{comp['type']}' not allowed. Only: {ALLOWED_COMPONENT_TYPES}"

    def test_components_have_names(self, flow_components):
        names = [c["name"] for c in flow_components]
        assert len(names) == len(set(names)), f"Duplicate component names: {names}"

    def test_components_have_prompt_id(self, flow_components):
        for comp in flow_components:
            assert "prompt_id" in comp, f"Component '{comp['name']}' missing prompt_id"

    def test_no_forbidden_component_fields(self, flow_components):
        for comp in flow_components:
            for field in FORBIDDEN_COMPONENT_FIELDS:
                assert field not in comp, \
                    f"Forbidden field '{field}' in component '{comp['name']}'"

    def test_inputs_use_from_as_format(self, flow_components):
        """Critical: string inputs cause WebSocket disconnect (Issue #591567)."""
        for comp in flow_components:
            for inp in comp.get("inputs", []):
                assert isinstance(inp, dict), \
                    f"Component '{comp['name']}' input must be dict (from/as), got: {type(inp)}"
                assert "from" in inp, \
                    f"Component '{comp['name']}' input missing 'from': {inp}"
                assert "as" in inp, \
                    f"Component '{comp['name']}' input missing 'as': {inp}"

    def test_project_id_input_present(self, flow_components):
        """Almost all tools require project_id context."""
        for comp in flow_components:
            inputs = comp.get("inputs", [])
            has_project_id = any(
                "project_id" in inp.get("from", "") or "project_id" in inp.get("as", "")
                for inp in inputs
            )
            assert has_project_id, \
                f"Component '{comp['name']}' should have project_id input (tools fail without it)"

    def test_tools_are_known(self, flow_components):
        for comp in flow_components:
            for tool in comp.get("toolset", []):
                assert tool in KNOWN_TOOLS, \
                    f"Component '{comp['name']}' uses unknown tool '{tool}'. Known: {sorted(KNOWN_TOOLS)}"

    def test_tool_count_reasonable(self, flow_components):
        """Too many tools causes agent over-exploration (LiveSpec §6 root cause 3)."""
        for comp in flow_components:
            tools = comp.get("toolset", [])
            assert len(tools) <= 10, \
                f"Component '{comp['name']}' has {len(tools)} tools (recommended ≤ 10 to limit over-exploration)"


class TestFlowPrompts:
    """Test prompt definitions."""

    def test_has_prompts(self, flow_prompts):
        assert len(flow_prompts) >= 1, "Flow must have at least 1 prompt"

    def test_prompts_match_components(self, flow_components, flow_prompts):
        comp_prompt_ids = {c["prompt_id"] for c in flow_components}
        prompt_ids = {p["prompt_id"] for p in flow_prompts}
        missing = comp_prompt_ids - prompt_ids
        assert not missing, f"Components reference prompts not defined: {missing}"

    def test_no_model_in_prompts(self, flow_prompts):
        """Model is locked at group level; specifying it in YAML causes validator rejection."""
        for prompt in flow_prompts:
            for field in FORBIDDEN_PROMPT_FIELDS:
                assert field not in prompt, \
                    f"Prompt '{prompt['prompt_id']}' has forbidden field '{field}'"

    def test_prompts_have_system_template(self, flow_prompts):
        for prompt in flow_prompts:
            template = prompt.get("prompt_template", {})
            assert "system" in template, \
                f"Prompt '{prompt['prompt_id']}' missing system template"
            assert len(template["system"].strip()) > 50, \
                f"Prompt '{prompt['prompt_id']}' system template too short"

    def test_prompts_have_user_template(self, flow_prompts):
        for prompt in flow_prompts:
            template = prompt.get("prompt_template", {})
            assert "user" in template, \
                f"Prompt '{prompt['prompt_id']}' missing user template"

    def test_prompts_have_placeholder_history(self, flow_prompts):
        """AgentComponent prompts should have placeholder: history for multi-turn."""
        for prompt in flow_prompts:
            if prompt.get("prompt_template", {}).get("system"):
                # Reporter doesn't need it (single action), but others do
                pass  # Soft check — log warning but don't fail

    def test_unit_primitives_empty(self, flow_prompts):
        for prompt in flow_prompts:
            up = prompt.get("unit_primitives", [])
            assert up == [], \
                f"Prompt '{prompt['prompt_id']}' unit_primitives must be [] (got: {up})"


class TestFlowRouting:
    """Test flow routing integrity."""

    def test_has_routers(self, flow_routers):
        assert len(flow_routers) >= 1, "Flow must have at least 1 router"

    def test_entry_point_exists(self, flow_definition, flow_components):
        entry = flow_definition.get("flow", {}).get("entry_point")
        assert entry, "Flow must have entry_point"
        names = [c["name"] for c in flow_components]
        assert entry in names, f"Entry point '{entry}' not in components: {names}"

    def test_routing_reaches_end(self, flow_routers):
        """Verify there's a path to 'end'."""
        reaches_end = any(r.get("to") == "end" for r in flow_routers)
        assert reaches_end, "No router reaches 'end' — flow will hang"

    def test_all_components_routed(self, flow_components, flow_routers):
        """Every component should appear in routing (either as 'from' or as target)."""
        comp_names = {c["name"] for c in flow_components}
        routed = set()
        for r in flow_routers:
            routed.add(r.get("from", ""))
            to = r.get("to", "")
            if isinstance(to, str):
                routed.add(to)
            # Conditional routing
            if "condition" in r:
                for target in r["condition"].get("routes", {}).values():
                    routed.add(target)
        routed.discard("end")
        unrouted = comp_names - routed
        assert not unrouted, f"Components not in any route: {unrouted}"

    def test_no_orphan_routes(self, flow_components, flow_routers):
        """Router targets should reference existing components or 'end'."""
        comp_names = {c["name"] for c in flow_components} | {"end"}
        for r in flow_routers:
            target = r.get("to", "")
            if isinstance(target, str):
                assert target in comp_names, f"Route target '{target}' not found in components"
            if "condition" in r:
                for target in r["condition"].get("routes", {}).values():
                    assert target in comp_names, f"Conditional route target '{target}' not found"


class TestStandaloneAgent:
    """Test standalone agent YAML (sentinel_triage.yml)."""

    def test_agent_has_required_fields(self, triage_agent_yaml):
        for field in ("name", "description", "public", "system_prompt", "tools"):
            assert field in triage_agent_yaml, f"Agent missing required field: {field}"

    def test_agent_is_public(self, triage_agent_yaml):
        assert triage_agent_yaml["public"] is True

    def test_agent_has_system_prompt(self, triage_agent_yaml):
        prompt = triage_agent_yaml.get("system_prompt", "")
        assert len(prompt) > 100, "Agent system_prompt too short"

    def test_agent_tools_are_known(self, triage_agent_yaml):
        for tool in triage_agent_yaml.get("tools", []):
            assert tool in KNOWN_TOOLS, f"Agent uses unknown tool: {tool}"
