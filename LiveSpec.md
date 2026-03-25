# GitLab Sentinel — LiveSpec

> **本文件是项目的单一真相来源 (Single Source of Truth)**
> 每次任务完成后评估是否需要更新本文件
> 新 agent 接手时只需读这个文件即可获得完整上下文

---

## 1. 产品定义

**名称**: GitLab Sentinel: Predictive DevOps Intelligence
**一句话**: 当开发者提交 MR 时，自动预测 pipeline 失败、安全漏洞、交付风险，在问题发生前贴出分析报告。
**差异化**: 预测式 (Prediction) vs 反应式 (Reaction) — 历届获奖者全是故障后修复，我们是故障前预防。

**比赛**: GitLab AI Hackathon 2026 ($65K 总奖金)
**截止**: 2026-03-25 14:00 EDT
**目标奖项**: Grand Prize ($15K) + Anthropic ($10K, 自动合格) + Google Cloud ($10K) + Green Agent ($3K)

---

## 2. 仓库信息

| 项目 | 值 |
|------|-----|
| GitLab | `gitlab.com/gitlab-ai-hackathon/participants/34674168` |
| GitHub (镜像) | `github.com/SunflowersLwtech/gitlab-sentinel` |
| 本地路径 | `/Users/sunfl/Documents/study/GitLabAI/gitlab-sentinel` |
| 开发文档 | `/Users/sunfl/Documents/study/GitLabAI/dev/docs/` |
| 参考资料 | `/Users/sunfl/Documents/study/GitLabAI/reference/` |
| Git identity | `LIUWEI / weiliu0607@gmail.com / gpgsign=false` |
| 双推送 | `git push origin main` 同时推 GitLab + GitHub |
| 分支规范 | 禁止 `claude` 出现在分支名、贡献者名单中 |

---

## 3. 账号与凭证

| 项目 | 值 |
|------|-----|
| Devpost | weiliu0607 |
| GitLab | weiliu0607 (User ID: 34674168) |
| GitLab PAT | `glpat-zsnFa8_...` (在 `.env` 中) |
| GitHub | SunflowersLwtech |
| Default Duo Namespace | GitLab AI Hackathon ✅ |
| Ultimate Trial | 30 天已激活 ✅ |
| GCP (有计费) | `project-349f30a3-7c3e-46dd-b95` |
| GCP (BigQuery) | `gitlab-490819` |
| BigQuery table | `gitlab-490819:sentinel_data.predictions` |
| Flow service account | `@ai-sentinel-predictive-analysis-gitlab-ai-hackathon` |

---

## 4. 当前项目文件

```
gitlab-sentinel/
├── agents/
│   ├── sentinel_triage.yml       # 独立 Agent (name/description/public/system_prompt/tools)
│   └── agent.yml.template        # 官方模板 (保留)
├── flows/
│   ├── sentinel_main.yml         # 4-agent Flow (name/description/public/definition:{v1 YAML})
│   └── flow.yml.template         # 官方模板 (保留)
├── skills/
│   └── predict-pipeline/SKILL.md # Slash command /predict-pipeline
├── eval/                         # Evaluation Framework
│   ├── README.md                 # Eval 使用说明
│   ├── metrics.py                # 行业标准指标 (pass@k, trajectory, detection rate)
│   ├── evaluate.py               # 评估运行器 (CLI: python eval/evaluate.py)
│   ├── scenarios/                # 4 个 benchmark 场景定义 (ground truth)
│   │   ├── scenario_a_security.json    # hardcoded key + SQL injection
│   │   ├── scenario_b_pipeline.json    # flask/werkzeug 依赖冲突
│   │   ├── scenario_c_delivery.json    # 15+ files 高复杂度变更
│   │   └── scenario_d_false_positive.json # README 改一行 (全绿)
│   └── results/                  # 执行结果 (gitignored)
├── tests/                        # pytest 测试套件 (70 tests, 0.18s)
│   ├── conftest.py               # 共享 fixtures
│   ├── test_yaml_validation.py   # Flow/Agent YAML 结构验证 (hackathon 约束)
│   ├── test_output_schemas.py    # Agent 输出 JSON schema 验证
│   ├── test_flow_integrity.py    # Flow 路由 + 数据接线完整性
│   └── test_prompt_quality.py    # Prompt 质量 + 安全性 + 效率检查
├── AGENTS.md                     # 项目级 agent 上下文
├── README.md                     # 项目文档
├── LICENSE                       # MIT
└── LiveSpec.md                   # 本文件
```

