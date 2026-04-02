# 开发与联调规范

本文档记录当前项目在真实实现下的开发、联调、验证和常见协作注意事项。

## 1. 当前开发形态

| 项目 | 当前情况 |
| --- | --- |
| 后端服务 | Python 单进程 HTTP 服务 |
| 前端页面 | 原生静态页面，由后端直接托管 |
| 本地数据库 | SQLite |
| 接口认证 | Cookie Session |
| 当前主要验证方式 | 语法检查 + 手工联调 |

说明：仓库中暂未形成完整自动化测试体系，当前协作仍以关键链路手工回归为主。

## 2. 常用启动方式

### 2.1 直接启动

```bash
python app/server.py
```

默认监听：

- `RESUME_APP_HOST=127.0.0.1`
- `RESUME_APP_PORT=8080`

### 2.2 Linux 后台启动

```bash
bash scripts/resume_app_up.sh
```

脚本会：

- 检查是否已有同一服务在运行
- 写 PID 到 `/tmp/recruitment-system-resume-app.pid`
- 输出日志到 `/tmp/recruitment-system-resume-app.log`

## 3. 关键联调场景

### 3.1 登录与用户管理

1. 通过 `/login` 页面登录。
2. 检查 Cookie 是否写入。
3. 验证首次登录/重置密码后的强制改密流程。
4. 验证管理员新增、编辑、重置密码是否生效。

### 3.2 岗位管理与评分表

1. 岗位列表加载。
2. 新建岗位、编辑岗位、关闭岗位、复制岗位。
3. 招聘负责人/用人经理用户下拉是否正确。
4. 岗位评分表上传、预览、版本切换、删除是否正常。
5. 管理员与人事经理是否可在岗位管理页右侧看到“简历结果导出”入口并正常进入导出页。
6. HR / 招聘专员是否不可见该入口，且直访导出页或导出接口时返回 403。

### 3.3 候选人上传与工作台

1. 上传 PDF 或图片简历并绑定岗位。
2. 列表是否出现新候选人。
3. 简历文件是否能在右侧 iframe 打开，PDF 与图片预览类型正确。
4. 通用信息保存后是否回显。
5. 流程推进后阶段状态是否更新。
6. 面试时间是否进入面试日历。
7. 离开工作台后再返回，是否能恢复最近查看的候选人。

### 3.4 结构化抽取与自动评分

1. 手动触发 `/resume-extract` 后抽取区块是否刷新。
2. 上传时若岗位启用自动评分，是否自动写入评分结果。
3. 手动触发 `/auto-score` 是否更新 AI 评分区块。
4. LLM 不可用时是否回退到规则评分，而不是整链路报错。
5. 本地 PDF 解析服务 `http://127.0.0.1:7642/ais/parser/syncParseFile` 是否可达，且能返回包含 `pages[].paragraphs[].textPara.content` 的 JSON 结果。
6. 首次解析后是否把文本和原始结果写入 `candidate_files`，再次触发自动评分/详情加载时是否优先复用数据库缓存。
7. 自动评分过程中即使 LLM 调用异常，`candidate_files` 中的解析缓存也不应丢失或回滚。
8. 简历刚上传完成时，规则初抽的手机号、邮箱和摘要是否已先写入 `resume_structured_json` 并可在页面回显。
9. 大模型结构化抽取完成后，页面字段是否遵守“有值覆盖、无值保留”，空值不会覆盖规则初抽或人工已有值。
10. 模拟本地 PDF 解析服务不可达或超时后，系统是否会自动回退旧的 PDF 文本提取工具，并继续把结果写入 `candidate_files`。
11. 上传图片简历时，是否同样调用本地解析服务并写入 `candidate_files` 解析缓存。
12. 上传图片简历时若本地解析服务不可达、超时、异常或空结果，接口是否直接返回解析失败且不保留上传结果。

### 3.5 操作记录页

1. 管理员访问 `/static/operations.html`。
2. 列表筛选、详情查看、上一条同对象比对是否正常。
3. 导出 JSON / CSV 是否正常。
4. 非管理员访问相关接口时是否返回 `403 operation_logs_forbidden`。

### 3.6 简历结果导出页

1. 管理员访问 `/resume-results-export`。
2. 按简历上传时间设置开始和结束日期后，统计区是否正确展示总数、已面试完、通过、未通过、四阶段在途数量。
3. “已面试完”是否严格等于“通过 + 未通过”。
4. 导出 CSV 后，记录数是否与当前筛选结果一致。
5. 导出列是否包含上传时间、简历人员、`初筛/一面/二面/HR面` 面试人和当前状态。
6. 人事经理访问页面与导出接口是否正常。
7. HR / 招聘专员访问页面或导出接口时是否返回 403。

## 4. 常用验证命令

### 4.1 Python 语法检查

```bash
python -m py_compile app/server.py
python -m py_compile app/backend/controllers/*.py
python -m py_compile app/backend/services/*.py
python -m py_compile app/backend/repositories/*.py
python -m py_compile app/backend/utils/*.py
```

### 4.2 前端脚本语法检查

```bash
node --check web/login.js
node --check web/app.js
node --check web/jobs.js
node --check web/resume-results-export.js
node --check web/users.js
node --check web/operations.js
```

