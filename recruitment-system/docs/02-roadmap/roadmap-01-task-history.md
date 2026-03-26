# Task History

## 1. 文档信息

- 当前版本: `0.1.15`
- 对应平台版本: `0.1.15`
- 作用: 记录已发布版本的历史任务与需求完成事实（唯一历史事实源）。

### 最近更新（最新 5 条）

| date | version | 对应平台版本 | summary |
| --- | --- | --- | --- |
| `2026-03-26` | `0.1.15` | `0.1.15` | 1. 补录已发布需求 `REQ-v0.1.15-001`：新增操作记录页面并完成统一日志留痕、详情比对与导出能力。<br>2. 补录已发布需求 `REQ-v0.1.15-002`：工作台支持记住并恢复上次查看的候选人/简历记录。<br>3. 补录已发布需求 `REQ-v0.1.15-003`：自动评分结果按评分项累加校验总分，并在工作台展示完整评分项明细。<br>4. 补录已发布需求 `REQ-v0.1.15-004`：上传评分表解析支持“维度标题行 + 评分项行 + 续行标准”的分段结构。<br>5. 补录已发布需求 `REQ-v0.1.15-005`：协作治理新增执行前强制重读 `docs/00-governance/` 与 `project-docs` 同步要求，并明确用户确认“已发布完成”后必须同步完成状态迁移。 |
| `2026-03-24` | `0.1.14` | `0.1.14` | 1. 归档 `REQ-v0.1.14-001/002` 并发布 `v0.1.14`。<br>2. 发布后已回填 `req-01/req-02`。<br>3. 归档完成后已切换 `req-00/roadmap-00` 至下一目标版本 `0.1.15`。 |
| `2026-03-24` | `0.1.13` | `0.1.13` | 1. 归档 `REQ-v0.1.13-002/003` 并补齐 `v0.1.13` 发布事实。<br>2. 补全 `v0.1.9/v0.1.10/v0.1.11` 历史归档，统一旧版本状态为 `DONE/RELEASED`。<br>3. 发布后回填记录已与 `req-01/req-02` 对齐。 |
| `2026-03-18` | `0.1.12` | `0.1.12` | 1. 归档 `REQ-v0.1.12-001` 并发布 `v0.1.12`。<br>2. 归档 `REQ-v0.1.12-002`（后端分层拆分）并完成 `req-01/req-02` 回填。 |
| `2026-03-17` | `0.1.11` | `0.1.11` | 1. 归档 `REQ-v0.1.11-001/002` 并补齐 `v0.1.11` 发布事实。<br>2. 发布后回填记录已与 `req-01/req-02` 对齐。 |

## 2. Roadmap History

