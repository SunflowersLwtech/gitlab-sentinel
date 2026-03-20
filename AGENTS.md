# GitLab Sentinel - Project Agent Configuration

## Overview
GitLab Sentinel is a predictive DevOps intelligence platform that uses multiple
specialized AI agents to predict and prevent pipeline failures, security risks,
and delivery delays BEFORE they happen.

## Architecture
- **Triage Agent**: Rapid risk classification across pipeline/security/delivery dimensions
- **Pipeline Predictor**: CI/CD failure prediction with preventive recommendations
- **Security Scanner**: Proactive vulnerability detection with CWE references
- **Reporter**: Structured MR comment generation with actionable insights

## Project Structure
- `agents/` - Standalone agent definitions
- `flows/` - Multi-agent flow orchestrations
- `skills/` - Reusable agent skills with slash commands
- `demo/` - Demo scenarios for testing

## Coding Standards
- YAML configurations for agent/flow definitions
- Structured JSON output from all analysis agents
- Markdown reports with emoji severity indicators

## Key Principles
1. PREDICTIVE over reactive - catch problems before they happen
2. Structured output - all agents produce parseable JSON
3. Actionable recommendations - every finding includes a fix suggestion
4. Minimal false negatives - when in doubt, flag the risk