---

## 5. 已验证的技术约束

### 5.1 Hackathon 验证器规则

| 规则 | 详情 |
|------|------|
| **只能用 AgentComponent** | DeterministicStepComponent / OneOffComponent 被验证器拒绝 |
| **Agent YAML 格式** | `name / description / public: true / system_prompt / tools` |
| **Flow YAML 格式** | `name / description / public: true / definition: { version: v1, ... }` |
| **unit_primitives** | 用 `[]` 空列表 |
| **Tags 不能删除** | 受保护，只能创建新版本号 |

### 5.2 Custom Flow 禁止字段

| 禁止字段 | 位置 |
|----------|------|
| `name, description, product_group` | definition 内部 |
| `model` | prompts 内 |
| `response_schema_id / version` | components 内 |
| `ui_role_as`, `stop` | components/params 内 |
| `environment: chat / chat-partial` | 只能 `ambient` |

### 5.3 Input 黄金规则 (Issue #591567)

```yaml
# ✅ 必须用 from/as 对象
inputs:
  - from: "context:goal"
    as: "user_request"
  - from: "context:project_id"    # 几乎必须包含
    as: "project_id"
# ❌ 字符串格式导致 WebSocket 断开
```

### 5.4 Hackathon sandbox 限制

- 模型锁定 Anthropic Claude，不可更改
- 所有组件共享同一模型 (Group Settings 决定)
- 不能在 YAML 中指定 model

---

## 6. 首次执行测试结果 (2026-03-20)

### MR !3: hardcoded API key + SQL injection

| Agent | 状态 | 输出质量 |
|-------|------|----------|
| triage_agent | ✅ | 正确识别 3 维风险 |
| pipeline_predictor | ✅ | **A+** 7 个 predicted_failures, score 15/100 |
| security_scanner | ⚠️ | 误判: 说 test_app.py 不存在 (扫描了 main 而非 MR 分支) |
| reporter | ❌ | WebSocket 断连 (code 1006), 报告未发出 |

### 根因

1. **WebSocket 超时**: 4 agent 串联 ~10 min 太长
2. **Security Scanner**: grep 整个仓库而非读 MR diff
3. **Agent 过度探索**: 153 次 tool call, 大量无意义 grep

### 修复方向

1. 减少 Agent 到 2-3 个或精简 prompt
2. 让 security_scanner 从 triage 结果读文件列表
3. Prompt 加 "完成后立即给最终答案"
4. 每 agent 工具数 ≤ 4

---

## 7. Benchmark 场景

| ID | 场景 | 预期检出 |
|----|------|---------|
| A | hardcoded key + SQL injection | security >= 8, 2 critical |
| B | flask 3.x vs werkzeug 2.x | pipeline "likely_fail" |
| C | 15+ files 无测试 | delivery >= 7 |
| D | README 改一行 | overall "low" |

---

## 8. 测试基础设施

### 8.1 离线测试 (pytest, 70 tests, 0.18s)

```bash
cd gitlab-sentinel && python -m pytest tests/ -v
```

| 测试文件 | 测试数 | 覆盖内容 |
|----------|--------|---------|
| `test_yaml_validation.py` | 26 | Hackathon 验证器约束、禁止字段、from/as 格式、工具白名单 |
| `test_output_schemas.py` | 10 | Agent 输出 JSON schema (triage/pipeline/security) |
| `test_flow_integrity.py` | 7 | 路由可达性、数据接线、Reporter 输入完整性 |
| `test_prompt_quality.py` | 27 | Role 定义、输出格式、安全性、效率、Eval 场景完整性 |

**TDD 工作流**: 修改 YAML/prompt → `pytest tests/` → 全绿再 push

### 8.2 Eval 框架 (行业标准指标)