| roadmap_version | status | date | summary | refs |
| --- | --- | --- | --- | --- |
| `v0.1.15` | `RELEASED` | `2026-03-26` | 补录发布操作记录页面：新增管理员可见的操作记录页、统一日志记录表、日志详情/比对/导出与关键链路留痕；补录发布工作台最近查看恢复：跨页返回时自动恢复上次查看候选人与简历上下文；补录发布自动评分明细增强：总分按评分项重算并完整展示维度下评分项；补录发布评分表分段结构解析增强与协作治理增强。 | `web/operations.html`, `web/operations.js`, `web/app.js`, `app/backend/controllers/operation_log_controller.py`, `app/backend/services/operation_log_service.py`, `app/backend/services/auto_score_service.py`, `app/backend/controllers/auth_controller.py`, `app/backend/controllers/user_role_controller.py`, `app/backend/controllers/job_controller.py`, `app/backend/controllers/candidate_controller.py`, `docs/00-governance/gov-02-requirements.md`, `docs/00-governance/gov-03-agent-collaboration.md`, `project-docs/development/development-and-integration-guidelines.md`, `docs/01-requirements/*`, `docs/02-roadmap/*` |
| `v0.1.14` | `RELEASED` | `2026-03-24` | 发布自动评分输入收敛与候选人筛选增强能力：评分表去重规范化、结构化候选人信息优先入模、阈值参数一致性与严格 JSON 输出落地；候选人列表支持流程状态、学校、学历、年限、评分区间、上传日期筛选，并完成左栏筛选区/面试日历滚动优化。 | `web/index.html`, `web/app.js`, `web/styles.css`, `app/backend/controllers/candidate_controller.py`, `app/backend/services/candidate_service.py`, `app/backend/services/recruitment_service.py`, `docs/01-requirements/*`, `docs/02-roadmap/*`, `project-docs/api/api-documentation.md` |
| `v0.1.13` | `RELEASED` | `2026-03-19` | 发布岗位信息后端存储与评分表解析预览、简历结构化抽取与通用信息融合展示能力：岗位管理以后端持久化数据为事实源，评分表支持上传解析预览，候选人详情页统一按“通用信息”口径展示结构化抽取结果并保留抽取更新入口与状态提示。 | `web/index.html`, `web/app.js`, `web/jobs.html`, `web/jobs.js`, `app/backend/services/recruitment_service.py`, `docs/01-requirements/*`, `docs/02-roadmap/*` |
| `v0.1.12` | `RELEASED` | `2026-03-18` | 发布岗位管理能力：岗位全生命周期配置、评分表版本管理、简历上传岗位关联、AI 自动评分与手动重评、关键操作审计，并完成大模型配置外置读取；补充归档后端分层拆分能力：`app/server.py` 收敛为入口，后端按控制层/服务层/数据库交互层/工具层拆分。 | `web/jobs.html`, `web/jobs.js`, `web/app.js`, `web/index.html`, `app/server.py`, `app/backend/controllers/resume_controller.py`, `app/backend/services/recruitment_service.py`, `app/backend/repositories/sqlite_helpers.py`, `app/backend/utils/time_utils.py`, `config/llm-config.json`, `config/llm-prompts.json`, `docs/01-requirements/*`, `docs/02-roadmap/*` |
| `v0.1.11` | `RELEASED` | `2026-03-17` | 发布上传与筛选支持部门维度、PDF 核心信息识别能力：上传 PDF 时支持部门选择，候选人列表支持按部门筛选，管理员与 HR 可编辑候选人部门，并可自动提取学校、电话、邮箱写入通用信息且允许人工修正。 | `web/index.html`, `web/app.js`, `app/backend/services/recruitment_service.py`, `app/backend/controllers/resume_controller.py`, `docs/01-requirements/*`, `docs/02-roadmap/*` |
| `v0.1.10` | `RELEASED` | `2026-03-17` | 发布角色权限管理、部门范围与用户管理编辑能力：统一四类角色访问边界，新增部门范围枚举与权限过滤链路，用户编辑改为弹窗表单并支持显示名、启用状态、角色与部门范围联动校验。 | `web/users.html`, `web/users.js`, `web/app.js`, `app/server.py`, `docs/01-requirements/*`, `docs/02-roadmap/*` |
| `v0.1.9` | `RELEASED` | `2026-03-17` | 发布角色定义基础能力：后端提供四类角色编码与角色定义数据，用户管理支持按角色编码创建/编辑用户，并开始生效管理员/HR/面试官/部门负责人的基础门禁与可见范围控制。 | `web/users.html`, `web/users.js`, `web/app.js`, `app/server.py`, `docs/01-requirements/*`, `docs/02-roadmap/*` |
| `v0.1.8` | `RELEASED` | `2026-03-17` | 发布候选人列表筛选能力（名称模糊、岗位精确/模糊与组合筛选），并完成左栏排版优化（排序方式下拉、筛选与日历可收起）。 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `docs/01-requirements/*`, `docs/02-roadmap/*` |
| `v0.1.7` | `RELEASED` | `2026-03-16` | 发布面试流程“初筛”阶段扩展，支持 `待初筛` 与 `未通过X` 状态细分，并联动阶段按钮文案和左侧状态展示。 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `docs/01-requirements/*`, `docs/02-roadmap/*` |
| `v0.1.6` | `RELEASED` | `2026-03-11` | 发布简历流入日期能力（日粒度存储/迁移回填/回显），发布前端批量上传与结果汇总，发布左侧候选人流入日期标签显示。 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `docs/01-requirements/*`, `docs/02-roadmap/*` |
| `v0.1.5` | `RELEASED` | `2026-03-11` | 发布简历导入升级（上传、UUID 映射、按日期落盘、同名全局唯一拒绝），发布候选人删除联动本地文件删除与候选人名称编辑，发布本地目录手动同步能力。 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `docs/01-requirements/*`, `docs/02-roadmap/*` |
| `v0.1.4` | `RELEASED` | `2026-02-28` | 发布用户管理与登录能力（Cookie Session、默认管理员首登改密、仅管理员管理用户），并支持阶段面试人分配与回显。 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `web/login.html`, `web/login.js`, `web/users.html`, `web/users.js`, `docs/01-requirements/*`, `docs/02-roadmap/*` |
| `v0.1.3` | `RELEASED` | `2026-02-28` | 发布左侧候选人管理与面试日历增强版（5态状态标签、颜色语义、星标与排序、终止默认隐藏/显示全部、未来面试日历）。 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `docs/01-requirements/*`, `docs/02-roadmap/*` |
| `v0.1.2` | `RELEASED` | `2026-02-28` | 发布面试流程增强版（三节点独立状态、节点时间展示、阶段重置、阶段/通用信息分离保存、文档版本治理收敛）。 | `app/server.py`, `web/*`, `docs/00-governance/*`, `docs/01-requirements/*`, `docs/02-roadmap/*` |
| `v0.1.1` | `RELEASED` | `2026-02-28` | 发布简历筛选系统首版（候选人列表/PDF 预览/人工录入/SQLite、一键启动）。 | `app/server.py`, `web/*`, `scripts/resume_app_up.sh` |

