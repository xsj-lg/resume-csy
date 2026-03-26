# recruitment-system

招聘系统项目（基于 doc-driven-project-template 初始化）。用统一治理规则驱动需求、执行和发布闭环。

## 目标

- 先定义规则，再推进需求和代码。
- 让需求、执行状态、发布历史保持单一事实来源。
- 让 Agent/Codex 在任何新项目里都能按同一交付语言协作。

## 目录

- `VERSION`: 平台版本。
- `docs/00-governance`: 治理规则（唯一规则来源）。
- `docs/01-requirements`: 需求讨论、术语定义、已发布能力快照。
- `docs/02-roadmap`: 执行清单与发布历史。
- `templates/`: 与 Codex 协作时可直接复用的交互模板。

## 使用方式

1. 本目录已完成初始化，可直接按治理流程推进需求和实现。
2. 如需再复制到其他项目，请替换文档中的 `<PROJECT_NAME>` 占位符。
3. 先阅读 `docs/docs-index.md` 和 `docs/00-governance/*`。
4. 从 `docs/01-requirements/req-00-draft.md` 录入需求，再平移到 `docs/02-roadmap/roadmap-00-todolist.md` 执行。
5. 发布后归档到 `docs/02-roadmap/roadmap-01-task-history.md`，并回填 `req-01` 与 `req-02`。

## 最小治理闭环

- 需求讨论: `req-00`
- 进入执行: `roadmap-00`
- 发布归档: `roadmap-01`
- 术语与能力回填: `req-01` + `req-02`

## 简历筛选系统（v0.1.1 已发布）

`REQ-v0.1.1-002` 已提供首版可运行实现：

- 后端：`app/server.py`（内置 HTTP 服务 + SQLite 持久化）
- 前端：`web/index.html` + `web/app.js` + `web/styles.css`
- 数据源：`data/cv/ais/20260228/*.pdf`
- SQLite：`data/recruitment.sqlite3`（运行时自动创建）

启动方式：

```bash
# 一键后台启动（推荐）
bash scripts/resume_app_up.sh

# 前台直接启动
python3 app/server.py
```

默认访问：

- `http://127.0.0.1:8080`