## 5. 接口联调约定

### 5.1 鉴权

- 登录后依赖浏览器自动携带 Cookie。
- 前端 `fetch` 不需要手动拼接 `Authorization` 头。
- 当接口返回 `401 unauthorized` 时，应跳回登录页。
- 当接口返回 `403 must_change_password` 时，应跳到改密流程。

### 5.2 JSON 与 FormData

- JSON 接口统一返回 `item/items/ok/error` 这种轻量结构。
- 文件上传场景统一使用 `multipart/form-data`。
- 服务端自行解析 multipart，对字段名大小写和结构比较敏感，联调时应严格复用现有前端字段名。

### 5.3 常用上传字段

#### 简历上传

- `file`
- `candidate_name`
- `department_scope`
- `job_id`
- `job_code`
- `job_title`
- `job_payload`

#### 岗位评分表上传

- `file`

## 6. 数据与迁移协作注意事项

1. 数据库结构由 `db_service.init_db()` 在启动时自动补齐，不依赖独立 migration 工具。
2. 修改数据库结构时，要同时考虑已有 SQLite 文件的增量升级路径。
3. 新增字段优先采用兼容 `ALTER TABLE ... ADD COLUMN` 的设计。
4. 候选人与岗位仍存在 `job_ref_id` 和 `job_id` 两套兼容关联字段，改动时不能只改一种写法。
5. 操作记录现在已经入独立表，新增关键业务操作时应同步补充留痕。

## 7. 前端本地状态现状

当前前端会使用 `localStorage` 保存部分界面状态，联调时需要留意历史缓存的影响。

主要键包括：

- `candidateSortMode`
- `showAllCandidates`
- `rs_workspace_last_candidate_v1`

涉及页面：

- `web/app.js`
- `web/operations.js`（仅本地兜底展示时会读取部分前端聚合数据）

## 8. LLM 配置协作约定

- 默认配置文件路径：`config/llm-config.json`
- 可通过环境变量 `RESUME_APP_LLM_CONFIG_PATH` 覆盖配置文件路径
- Prompt 配置默认来自 `config/llm-prompts.json`
- `/api/settings/llm-config` 只返回可公开的运行摘要，不回传实际密钥
- 协作上仍推荐使用环境变量，而不是把密钥写进仓库文件

## 8.5 PDF 解析服务协作约定

- 简历 PDF 文本读取当前优先通过本地解析服务完成，而不是直接使用本地 `pypdf` 链路。
- 图片简历上传时也会复用同一解析服务接口与 `file` 上传字段。
- 默认配置文件路径：`config/pdf-parser-config.json`
- 默认解析服务地址：`http://127.0.0.1:7642/ais/parser/syncParseFile`
- 运行时优先读取 `pdf-parser-config.json` 中的 `service_url`、`timeout_seconds` 和 `fallback_enabled`。
- 可通过环境变量 `RESUME_APP_PDF_PARSER_CONFIG_PATH` 覆盖 PDF 解析配置文件路径。
- 可通过环境变量 `RESUME_APP_PDF_PARSER_URL`、`RESUME_APP_PDF_PARSER_TIMEOUT_SECONDS`、`RESUME_APP_PDF_PARSER_FALLBACK_ENABLED` 覆盖单项运行参数。
- 解析服务返回结果以 `pages[].paragraphs[].textPara.content` 为主要文本来源，联调时应优先检查该结构是否稳定。
- 首次解析成功后，会将解析文本和原始结果缓存到 `candidate_files`；后续自动评分、详情兜底抽取与再次读取文本时优先复用数据库缓存。
- 当解析服务不可达、超时、返回异常状态、非法 JSON 或空结果时，会自动回退旧的 PDF 文本提取工具，并将回退文本与来源信息同样写入 `candidate_files`。
- 当上传文件为图片时，不启用旧 PDF 工具回退；若解析服务失败，上传接口直接返回解析失败。
- 手动调用 `/api/evaluations/{candidate_id}/resume-extract` 时，若数据库中已有可用解析缓存，则结构化抽取会直接复用缓存，不再默认重新请求解析服务。
- 上传完成后的规则初抽会先把手机号、邮箱和摘要写入 `candidate_profiles.resume_structured_json`，用于页面即时回显。
- 大模型结构化抽取成功后，会在保留既有结果的前提下按字段级合并 `resume_structured_json`，仅用非空有效值覆盖原字段。

## 9. 当前技术限制

- 无 FastAPI/Flask
- 无 ORM
- 无 OpenAPI 自动生成
- 无统一中间件系统
- 无成熟自动化测试工程

因此当前协作默认采用“页面直连真实接口 + 手工回归关键链路”的方式。

## 10. 变更时必须同步更新的文档

| 变更类型 | 需要同步更新的文档 |
| --- | --- |
| 新增或修改接口 | `project-docs/api/api-documentation.md` |
| 新增或修改表结构 | `project-docs/database/database-schema.md` |
| 新增页面或模块目录 | `project-docs/development/project-structure-and-module-spec.md` |
| 部署/启动/配置变更 | `project-docs/operations/deployment-and-operations-guide.md` |
| 角色权限或业务流程变化 | `project-docs/product/feature-list.md` |