## 3. 已完成任务明细（历史）

### v0.1.15（已发布补录）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.15-001` | `DONE` | 新增操作记录页面 | `web/operations.html`, `web/operations.js`, `app/backend/controllers/operation_log_controller.py`, `app/backend/services/operation_log_service.py`, `app/backend/controllers/auth_controller.py`, `app/backend/controllers/user_role_controller.py`, `app/backend/controllers/job_controller.py`, `app/backend/controllers/candidate_controller.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 系统级操作记录页面已可查询、筛选、查看详情、比对同对象上一条记录并导出结果；统一日志记录表与关键链路留痕已落地，不影响现有岗位级关键操作日志展示。 |
| `REQ-v0.1.15-002` | `DONE` | 工作台记住上次查看简历 | `web/app.js`, `web/index.html`, `project-docs/development/development-and-integration-guidelines.md`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 工作台可持久化并恢复上次查看的候选人/简历记录，返回工作台时可自动恢复详情区与预览区；候选人失效或不可见时可安全降级，不影响既有列表筛选、排序、星标与预览行为。 |
| `REQ-v0.1.15-003` | `DONE` | 自动评分总分校验与评分项明细展示 | `web/app.js`, `app/backend/services/auto_score_service.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 自动评分结果已按评分项得分重算维度分与总分，工作台可完整展示维度下全部评分项、判定依据、命中证据与置信度，且历史无明细记录可兼容查看。 |
| `REQ-v0.1.15-004` | `DONE` | 上传评分表解析补全维度下评分项 | `app/backend/services/score_table_service.py`, `app/backend/services/job_service.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 上传评分表支持“维度标题行 + 评分项行 + 续行标准”的分段结构解析；评分表预览与岗位评分项快照均能正确保留 `dimension/point/criterion/score` 归属，且平铺评分表解析行为保持兼容。 |
| `REQ-v0.1.15-005` | `DONE` | 治理补充执行前通读与 project-docs 同步规则 | `docs/00-governance/gov-03-agent-collaboration.md`, `project-docs/development/development-and-integration-guidelines.md`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 协作治理明确要求 Agent 每次执行前先读取 `docs/docs-index.md` 并完整重读 `docs/00-governance/`；涉及代码或文件变更时必须按映射规则同步更新对应 `project-docs` 描述，并在交付中声明同步结果。 |

### v0.1.14（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.14-001` | `DONE` | 结合简历结构化信息进行AI自动评分 | `web/app.js`, `app/backend/services/recruitment_service.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 自动评分输入完成评分表规范化去重、结构化候选人信息优先入模、阈值参数一致性与严格 JSON 输出，且不影响自动评分触发、手动重评、结果回显与审计日志链路。 |
| `REQ-v0.1.14-002` | `DONE` | 候选人筛选与左栏展示优化 | `web/index.html`, `web/app.js`, `web/styles.css`, `app/backend/controllers/candidate_controller.py`, `app/backend/services/candidate_service.py`, `project-docs/api/api-documentation.md`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 候选人列表支持流程状态、学校、学历、年限、评分区间、上传日期筛选，`filters/upload_dates` 返回与前端交互对齐，筛选面板与面试日历在多列布局下支持内部滚动。 |

