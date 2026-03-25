"""
Flow Integrity Tests

Validates the logical integrity of the flow graph: data wiring, reachability, and dependencies.
Run with: pytest tests/test_flow_integrity.py -v
"""

import pytest


class TestDataWiring:
    """Test that component inputs reference valid upstream outputs."""

    def test_first_component_uses_context(self, flow_definition):
        """Entry point should only reference context: inputs (not other components)."""
        entry = flow_definition["flow"]["entry_point"]
        entry_comp = next(c for c in flow_definition["components"] if c["name"] == entry)
        for inp in entry_comp.get("inputs", []):
            source = inp["from"]
            assert source.startswith("context:"), \
                f"Entry component '{entry}' input references non-context source: {source}"
            # Entry should NOT reference other component final_answers
            assert ".final_answer" not in source or source.startswith("context:goal") or source.startswith("context:project_id"), \
                f"Entry component '{entry}' references another component's output: {source}"

    def test_downstream_refs_exist(self, flow_components, flow_routers):
        """If component B references A.final_answer, A must execute before B."""
        comp_names = [c["name"] for c in flow_components]

        # Build execution order from routers
        order = []
        for r in flow_routers:
            if r["from"] not in order:
                order.append(r["from"])
            to = r.get("to", "")
            if to != "end" and to not in order:
                order.append(to)

        # Check each component's inputs
        for comp in flow_components:
            comp_idx = order.index(comp["name"]) if comp["name"] in order else -1
            for inp in comp.get("inputs", []):
                source = inp["from"]
                # Check references to other component outputs
                if ".final_answer" in source and source.startswith("context:"):
                    ref_name = source.replace("context:", "").split(".")[0]
                    if ref_name in comp_names:
                        ref_idx = order.index(ref_name) if ref_name in order else -1
                        assert ref_idx < comp_idx, \
                            f"'{comp['name']}' references '{ref_name}.final_answer' but '{ref_name}' executes after it"

    def test_reporter_receives_analyzer_output(self, flow_components):
        """Reporter should receive the analyzer's output."""
        reporter = next((c for c in flow_components if c["name"] == "reporter"), None)
        if not reporter:
            pytest.skip("No reporter component")
        input_sources = [inp["from"] for inp in reporter.get("inputs", [])]
        assert any("analyzer" in src for src in input_sources), \
            f"Reporter missing input from 'analyzer'. Sources: {input_sources}"


class TestFlowGraph:
    """Test the flow graph for completeness and correctness."""

    def test_linear_chain_reachability(self, flow_definition):
        """Traverse from entry_point to 'end' following routers."""
        entry = flow_definition["flow"]["entry_point"]
        routers = flow_definition.get("routers", [])
        router_map = {}
        for r in routers:
            frm = r["from"]
            to = r.get("to")
            if to:
                router_map[frm] = to
            elif "condition" in r:
                routes = r["condition"].get("routes", {})
                router_map[frm] = routes.get("default_route", list(routes.values())[0] if routes else "end")

        visited = set()
        current = entry
        while current != "end":
            assert current not in visited, f"Cycle detected at '{current}'"
            visited.add(current)
            assert current in router_map, f"Dead end at '{current}' — no route to next component"
            current = router_map[current]

    def test_no_unreachable_components(self, flow_components, flow_definition):
        """Every component should be reachable from entry_point."""
        entry = flow_definition["flow"]["entry_point"]
        routers = flow_definition.get("routers", [])

        # Build adjacency
        reachable = set()
        queue = [entry]
        adj = {}
        for r in routers:
            frm = r["from"]
            targets = []
            if "to" in r:
                targets.append(r["to"])
            if "condition" in r:
                targets.extend(r["condition"].get("routes", {}).values())
            adj.setdefault(frm, []).extend(targets)

        while queue:
            node = queue.pop(0)
            if node in reachable or node == "end":
                continue
            reachable.add(node)
            for target in adj.get(node, []):
                queue.append(target)

        comp_names = {c["name"] for c in flow_components}
        unreachable = comp_names - reachable
        assert not unreachable, f"Unreachable components: {unreachable}"

    def test_exactly_two_components(self, flow_components):
        """Championship architecture: exactly 2 agents (analyzer + reporter)."""
        assert len(flow_components) == 2, \
            f"Expected 2 components (analyzer + reporter), got {len(flow_components)}: {[c['name'] for c in flow_components]}"


class TestPromptComponentAlignment:
    """Test that prompts and components are properly aligned."""

    def test_prompt_ids_unique(self, flow_prompts):
        ids = [p["prompt_id"] for p in flow_prompts]
        assert len(ids) == len(set(ids)), f"Duplicate prompt_ids: {ids}"

    def test_prompt_placeholders_match_inputs(self, flow_components, flow_prompts):
        """Check that {{placeholder}} in prompts correspond to component input 'as' values."""
        prompt_map = {p["prompt_id"]: p for p in flow_prompts}
        for comp in flow_components:
            pid = comp.get("prompt_id")
            if pid not in prompt_map:
                continue
            prompt = prompt_map[pid]
            template = prompt.get("prompt_template", {})
            user_template = template.get("user", "")

            # Extract {{placeholders}}
            import re
            placeholders = set(re.findall(r'\{\{(\w+)\}\}', user_template))
            input_as_names = {inp["as"] for inp in comp.get("inputs", [])}

            missing = placeholders - input_as_names
            assert not missing, \
                f"Component '{comp['name']}' prompt has placeholders {missing} not provided by inputs. " \
                f"Inputs provide: {input_as_names}"
