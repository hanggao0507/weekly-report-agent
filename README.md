# Weekly Report Agent

一个基于 `Python + FastAPI + Jinja2/HTMX + LangGraph` 的每周工作周报助手。它可以在每周五 17:00 自动生成团队周报，也支持从页面点击“立即生成”，输出 Markdown 周报和可直接查看的 HTML 结果页。

当前 v1 使用 `GitHub Mock` 与 `飞书 Mock` 数据，目标是先把完整链路跑通：配置加载、数据采集、成员归因、Agent 汇总、结果渲染、下载导出、定时调度与测试验证。

## 功能概览

- 支持 YAML / JSON 配置
- 支持定时生成与页面立即生成
- 支持 GitHub Mock 数据：`commit / PR / issue`
- 支持飞书 Mock 数据：`calendar / message`
- 输出团队总览 + 成员明细的 Markdown 周报
- Web 页面直接渲染最终周报并支持下载 Markdown / HTML
- 使用 SQLite 记录运行状态与产物索引
- 提供 CLI、脚本与自动化测试

## 项目结构

```text
weekly-report-agent/
├── README.md
├── requirements.txt
├── config/
│   ├── example.yaml
│   └── mock/
│       ├── github/
│       ├── feishu/
│       └── team_members.json
├── src/
├── web/
├── docs/
├── tests/
└── scripts/
```

## 快速启动

### 1. 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. 启动服务

```powershell
$env:WEEKLY_REPORT_CONFIG = ".\config\example.yaml"
.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

打开 [http://127.0.0.1:8000](http://127.0.0.1:8000) 即可查看结果页并手动触发周报生成。

### 3. 使用 CLI 立即生成

```powershell
.\.venv\Scripts\python.exe -m src.cli.generate --config .\config\example.yaml --trigger manual
```

## 配置说明

默认样例配置位于 [config/example.yaml](/C:/Users/ah/Documents/New%20project/weekly-report-agent/config/example.yaml)。

| 字段 | 说明 |
| --- | --- |
| `schedule.cron` | 定时生成表达式，默认 `0 17 * * 5` |
| `schedule.timezone` | 调度时区 |
| `team.name` | 团队名称 |
| `team.members_file` | 成员映射文件路径 |
| `sources.github.mode` | 数据源模式，v1 默认 `mock` |
| `sources.github.mock_data_dir` | GitHub Mock 数据目录 |
| `sources.github.repos` | 展示和筛选的仓库列表 |
| `sources.feishu.mode` | 数据源模式，v1 默认 `mock` |
| `sources.feishu.fixture_paths.calendar` | 飞书日程 Mock 文件 |
| `sources.feishu.fixture_paths.messages` | 飞书消息 Mock 文件 |
| `report.template` | Markdown 模板名称 |
| `report.sections` | 生成周报包含的章节 |
| `report.output_dir` | 产物输出目录 |
| `report.window_days` | 周报时间窗口天数 |
| `report.export_formats` | 导出格式 |
| `llm.mode` | `mock` 或 `real` |
| `llm.provider` | `rule-based` 或真实模型提供方标识 |
| `llm.model` | Mock 模式下仅作占位，真实模式下为 OpenAI 模型名 |
| `llm.api_key_env` | 真实 LLM 模式读取的 API Key 环境变量名 |
| `llm.base_url` | 真实 LLM 请求使用的 OpenAI 兼容网关地址 |
| `llm.timeout_seconds` | 真实 LLM 调用超时时间 |
| `llm.max_retries` | 真实 LLM 请求失败时的 SDK 重试次数 |
| `llm.fallback_to_mock` | 真实 LLM 调用失败时是否自动退回规则汇总 |
| `llm.prompt_template` | LLM 汇总使用的 Prompt 模板文件路径 |
| `app.db_path` | SQLite 文件路径 |
| `app.host` / `app.port` | Web 启动地址 |

## Mock 数据说明

### GitHub Mock

GitHub Mock 数据位于 `config/mock/github/`：

- `commits.json`
- `pulls.json`
- `issues.json`

字段设计尽量贴近真实 GitHub API，例如：

- `author_login`
- `author_email`
- `state`
- `merged_at`
- `html_url`
- `labels`

### 飞书 Mock

飞书 Mock 数据位于 `config/mock/feishu/`：

- `calendar.json`
- `messages.json`

字段保留了真实接入所需语义，例如：

- `event_title`
- `attendees`
- `message_text`
- `risk_hint`
- `next_plan_hint`

## 真实接入替换说明

当前版本为了保证项目能开箱演示，`GitHub` 与 `飞书` 都使用 Mock 数据。

### GitHub 真实接入应如何替换

需要替换 `src/adapters/github_mock.py` 中的 `GitHubMockAdapter`，改为真实 API 适配器，例如：

- GitHub REST API
- GitHub GraphQL API

建议保留相同的标准化输出结构 `NormalizedWorkItem`，这样无需改动后续聚合、汇总和渲染流程。推荐新增配置项：

- `sources.github.token_env`
- `sources.github.base_url`
- `sources.github.org`
- `sources.github.repos`
- `sources.github.request_timeout`

鉴权方式建议使用：

- 个人访问令牌 `GITHUB_TOKEN`
- GitHub App 安装令牌

### 飞书真实接入应如何替换

需要替换 `src/adapters/feishu_mock.py` 中的 `FeishuMockAdapter`，改为真实飞书开放平台 API 适配器，例如：

- Calendar API
- IM Message API

建议新增配置项：

- `sources.feishu.app_id_env`
- `sources.feishu.app_secret_env`
- `sources.feishu.calendar_id`
- `sources.feishu.user_scope`

同样建议保留 `NormalizedWorkItem` 输出，避免影响 Agent 工作流和页面展示层。

## LLM 汇总模式

当前项目支持两种汇总模式：

### 1. Mock / 规则汇总

默认配置：

```yaml
llm:
  mode: "mock"
  provider: "rule-based"