### v0.1.13（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.13-002` | `DONE` | 岗位信息后端存储与评分表解析预览 | `web/jobs.html`, `web/jobs.js`, `web/index.html`, `web/app.js`, `app/server.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 岗位管理以后端持久化记录为事实源；评分表支持上传、服务端落盘、解析预览与已生效版本读取；LLM 不可用时可自动降级规则解析。 |
| `REQ-v0.1.13-003` | `DONE` | 简历结构化抽取与通用信息合并展示 | `web/index.html`, `web/app.js`, `app/backend/services/recruitment_service.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 候选人详情页统一通用信息展示口径，不再重复展示同口径结构化字段；“更新抽取”可同步刷新通用信息；历史无结构化数据与抽取失败场景保持可用并不影响保存、流程流转、自动评分和列表回显链路。 |

### v0.1.12（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.12-001` | `DONE` | 添加岗位管理功能 | `web/jobs.html`, `web/jobs.js`, `web/index.html`, `web/app.js`, `web/users.html`, `web/users.js`, `app/server.py`, `config/llm-config.json`, `config/llm-prompts.json`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 岗位生命周期管理、评分表版本管理、岗位关联上传、AI 自动评分与手动重评、评分结果回显及关键操作审计链路已打通；大模型配置已外置并支持只读查看。 |
| `REQ-v0.1.12-002` | `DONE` | 后端分层拆分 | `app/server.py`, `app/backend/controllers/resume_controller.py`, `app/backend/services/recruitment_service.py`, `app/backend/repositories/sqlite_helpers.py`, `app/backend/utils/time_utils.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 后端完成控制层/服务层/数据库交互层/工具层拆分，`app/server.py` 收敛为启动入口；`py_compile` 覆盖入口与分层文件校验通过。 |

### v0.1.10（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.10-001` | `DONE` | 添加角色权限管理 | `web/app.js`, `web/index.html`, `web/users.html`, `web/users.js`, `app/server.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 四类角色访问控制、数据可见范围与关键接口权限校验已落地；角色删除前关联校验与单主角色约束生效。 |
| `REQ-v0.1.10-002` | `DONE` | 添加部门范围 | `web/users.html`, `web/users.js`, `app/server.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 部门范围枚举、入参校验、持久化与部门负责人权限过滤链路已打通；创建/编辑用户可正确回显部门范围。 |
| `REQ-v0.1.10-003` | `DONE` | 用户管理编辑能力补齐 | `web/users.html`, `web/users.js`, `app/server.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 用户管理“编辑”支持显示名、启用/禁用状态、角色与部门范围编辑；角色为部门负责人时部门范围必填，非部门负责人时不生效；保存后列表即时回显并持久化。 |

### v0.1.11（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.11-001` | `DONE` | 上传与筛选支持部门维度 | `web/index.html`, `web/app.js`, `app/backend/services/recruitment_service.py`, `app/backend/controllers/resume_controller.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 上传 PDF 支持部门选择并持久化；候选人列表支持按部门筛选；部门负责人不显示部门筛选；管理员与 HR 可编辑候选人部门并即时回显。 |
| `REQ-v0.1.11-002` | `DONE` | PDF 核心信息识别 | `web/index.html`, `web/app.js`, `app/backend/services/recruitment_service.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | PDF 文本解析与学校/电话/邮箱识别链路已打通；识别失败不阻塞上传；候选人通用信息支持人工修正并持久化回显。 |

### v0.1.9（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.9-001` | `DONE` | 添加角色定义模块 | `web/users.html`, `web/users.js`, `web/app.js`, `app/server.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 四类角色编码、角色定义查询、用户角色录入/编辑及基础角色门禁链路已落地。 |

