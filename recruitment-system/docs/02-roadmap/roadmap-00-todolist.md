# TodoList

## 1. 文档信息

- 当前版本: `0.1.17`
- 目标版本: `0.1.17`
- 作用: 记录目标版本执行中的任务清单与状态，作为发布前唯一执行事实源。

### 最近更新（最新 5 条）

| date | version | target_version | summary |
| --- | --- | --- | --- |
| `2026-03-27` | `0.1.16` | `0.1.16` | 1. `v0.1.16` 已发布：`REQ-v0.1.16-001/002/003/004` 已归档到 `roadmap-01` 并完成 `req-01/req-02` 回填。<br>2. `roadmap-00` 已按规则清场并切换到下一目标版本 `0.1.17`。 |
| `2026-03-27` | `0.1.16` | `0.1.16` | 1. 修复 `REQ-v0.1.16-003` 回归问题：结构化抽取成功后，候选人姓名需同步覆盖页面通用信息与列表名称来源。<br>2. 结构化抽取现已将合并后的 `basic.name` 回写到 `candidate_files.candidate_name`，并对“未知/未提供”等占位姓名做兜底过滤。 |
| `2026-03-27` | `0.1.16` | `0.1.16` | 1. 修正 `REQ-v0.1.16-002` 的结构化抽取复用口径：当自动评分或其他链路已写入简历解析缓存后，后续 `/resume-extract` 不再默认强制刷新。<br>2. 简历结构化抽取现已统一优先复用 `candidate_files` 中的已落库解析结果，仅在缓存缺失或显式要求刷新时才重新请求解析服务。 |
| `2026-03-27` | `0.1.16` | `0.1.16` | 1. `REQ-v0.1.16-003` 已完成开发：上传后的规则初抽会先写入 `resume_structured_json`，大模型抽取完成后再按字段级策略合并回写。<br>2. 页面结构化抽取回显支持初抽结果即时展示，并在大模型成功后执行“有值覆盖、无值保留”的替换。<br>3. 语法检查、规则初抽写入验证与结构化字段合并验证完成，`REQ-v0.1.16-003` 状态更新为 `DONE`，验证结果置为 `PASS`。 |
| `2026-03-27` | `0.1.16` | `0.1.16` | 1. 修复 LLM 流式调用返回值契约不一致问题：`call_llm_chat_stream()` 在异常/降级分支不再返回额外调试对象。<br>2. 自动评分、简历抽取与评分表预览链路继续统一按三个返回值解包，避免触发 `too many values to unpack (expected 3)`。 |

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

- 当前目标版本暂无执行项。

### 任务详情

| target_version | requirement_id | task_status | item | draft_ref | frontend_scope | backend_scope | verification_plan | verification_result | done_definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

### 平移拆分模板（需求进入 roadmap-00 时填写）

| target_version | requirement_id | task_status | item | draft_ref | frontend_scope | backend_scope | verification_plan | verification_result | done_definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0.1.x` | `REQ-v0.1.x-00x` | `PENDING` | 示例：支持候选人筛选 | `req-00 4.x` | `是：筛选输入框、列表联动、空态文案` | `是：新增筛选参数、查询条件拼接` | `1) 接口按姓名、岗位筛选返回正确。2) 页面筛选后列表与计数正确。3) 回归上传与详情查看不受影响。` | `TODO` | `前后端改动点完成，验证项全部 PASS 后可置 DONE。` |

### 执行说明（当前目标版本）

- 当前目标版本已切换到 `0.1.17`。
- 发布归档（2026-03-26）：根据用户明确确认，`REQ-v0.1.15-001/002/003` 与 `REQ-v0.1.15-004/005` 一并视为真实已发布事实，已同步归档到 `roadmap-01` 并完成 `req-01/req-02` 回填。
- `v0.1.16` 已于 `2026-03-27` 发布，`REQ-v0.1.16-001/002/003/004` 已归档到 `roadmap-01` 并完成 `req-01/req-02` 回填。
- 当前目标版本 `0.1.17` 暂无执行中的需求项。

## 4. 版本执行规则（MUST）

1. 进入执行的需求必须先平移到本文档。
2. 平移后初始状态为 `PENDING`。
3. 执行状态只在本文档维护。
4. 平移时必须完成需求拆分：明确 `frontend_scope` 与 `backend_scope`，并写清功能点。
5. 每条需求必须维护 `verification_plan` 与 `verification_result`，未完成验证不得置 `DONE`。
6. `DONE` 在发布时归档到 `roadmap-01`。
