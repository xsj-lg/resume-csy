# TodoList

## 1. 文档信息

- 当前版本: `0.1.16`
- 目标版本: `0.1.16`
- 作用: 记录目标版本执行中的任务清单与状态，作为发布前唯一执行事实源。

### 最近更新（最新 5 条）

| date | version | target_version | summary |
| --- | --- | --- | --- |
| `2026-03-26` | `0.1.16` | `0.1.16` | 1. 根据用户确认，`REQ-v0.1.15-001/002/003` 已补录为真实已发布事实，并与 `REQ-v0.1.15-004/005` 一起完成 `roadmap-01` 归档及 `req-01/req-02` 回填。<br>2. `roadmap-00` 已按规则清场并切换到下一目标版本 `0.1.16`。<br>3. `REQ-v0.1.16-001` 已从 `req-00` 平移至本清单，状态初始化为 `PENDING`。 |
| `2026-03-26` | `0.1.15` | `0.1.15` | 1. `REQ-v0.1.15-005` 从 `req-00` 平移至本清单并进入执行。<br>2. 已完成协作治理补充：执行前强制重读 `docs/00-governance/`，且代码或文件变更必须同步更新对应 `project-docs` 描述。<br>3. 文档核对完成，`REQ-v0.1.15-005` 状态更新为 `DONE`，验证结果置为 `PASS`。<br>4. 用户确认已发布，`REQ-v0.1.15-005` 已归档到 `roadmap-01` 并完成 `req-01/req-02` 回填。 |
| `2026-03-25` | `0.1.15` | `0.1.15` | 1. `REQ-v0.1.15-004` 从 `req-00` 平移至本清单并进入 `IN_PROGRESS`。<br>2. 已启动上传评分表分段结构解析修复，补全维度下评分项与续行标准归属。<br>3. 功能验证完成，`REQ-v0.1.15-004` 状态更新为 `DONE`，验证结果置为 `PASS`。 |
| `2026-03-25` | `0.1.15` | `0.1.15` | 1. `REQ-v0.1.15-003` 从 `req-00` 平移至本清单并进入 `IN_PROGRESS`。<br>2. 已启动自动评分总分按评分项累加校验与前端评分项明细完整展示开发。 |
| `2026-03-25` | `0.1.15` | `0.1.15` | 1. `REQ-v0.1.15-002` 从 `req-00` 平移至本清单并进入 `IN_PROGRESS`。<br>2. 已启动工作台选中简历记录的前端持久化与返回恢复能力开发。 |

## 2. 字段说明

- `target_version`: 目标版本。
- `requirement_id`: 需求编号（`REQ-v<version>-NNN`）。
- `task_status`: `PENDING` / `IN_PROGRESS` / `BLOCKED` / `CANCELLED` / `DONE`。
- `item`: 执行任务标题。
- `draft_ref`: 对应 `req-00-draft.md` 来源。
- `frontend_scope`: 前端改动拆分（是否改动 + 功能点清单；不涉及填 `N/A`）。
- `backend_scope`: 后端改动拆分（是否改动 + 功能点清单；不涉及填 `N/A`）。
- `verification_plan`: 验证计划（至少列出接口、页面、回归中的实际验证项）。
- `verification_result`: 验证结果（`TODO` / `PASS` / `FAIL` / `N/A`）。
- `done_definition`: 完成判定标准。

## 3. Current TODO List

### 快速清单

- `REQ-v0.1.16-001` (`PENDING`): PDF 读取切换为解析服务接口。

### 任务详情

| target_version | requirement_id | task_status | item | draft_ref | frontend_scope | backend_scope | verification_plan | verification_result | done_definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0.1.16` | `REQ-v0.1.16-001` | `PENDING` | PDF 读取切换为解析服务接口 | `req-00 4.2` | `N/A` | `是：将 PDF 读取入口切换为本地解析服务接口调用；解析 `pages/paragraphs/textPara.content` 等结果结构；为基础信息识别、结构化抽取和自动评分提供兼容文本或结构化输入。` | `1) 读取 PDF 时改为调用 `POST http://127.0.0.1:7642/ais/parser/syncParseFile`。2) 服务端可正确处理 multipart `file` 上传并解析接口返回的页面/段落文本。3) 解析结果能继续支撑手机号、邮箱、学校识别及后续结构化抽取链路。4) 当解析服务异常或结果为空时，系统返回明确错误或按约定降级。` | `TODO` | `PDF 读取主链路已切换为解析服务接口，且上传、抽取、自动评分等下游链路验证通过后可置 DONE。` |

### 平移拆分模板（需求进入 roadmap-00 时填写）

| target_version | requirement_id | task_status | item | draft_ref | frontend_scope | backend_scope | verification_plan | verification_result | done_definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0.1.x` | `REQ-v0.1.x-00x` | `PENDING` | 示例：支持候选人筛选 | `req-00 4.x` | `是：筛选输入框、列表联动、空态文案` | `是：新增筛选参数、查询条件拼接` | `1) 接口按姓名、岗位筛选返回正确。2) 页面筛选后列表与计数正确。3) 回归上传与详情查看不受影响。` | `TODO` | `前后端改动点完成，验证项全部 PASS 后可置 DONE。` |

### 执行说明（当前目标版本）

- 当前目标版本已切换到 `0.1.16`。
- 发布归档（2026-03-26）：根据用户明确确认，`REQ-v0.1.15-001/002/003` 与 `REQ-v0.1.15-004/005` 一并视为真实已发布事实，已同步归档到 `roadmap-01` 并完成 `req-01/req-02` 回填。
- `REQ-v0.1.16-001` 已由 `req-00` 确认为 `CONFIRMED` 并平移至当前版本执行清单，状态 `PENDING`。
- 需求范围（2026-03-26）：现有 PDF 读取链路需从本地文本解析切换为本地解析服务接口，接口结果格式以用户提供的 `d:\AIS\test.json` 为参考。

## 4. 版本执行规则（MUST）

1. 进入执行的需求必须先平移到本文档。
2. 平移后初始状态为 `PENDING`。
3. 执行状态只在本文档维护。
4. 平移时必须完成需求拆分：明确 `frontend_scope` 与 `backend_scope`，并写清功能点。
5. 每条需求必须维护 `verification_plan` 与 `verification_result`，未完成验证不得置 `DONE`。
6. `DONE` 在发布时归档到 `roadmap-01`。
