# GitLab Sentinel — Predict. Prevent. Protect.

> Predictive DevOps intelligence that catches pipeline failures, security risks,
> and delivery delays **BEFORE** they impact your team.

## What is Sentinel?

Sentinel is an autonomous multi-agent system built on **GitLab Duo Agent Platform**
that shifts DevOps from reactive firefighting to proactive prevention.

Unlike traditional tools that fix problems after they occur, Sentinel **predicts**
them before they happen.

## How It Works

```
MR Created / @mention trigger
        |
   Triage Agent ──── Rapid risk classification (pipeline/security/delivery)
        |
   Pipeline Predictor ──── CI/CD failure prediction + prevention
        |
   Security Scanner ──── Proactive vulnerability detection + CWE refs
        |
   Reporter ──── Structured MR comment with actionable insights
```

## Quick Start

1. Enable the Sentinel agents and flow in your project (Automate menu)
2. Create or update a Merge Request
3. Mention `@ai-sentinel-main-gitlab-ai-hackathon` in an MR comment
4. Watch the predictive analysis report appear

## Agents

| Agent | Role | Trigger |
|-------|------|---------|
| **Sentinel Triage** | Rapid risk classification across 3 dimensions | Chat / @mention |
| **Sentinel Flow** | Full multi-agent predictive analysis pipeline | @mention in MR |

## Technology

- **Platform**: GitLab Duo Agent Platform (Custom Agents + Custom Flows)
- **AI Model**: Anthropic Claude (via GitLab Duo)
- **Cloud**: Google Cloud (Cloud Functions + BigQuery)
- **Design**: Green Agent principles (token efficiency, early termination)

## Sustainability Design

Sentinel is designed for minimal resource usage:
- **Early termination**: Low-risk MRs skip specialist agents
- **Prompt efficiency**: Triage uses compact prompts for fast classification
- **Incremental analysis**: Only analyzes changed files, not entire repo
- **Token reporting**: Every report includes resource usage metrics

## License

MIT License - see [LICENSE](LICENSE)

---

*Built for the GitLab AI Hackathon 2026 | Powered by GitLab Duo Agent Platform + Anthropic Claude*