```

这种模式不会调用真实大模型，而是用规则把标准化工作项归纳到：

- 本周完成
- 进行中
- 风险 / 阻塞
- 下周计划

对应实现位于：

- `src/services/summarizer.py` 中的 `RuleBasedSummarizer`

### 2. Real / OpenAI 汇总

如果需要启用真实模型汇总，可以把配置改为：

```yaml
llm:
  mode: "real"
  provider: "openai"
  model: "gpt-5.4"
  temperature: 0.2
  api_key_env: "OPENAI_API_KEY"
  base_url: "https://xxxx"
  timeout_seconds: 30.0
  max_retries: 2
  fallback_to_mock: true
  prompt_template: "./src/templates/prompts/weekly_report_summary.txt"
```

并在环境变量中提供：

```powershell
$env:OPENAI_API_KEY = "your-api-key"
```

真实模式下会：

1. 先完成时间窗口解析、数据源过滤、成员归因和团队聚合
2. 将标准化后的成员工作项序列化为 JSON
3. 调用 OpenAI Responses API
4. 要求模型返回固定 JSON 结构
5. 再映射回 `TeamWeeklyReport`

对应实现位于：

- `src/services/summarizer.py` 中的 `LLMSummarizer`

如果 `llm.mode=real` 但没有提供 API Key，系统会直接报错，而不是静默退回 mock。

## 如何切换汇总模式

### 切换到 Mock 模式

适合本地演示、离线开发和稳定测试。

1. 打开 [config/example.yaml](/C:/Users/ah/Documents/New%20project/weekly-report-agent/config/example.yaml)
2. 确认配置如下：

```yaml
llm:
  mode: "mock"
  provider: "rule-based"
  model: "weekly-report-template"
  temperature: 0.0
  api_key_env: "OPENAI_API_KEY"
```

3. 直接启动服务或运行 CLI，无需额外环境变量

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

或：

```powershell
.\.venv\Scripts\python.exe -m src.cli.generate --config .\config\example.yaml --trigger manual
```

### 切换到 Real / OpenAI 模式

适合你要验证真实模型总结效果时使用。

1. 打开 [config/example.yaml](/C:/Users/ah/Documents/New%20project/weekly-report-agent/config/example.yaml)
2. 把 `llm` 段改成下面这样：

```yaml
llm:
  mode: "real"
  provider: "openai"
  model: "gpt-4.1"
  temperature: 0.2
  api_key_env: "OPENAI_API_KEY"