### v0.1.8（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.8-001` | `DONE` | 简历筛选（按候选人名称/岗位） | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 支持名称模糊筛选、岗位精确/模糊筛选与组合筛选；支持一键重置；筛选结果变化时候选人列表与总数实时更新；左栏支持排序方式下拉，筛选区与面试日历可展开/收起。 |

### v0.1.7（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.7-001` | `DONE` | 新增初筛阶段与未通过状态细分 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 面试阶段扩展为 `初筛/一面/二面/HR面`；候选人状态支持 `待初筛` 与 `未通过X`；`HR面` 下一阶段按钮显示 `通过面试`；结束按钮按当前阶段显示 `未通过X`；历史三阶段数据可兼容回读。 |

### v0.1.6（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.6-001` | `DONE` | 简历流入日期记录（日粒度） | `app/server.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | `candidate_files` 支持 `inflow_date` 持久化，上传/目录同步/历史迁移均可回填并回显。 |
| `REQ-v0.1.6-002` | `DONE` | 前端批量上传 PDF | `web/index.html`, `web/app.js`, `web/styles.css`, `app/server.py`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 上传弹框支持多文件提交，支持部分成功并返回成功/失败汇总，完成后刷新列表与日历。 |
| `REQ-v0.1.6-003` | `DONE` | 左侧候选人列表展示流入日标签 | `web/app.js`, `web/styles.css`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 左侧候选人标签区展示 `YYYY-MM-DD` 日期标签；无值回显 `未知`。 |

### v0.1.5（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.5-001` | `DONE` | 左栏上传 PDF + UUID 候选人映射改造 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 上传弹框可用、同名全局唯一拒绝、文件按日期目录落盘、候选人以 UUID 持久关联并可预览、历史数据迁移不丢失。 |
| `REQ-v0.1.5-002` | `DONE` | 上传简历删除能力与候选人名称可编辑 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 支持删除候选人并联动删除本地 PDF/候选人信息；通用信息可编辑候选人名称并持久化回显。 |
| `REQ-v0.1.5-003` | `DONE` | 手动同步本地目录简历 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 左栏可手动触发目录同步；新增 PDF 无需重启可入库并刷新展示；同步结果可见新增/扫描统计。 |

### v0.1.4（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.4-001` | `DONE` | 用户管理、登录与阶段面试人分配 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `web/login.html`, `web/login.js`, `web/users.html`, `web/users.js`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 登录与会话可用（Cookie Session），默认管理员首登强制改密、禁止注册、仅管理员可创建用户；阶段面试人可按阶段下拉选择并可保存回显。 |

### v0.1.3（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.3-001` | `DONE` | 左侧候选人管理与面试日历增强 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 左侧支持 5 态状态标签颜色、星标与排序、终止默认隐藏与显示全部；面试日历仅展示未来安排并按最近时间优先。 |

### v0.1.2（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.2-001` | `DONE` | 候选人列表标签与面试轮次信息增强 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `docs/01-requirements/req-00-draft.md`, `docs/02-roadmap/roadmap-00-todolist.md` | 左侧标签与申请岗位说明可用；右侧三节点阶段流转/重置、节点时间展示、分离保存与历史面评回看均可保存回显。 |

### v0.1.1（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.1-001` | `DONE` | 初始化项目主业务骨架 | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `README.md` | 主业务链路可运行，文档闭环完整。 |
| `REQ-v0.1.1-002` | `DONE` | 简历筛选工作台（AIS 批次） | `app/server.py`, `web/index.html`, `web/app.js`, `web/styles.css`, `scripts/resume_app_up.sh` | 三栏界面可用，SQLite 录入可保存并可回显。 |

### v0.1.0（已发布）

| requirement_id | status | item | evidence_refs | done_definition |
| --- | --- | --- | --- | --- |
| `REQ-v0.1.0-001` | `DONE` | 初始化文档治理模板 | `docs/00-governance/*`, `docs/01-requirements/*`, `docs/02-roadmap/*` | 完成文档治理闭环基础结构。 |

## 4. 历史补录（未归档）

当前无未归档历史补录条目。

## 5. 归档规则（MUST）

1. 只接收来自 `roadmap-00` 的 `DONE`。
2. 非 `DONE` 状态不得写入本文件。
3. 保留原始 `requirement_id`，不得改写。
