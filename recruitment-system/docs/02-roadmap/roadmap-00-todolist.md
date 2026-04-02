# TodoList

## 1. 文档信息

- 当前版本: `0.1.19`
- 目标版本: `0.1.19`
- 作用: 记录目标版本执行中的任务清单与状态，作为发布前唯一执行事实源。

### 最近更新（最新 5 条）

| date | version | target_version | summary |
| --- | --- | --- | --- |
| `2026-04-01` | `0.1.19` | `0.1.19` | 1. 新增执行项 `REQ-v0.1.19-001`：上传图片时复用本地解析服务接口，并沿用既有解析缓存结构。<br>2. 已完成上传入口、解析链路、预览类型与联调文档同步，图片场景在解析服务失败时直接返回解析失败；语法检查完成后状态置为 `DONE`、验证结果置为 `PASS`。 |
| `2026-04-01` | `0.1.19` | `0.1.19` | 1. `v0.1.18` 已发布：`REQ-v0.1.18-001` 已归档到 `roadmap-01` 并完成 `req-01/req-02` 回填。<br>2. `roadmap-00` 已按规则清场并切换到下一目标版本 `0.1.19`。 |
| `2026-03-31` | `0.1.18` | `0.1.18` | 1. `REQ-v0.1.18-001` 已从 `req-00` 平移到当前执行清单并进入 `PENDING`。<br>2. 启动岗位管理“简历结果导出”入口、独立导出页、统计汇总和表格导出能力改造。 |
| `2026-03-30` | `0.1.17` | `0.1.17` | 1. 用户确认 `REQ-v0.1.16-001/002` 已发布。<br>2. 两条需求已从当前执行清单归档到 `roadmap-01`，并完成 `req-01/req-02` 发布后回填。 |
| `2026-03-30` | `0.1.17` | `0.1.17` | 1. `REQ-v0.1.16-002` 从 `req-00` 平移至本清单并进入 `PENDING`。<br>2. 启动面试阶段按钮下沉、阶段面评信息联动与下一阶段安排录入改造。 |

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

- `REQ-v0.1.19-001` `DONE`：上传图片时复用本地解析服务，图片解析失败直接返回错误。

### 任务详情

| target_version | requirement_id | task_status | item | draft_ref | frontend_scope | backend_scope | verification_plan | verification_result | done_definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0.1.19` | `REQ-v0.1.19-001` | `DONE` | 支持上传图片并复用本地解析服务 | `req-00 4.2` | `是：上传按钮/弹窗文案、文件类型校验、图片预览文案` | `是：上传类型校验、图片调用本地解析服务、解析缓存写入、图片失败即返回解析失败、预览响应类型按文件类型返回` | `1) Python 语法检查通过。2) 前端脚本语法检查通过。3) 代码核对图片上传走本地解析服务且失败不走 PDF 回退。4) 回归确认 PDF 上传/缓存/回退链路仍保留。` | `PASS` | `图片上传成功时可复用既有解析缓存与抽取链路；图片解析服务失败时接口直接报错；PDF 既有链路不回归。` |

### 平移拆分模板（需求进入 roadmap-00 时填写）

| target_version | requirement_id | task_status | item | draft_ref | frontend_scope | backend_scope | verification_plan | verification_result | done_definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `0.1.x` | `REQ-v0.1.x-00x` | `PENDING` | 示例：支持候选人筛选 | `req-00 4.x` | `是：筛选输入框、列表联动、空态文案` | `是：新增筛选参数、查询条件拼接` | `1) 接口按姓名、岗位筛选返回正确。2) 页面筛选后列表与计数正确。3) 回归上传与详情查看不受影响。` | `TODO` | `前后端改动点完成，验证项全部 PASS 后可置 DONE。` |

### 执行说明（当前目标版本）

- 当前目标版本已切换到 `0.1.19`。
- `REQ-v0.1.18-001` 已于 `2026-04-01` 完成发布归档，详见 `roadmap-01-task-history.md`。
- `REQ-v0.1.16-001/002` 已于 `2026-03-30` 完成发布归档，详见 `roadmap-01-task-history.md`。
- 当前目标版本 `0.1.19` 已新增 `REQ-v0.1.19-001`，当前已完成开发与语法校验，等待后续统一发布归档。

## 4. 版本执行规则（MUST）

1. 进入执行的需求必须先平移到本文档。
2. 平移后初始状态为 `PENDING`。
3. 执行状态只在本文档维护。
4. 平移时必须完成需求拆分：明确 `frontend_scope` 与 `backend_scope`，并写清功能点。
5. 每条需求必须维护 `verification_plan` 与 `verification_result`，未完成验证不得置 `DONE`。
6. `DONE` 在发布时归档到 `roadmap-01`。