```

3. 在启动前设置 API Key：

```powershell
$env:OPENAI_API_KEY = "your-api-key"
```

4. 再启动服务或运行 CLI：

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

或：

```powershell
.\.venv\Scripts\python.exe -m src.cli.generate --config .\config\example.yaml --trigger manual
```

如果你使用的是 OpenAI 兼容网关，例如：

- `base_url = "https://xxx"`
- `wire_api = "responses"`
- `model = "gpt-5.4"`

那么当前项目已经可以直接通过 `llm.base_url` 对接，不需要再手改 Python 代码。

### 切换后的行为差异

| 模式 | 是否调用真实模型 | 适用场景 | 失败行为 |
| --- | --- | --- | --- |
| `mock` | 否 | 本地联调、测试、演示 | 不依赖外部 API |
| `real` | 是 | 体验真实总结效果 | 缺少 `OPENAI_API_KEY` 会直接报错；若开启 `fallback_to_mock`，模型调用失败时会退回规则汇总 |

### 推荐切换方式

- 日常开发：保持 `mock`
- 做真实效果验证：临时切到 `real`
- 跑自动化测试：保持 `mock`

### 常见问题

#### 1. 改成 `real` 以后为什么报错？

通常是因为没有设置：

```powershell
$env:OPENAI_API_KEY = "your-api-key"
```

或者 `api_key_env` 和你实际设置的环境变量名不一致。

#### 2. 改成 `real` 后，数据源还是 Mock 吗？

是的。当前项目里：

- GitHub / 飞书数据源仍然是 Mock
- 只有“汇总生成周报”这一步会切换成真实模型

#### 3. 想切回 Mock 怎么做？

把 `config/example.yaml` 中的：

```yaml
llm:
  mode: "real"
```

改回：

```yaml
llm:
  mode: "mock"
```

然后重启服务即可。

### 真实模式增强能力

当前 `LLMSummarizer` 已支持：

- OpenAI SDK 超时控制：`llm.timeout_seconds`
- OpenAI SDK 重试：`llm.max_retries`
- 模型失败后自动回退规则汇总：`llm.fallback_to_mock`
- Prompt 抽到独立模板文件：
  - [src/templates/prompts/weekly_report_summary.txt](/C:/Users/ah/Documents/New%20project/weekly-report-agent/src/templates/prompts/weekly_report_summary.txt)

如果你要调优真实模型总结效果，建议优先改这个 Prompt 模板，而不是直接修改 Python 代码。

## 运行方式

### Web UI 手动触发

- 打开首页
- 点击“立即生成”
- 页面将轮询任务状态
- 完成后可进入结果详情并下载 Markdown / HTML

### 定时触发

系统会在 FastAPI 启动时注册 APScheduler 任务，默认使用：

```yaml
schedule:
  cron: "0 17 * * 5"
  timezone: "Asia/Shanghai"
```

## 测试

### 运行全部测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### 运行集成测试

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration -q
```

### 测试覆盖重点

- 配置解析与路径解析
- GitHub / 飞书 Mock 适配器标准化
- 成员归因和未归因分组
- 团队汇总与四段式周报生成
- 页面触发、状态轮询、详情页与下载接口

## 脚本说明

- [scripts/run_dev.ps1](/C:/Users/ah/Documents/New%20project/weekly-report-agent/scripts/run_dev.ps1)：本地开发启动
- [scripts/generate_demo_report.ps1](/C:/Users/ah/Documents/New%20project/weekly-report-agent/scripts/generate_demo_report.ps1)：命令行生成演示周报
- [scripts/test_all.ps1](/C:/Users/ah/Documents/New%20project/weekly-report-agent/scripts/test_all.ps1)：执行测试

## 设计文档

详细设计见 [docs/design.md](/C:/Users/ah/Documents/New%20project/weekly-report-agent/docs/design.md)。
