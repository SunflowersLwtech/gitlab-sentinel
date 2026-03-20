---
name: predict-pipeline
description: Predict CI/CD pipeline failures before they happen by analyzing code changes, dependencies, and CI configuration
metadata:
  slash-command: enabled
---

## Predict Pipeline Skill

When invoked, analyze the current merge request or branch changes to predict
potential CI/CD pipeline failures.

### Steps
1. Read .gitlab-ci.yml and all included CI config files
2. Analyze the diff for dependency, build, test, and integration changes
3. Cross-reference with recent pipeline history if available
4. Generate a prediction report with confidence scores

### Output
Provide a structured prediction with:
- Pass/Fail prediction with confidence percentage
- Specific failure points identified
- Preventive actions recommended
- Auto-fix suggestions where applicable