```bash
python eval/evaluate.py eval/results/scenario_a_run1.json    # 单次评估
python eval/evaluate.py --all eval/results/                    # 批量评估 + pass@k 统计
```

| 指标 | 来源 | 描述 |
|------|------|------|
| **pass@k** | AWS DevOps Agent | k 次中至少 1 次通过 |
| **pass^k** | AWS DevOps Agent | k 次中通过率 (reliability) |
| **detection_completeness** | 自定义 | 必需漏洞检出率 |
| **false_positive_rate** | 自定义 | 误报率 |
| **tool_trajectory** | Google ADK / LangChain AgentEvals | 工具调用序列评分 |
| **prediction_accuracy** | 自定义 | 预测结果匹配 |
| **keyword_presence** | 自定义 | 输出关键词覆盖 |
| **efficiency** | Green Agent Prize | tool_calls + latency + token_count |
| **report_posted** | 自定义 | Reporter 是否成功发出 MR 评论 |

### 8.3 Eval 工作流

```
1. 创建 test MR (注入特定问题)
2. @mention 触发 flow → 等待执行
3. 从 session 日志提取结果 → 保存为 eval/results/scenario_X_runN.json
4. python eval/evaluate.py → 得到 PASS/FAIL + 分数
5. 修改 prompt → pytest tests/ → 重新触发
6. 重复至所有 scenario 达标
```

---

## 9. 竞争情报

- 竞争者 `gitlab-security-sentinel` 存在 — 用全名区分
- 历届获奖者全用 Gemini → Anthropic $10K 竞争少
- Security 方向拥挤 (12+) — predictive 角度差异化
- 89 个官方工具: `reference/resources/tool_mapping.json`

---

## 10. 开发流程

```
编辑 → commit (LIUWEI, no gpgsign) → push → CI 验证 → 创建 tag → 自动发布 → @mention 测试
```

### API

```bash
export GITLAB_PAT="glpat-zsnFa8_298TshNHb_dIn_mM6MQpvOjEKdTprbjZyYw8.01.171nzntzi"
export PROJECT_ID=80449087

# Pipeline
curl -s -H "PRIVATE-TOKEN: $GITLAB_PAT" "https://gitlab.com/api/v4/projects/$PROJECT_ID/pipelines?per_page=5"

# MR notes
curl -s -H "PRIVATE-TOKEN: $GITLAB_PAT" "https://gitlab.com/api/v4/projects/$PROJECT_ID/merge_requests/{iid}/notes"

# 触发 flow
curl -s -H "PRIVATE-TOKEN: $GITLAB_PAT" -X POST \
  "https://gitlab.com/api/v4/projects/$PROJECT_ID/merge_requests/{iid}/notes" \
  -d "body=@ai-sentinel-predictive-analysis-gitlab-ai-hackathon analyze this"
```

---

## 11. 下一步优先级

```
P0: 修复 3 个问题 (超时 / security scanner 误判 / reporter 断连)
P1: 跑 4 个 benchmark, 建立质量基线
P2: 迭代 prompt 直到 benchmark 达标
P3: 构建 demo 场景 + 录制 3 分钟视频
P4: GCP 集成 (Cloud Function webhook)
P5: Devpost 提交
```

---

## 12. 文件索引

| 文件 | 内容 |
|------|------|
| `LiveSpec.md` | **本文件** |
| `dev/docs/STATUS.md` | 项目状态总览 |
| `dev/docs/testing-plan.md` | 测试 + benchmark |
| `dev/docs/blocker-prevention-master.md` | 阻塞预防 (v2) |
| `dev/docs/template-format-discovery.md` | 模板格式发现 |
| `dev/docs/known-issues-platform.md` | 30+ 平台问题 |
| `reference/strategy/winning_blueprint.md` | 冠军蓝图 (1958行) |
| `reference/gitlab-platform/technical_analysis.md` | 平台技术 (1404行) |
| `reference/resources/tool_mapping.json` | 89 个官方工具 |

---

*Last updated: 2026-03-21 — Added test infra (§8): 70 pytest tests + eval framework with 4 scenarios*
*Update after every significant task completion*