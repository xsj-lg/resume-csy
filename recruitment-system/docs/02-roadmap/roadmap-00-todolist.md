# TodoList

## 1. 文档信息

- 当前版本: `0.1.19`
- 目标版本: `0.1.19`
- 作用: 记录目标版本执行中的任务清单与状态，作为发布前唯一执行事实源。

### 最近更新（最新 5 条）

| date | version | target_version | summary |
| --- | --- | --- | --- |
| `2026-04-01` | `0.1.19` | `0.1.19` | 1. `v0.1.18` 已发布：`REQ-v0.1.18-001` 已归档到 `roadmap-01` 并完成 `req-01/req-02` 回填。<br>2. `roadmap-00` 已按规则清场并切换到下一目标版本 `0.1.19`。 |
| `2026-03-31` | `0.1.18` | `0.1.18` | 1. `REQ-v0.1.18-001` 已从 `req-00` 平移到当前执行清单并进入 `PENDING`。<br>2. 启动岗位管理“简历结果导出”入口、独立导出页、统计汇总和表格导出能力改造。 |
| `2026-03-30` | `0.1.17` | `0.1.17` | 1. 用户确认 `REQ-v0.1.16-001/002` 已发布。<br>2. 两条需求已从当前执行清单归档到 `roadmap-01`，并完成 `req-01/req-02` 发布后回填。 |
| `2026-03-30` | `0.1.17` | `0.1.17` | 1. `REQ-v0.1.16-002` 从 `req-00` 平移至本清单并进入 `PENDING`。<br>2. 启动面试阶段按钮下沉、阶段面评信息联动与下一阶段安排录入改造。 |
| `2026-03-30` | `0.1.17` | `0.1.17` | 1. `REQ-v0.1.16-001` 已在本地发布窗口内收口完成。<br>2. 角色权限与阶段负责人驱动的候选人可见范围改造闭环完成。 |
| `2026-03-27` | `0.1.16` | `0.1.16` | 1. `v0.1.16` 已发布：`REQ-v0.1.16-001/002/003/004` 已归档到 `roadmap-01` 并完成 `req-01/req-02` 回填。<br>2. `roadmap-00` 已按规则清场并切换到下一目标版本 `0.1.17`。 |
| `2026-03-27` | `0.1.16` | `0.1.16` | 1. 修复 `REQ-v0.1.16-003` 回归问题：结构化抽取成功后，候选人姓名需同步覆盖页面通用信息与列表名称来源。<br>2. 结构化抽取现已将合并后的 `basic.name` 回写到 `candidate_files.candidate_name`，并对“未知/未提供”等占位姓名做兜底过滤。 |

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

- 当前已切换到 `0.1.19` 规划窗口，等待新需求进入执行清单。

### 任务详情

| target_version | requirement_id | task_status | item | draft_ref | frontend_scope | backend_scope | verification_plan | verification_result | done_definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

### 平移拆分模板（需求进入 roadmap-00 时填写）

| target_version | requirement_id | task_status | item | draft_ref | frontend_scope | backend_scope | verification_plan | verification_result | done_definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0.1.x` | `REQ-v0.1.x-00x` | `PENDING` | 示例：支持候选人筛选 | `req-00 4.x` | `是：筛选输入框、列表联动、空态文案` | `是：新增筛选参数、查询条件拼接` | `1) 接口按姓名、岗位筛选返回正确。2) 页面筛选后列表与计数正确。3) 回归上传与详情查看不受影响。` | `TODO` | `前后端改动点完成，验证项全部 PASS 后可置 DONE。` |

### 执行说明（当前目标版本）

- 当前目标版本已切换到 `0.1.19`。
- `REQ-v0.1.18-001` 已于 `2026-04-01` 完成发布归档，详见 `roadmap-01-task-history.md`。
- `REQ-v0.1.16-001/002` 已于 `2026-03-30` 完成发布归档，详见 `roadmap-01-task-history.md`。

## 4. 版本执行规则（MUST）

1. 进入执行的需求必须先平移到本文档。
2. 平移后初始状态为 `PENDING`。
3. 执行状态只在本文档维护。
4. 平移时必须完成需求拆分：明确 `frontend_scope` 与 `backend_scope`，并写清功能点。
5. 每条需求必须维护 `verification_plan` 与 `verification_result`，未完成验证不得置 `DONE`。
6. `DONE` 在发布时归档到 `roadmap-01`。
