"""
Prompt Quality & Best Practice Tests

Checks that prompts follow industry best practices for agent prompting:
- Claude XML structuring
- Output format specification
- Role definition clarity
- Instruction specificity
Run with: pytest tests/test_prompt_quality.py -v
"""

import re
import pytest


class TestPromptStructure:
    """Check prompts follow Claude-optimized XML structuring patterns."""

    def test_system_has_role_definition(self, flow_prompts):
        """Best practice: every system prompt should define the agent's role."""
        for prompt in flow_prompts:
            system = prompt.get("prompt_template", {}).get("system", "")
            has_role = any(marker in system.lower() for marker in [
                "<role>", "you are", "your role", "act as", "you're the"
            ])
            assert has_role, \
                f"Prompt '{prompt['prompt_id']}' missing role definition in system prompt"

    def test_system_has_output_format(self, flow_prompts):
        """Agents should know what format to output (JSON, Markdown, etc.)."""
        for prompt in flow_prompts:
            system = prompt.get("prompt_template", {}).get("system", "")
            has_format = any(marker in system.lower() for marker in [
                "<output_format>", "respond with json", "output format",
                "return a json", "json:", "format:", "markdown report",
                "respond with only this json", "<report_template>",
            ])
            assert has_format, \
                f"Prompt '{prompt['prompt_id']}' missing output format specification"

    def test_system_not_too_short(self, flow_prompts):
        """System prompts should be substantial enough for good agent behavior."""
        for prompt in flow_prompts:
            system = prompt.get("prompt_template", {}).get("system", "")
            min_len = 100 if "reporter" in prompt["prompt_id"] else 200
            assert len(system) >= min_len, \
                f"Prompt '{prompt['prompt_id']}' system prompt too short ({len(system)} chars, min {min_len})"

    def test_system_not_too_long(self, flow_prompts):
        """Extremely long prompts waste tokens and cause agent confusion."""
        for prompt in flow_prompts:
            system = prompt.get("prompt_template", {}).get("system", "")
            assert len(system) <= 5000, \
                f"Prompt '{prompt['prompt_id']}' system prompt too long ({len(system)} chars). " \
                "Consider condensing — long prompts cause agent over-exploration."

    def test_user_template_has_placeholders(self, flow_prompts):
        """User templates should use {{variables}} to inject dynamic context."""
        for prompt in flow_prompts:
            user = prompt.get("prompt_template", {}).get("user", "")
            placeholders = re.findall(r'\{\{(\w+)\}\}', user)
            assert len(placeholders) >= 1, \
                f"Prompt '{prompt['prompt_id']}' user template has no {{{{placeholders}}}}"


class TestPromptSafety:
    """Check prompts don't have known anti-patterns."""

    def test_no_hardcoded_credentials(self, flow_prompts):
        """Prompts should never contain API keys, tokens, or passwords."""
        patterns = [
            r'sk-[a-zA-Z0-9]{20,}',
            r'glpat-[a-zA-Z0-9_\-]+',
            r'ghp_[a-zA-Z0-9]+',
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
        ]
        for prompt in flow_prompts:
            full_text = str(prompt)
            for pattern in patterns:
                assert not re.search(pattern, full_text, re.IGNORECASE), \
                    f"Prompt '{prompt['prompt_id']}' contains potential credentials matching: {pattern}"

    def test_no_prompt_injection_vectors(self, flow_prompts):
        """Check for common prompt injection vulnerabilities."""
        dangerous = [
            "ignore previous instructions",
            "disregard all prior",
            "system prompt:",
            "you are now",
        ]
        for prompt in flow_prompts:
            system = prompt.get("prompt_template", {}).get("system", "").lower()
            for phrase in dangerous:
                assert phrase not in system, \
                    f"Prompt '{prompt['prompt_id']}' contains suspicious phrase: '{phrase}'"


class TestPromptEfficiency:
    """Check prompts are optimized for token efficiency (Green Agent Prize)."""

    def test_no_excessive_repetition(self, flow_prompts):
        """Prompts shouldn't repeat the same instruction multiple times."""
        for prompt in flow_prompts:
            system = prompt.get("prompt_template", {}).get("system", "")
            sentences = [s.strip().lower() for s in system.split('.') if len(s.strip()) > 20]
            seen = set()
            duplicates = []
            for s in sentences:
                if s in seen:
                    duplicates.append(s)
                seen.add(s)
            assert not duplicates, \
                f"Prompt '{prompt['prompt_id']}' has repeated sentences: {duplicates[:2]}"

    def test_has_tool_budget(self, flow_prompts):
        """Prompts should specify tool call limits for efficiency."""
        for prompt in flow_prompts:
            system = prompt.get("prompt_template", {}).get("system", "")
            has_budget = any(marker in system.lower() for marker in [
                "tool_budget", "maximum", "tool calls", "≤"
            ])
            assert has_budget, \
                f"Prompt '{prompt['prompt_id']}' missing tool call budget constraint"

    def test_has_immediate_answer_directive(self, flow_prompts):
        """Prompts should tell agents to answer immediately after analysis."""
        for prompt in flow_prompts:
            system = prompt.get("prompt_template", {}).get("system", "")
            has_directive = any(marker in system.lower() for marker in [
                "immediately", "final answer", "stop calling tools"
            ])
            assert has_directive, \
                f"Prompt '{prompt['prompt_id']}' missing 'answer immediately' directive"


class TestEvalScenarioIntegrity:
    """Test that eval scenarios are well-formed."""

    def test_scenario_has_required_fields(self, eval_scenario):
        for field in ("id", "name", "description", "expected", "pass_criteria"):
            assert field in eval_scenario, f"Scenario missing field: {field}"

    def test_scenario_has_expected_outputs(self, eval_scenario):
        expected = eval_scenario["expected"]
        # With 2-agent architecture, expect analyzer and/or triage sections
        agent_sections = [k for k in expected.keys() if k in (
            "triage", "pipeline_predictor", "security_scanner", "reporter", "analyzer"
        )]
        assert len(agent_sections) >= 1, f"Scenario {eval_scenario['id']} has no agent expected outputs"

    def test_scenario_pass_criteria_non_empty(self, eval_scenario):
        criteria = eval_scenario["pass_criteria"]
        assert len(criteria) >= 1, f"Scenario {eval_scenario['id']} has no pass criteria"
