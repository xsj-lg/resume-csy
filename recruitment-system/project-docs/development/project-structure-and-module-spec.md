# 项目目录与模块规范

本文档基于当前仓库的真实结构整理，用于说明目录分层、模块职责和当前代码边界。

## 1. 当前技术形态

| 项目 | 当前实现 |
| --- | --- |
| 后端框架 | 无第三方 Web 框架，基于 Python 标准库 `http.server` |
| 前端框架 | 无前端框架，原生 HTML/CSS/JavaScript |
| 数据库 | SQLite |
| 页面提供方式 | 后端直接提供 `web/` 静态文件 |
| 运行方式 | 单体进程，HTTP 与静态资源同服务 |

重要纠正：

- 当前项目不是 `FastAPI`。
- 当前项目不是前后端分离部署。
- 当前项目没有 ORM，也没有独立 migration 工具。

## 2. 目录总览

```text
recruitment-system/
├── VERSION
├── app/
│   ├── server.py
│   └── backend/
│       ├── controllers/
│       ├── repositories/
│       ├── services/
│       └── utils/
├── config/
├── data/
├── docs/
├── project-docs/
├── release/
├── scripts/
├── templates/
└── web/
```

## 3. 主要目录职责

### 3.1 `app/server.py`

- 启动入口。
- 负责启动 `ThreadingHTTPServer`。
- 通过控制器层初始化数据库并提供静态资源。

### 3.2 `app/backend/controllers/`

控制层负责路由分发、参数读取、权限前置判断和 HTTP 响应。

当前文件：

- `resume_controller.py`
  - HTTP Server 主入口
  - 统一处理 GET/POST/PUT/DELETE
  - 负责 Cookie 解析、JSON 返回、multipart 解析
- `system_controller.py`
  - 公共页面与 `/api/healthz`
- `auth_controller.py`
  - 登录、退出、当前用户、修改密码
- `user_role_controller.py`
  - 用户管理、角色定义、LLM 配置摘要
- `job_controller.py`
  - 岗位列表、批量保存、评分表上传/删除/预览
- `candidate_controller.py`
  - 候选人列表、简历上传/同步、评估详情、流程动作、自动评分、结构化抽取
- `operation_log_controller.py`
  - 操作记录列表、详情、导出

边界要求：

- Controller 只处理 HTTP 协议层问题。
- 不在 Controller 中直接拼接复杂业务对象。
- 不在 Controller 中直接维护 SQLite 迁移逻辑。

### 3.3 `app/backend/services/`

服务层承载业务规则、数据库操作编排和外部能力调用。

当前模块分布：

- `recruitment_service.py`
  - Facade 层，向控制器统一导出常量和服务函数
- `role_user_service.py`
  - 用户、角色、密码、Session 管理
- `job_service.py`
  - 岗位查询、保存、评分表版本管理
- `score_table_service.py`
  - 评分表文件解析、预览生成、评分项标准化与 Prompt 压缩
- `candidate_query_service.py`
  - 候选人列表聚合、筛选和面试日历查询
- `candidate_command_service.py`
  - 候选人上传、同步、删除、简历路径解析
- `candidate_workflow_service.py`
  - 候选人权限判断、流程流转、档案与面评保存
- `candidate_domain_service.py`
  - 面试阶段状态机、字段校验、状态推导
- `resume_extract_service.py`
  - 通过本地解析服务接口读取 PDF 内容
  - 维护 `candidate_files` 中的解析文本/原始结果缓存
  - 结构化抽取、抽取写回与手动刷新
- `auto_score_service.py`
  - 自动评分、规则降级、评分结果读写
- `llm_service.py`
  - LLM 配置读取、Prompt 加载、流式调用、JSON 解析
- `db_service.py`
  - 数据库初始化、增量迁移、历史兼容处理
- `operation_log_service.py`
  - 操作记录写入、查询、导出、审计上下文处理
- `candidate_service.py`
  - 聚合导出层 + 少量通用工具函数
  - 对外兼容旧调用入口，不再承担全部候选人业务实现

当前事实：

- 服务层已按职责拆分完成主体迁移。
- `candidate_service.py` 仍保留兼容性导出和少量基础工具，但不是主要业务实现落点。
- 新增业务优先进入独立 service，再通过 `recruitment_service.py` 暴露。

### 3.4 `app/backend/repositories/`

Repository 层当前仍然较薄，但已经出现明确的候选人仓储边界。

当前文件：

- `sqlite_helpers.py`
  - SQLite 连接封装
  - 统一设置 `busy_timeout`、优先启用 `WAL`、设置 `synchronous=NORMAL`
- `candidate_repository.py`
  - 候选人文件、档案、轮次、默认对象和补种逻辑

### 3.5 `app/backend/utils/`

- `time_utils.py`
  - 当前时间、时间戳、当天目录等轻量工具函数

### 3.6 `web/`

前端静态资源目录，由后端直接映射为 `/static/*` 和多个页面入口。

当前主要文件：

- `login.html` / `login.js`
  - 登录与首次改密
- `index.html` / `app.js`
  - 候选人工作台
- `jobs.html` / `jobs.js`
  - 岗位管理
- `users.html` / `users.js`
  - 用户管理与 LLM 配置只读页
- `operations.html` / `operations.js`
  - 操作记录审计页
- `styles.css`
  - 全站样式

附加说明：

- `app.recovered.js`、`app.corrupted.backup.js` 属于历史恢复/备份文件，不是当前主入口。
- 前端以原生 DOM 操作为主，没有构建流程。
- 工作台会使用 `localStorage` 保存排序、显示范围和最近查看候选人状态。

### 3.7 `config/`

- `llm-config.json`
  - LLM 运行配置
- `llm-prompts.json`
  - Prompt 模板配置
- `pdf-parser-config.json`
  - PDF 解析服务运行配置

### 3.8 `data/`

- `recruitment.sqlite3`
  - SQLite 主库
- `cv/ais/`
  - 简历 PDF 存储根目录
- `job_templates/`
  - 岗位评分表文件根目录

### 3.9 `scripts/`

- `resume_app_up.sh`
  - Linux 后台启动脚本
- `package_linux_release.py`
  - 打包 Linux 发行包

### 3.10 `release/`

当前已存在 Linux 离线包输出目录，说明项目已有离线发包流程。

## 4. 当前模块协作链路

### 4.1 登录链路

1. `login.js` 提交 `/api/auth/login`
2. `auth_controller.py` 校验账号密码
3. `role_user_service.py` 创建 `user_sessions`
4. 返回用户信息并写入 Cookie

### 4.2 岗位维护链路

1. `jobs.js` 读取/编辑岗位草稿
2. 通过 `/api/jobs`、`/api/jobs/bulk`、`/api/jobs/{job_id}/score-table` 与后端同步
3. `job_controller.py` 调用 `job_service.py`
4. 评分表解析与预览进入 `score_table_service.py`

### 4.3 简历上传与评分链路

1. `app.js` 通过 multipart 调用 `/api/resumes/upload`
2. `candidate_controller.py` 调用 `candidate_command_service.py`
3. 候选人档案、岗位快照、简历文件入库
4. 上传后优先生成并缓存 PDF 解析文本，再异步触发结构化抽取
5. 若岗位开启自动评分，则进一步调用 `auto_score_service.py`
6. 评分结果落库到 `candidate_auto_scores`

### 4.4 候选人详情链路

1. `app.js` 读取 `/api/evaluations/{candidate_id}`
2. 服务端聚合 `candidate_profiles`、`candidate_files`、`interview_round_notes`、`candidate_auto_scores`、岗位快照
3. `candidate_workflow_service.py` 和 `candidate_query_service.py` 协同返回详情

### 4.5 操作记录链路

1. `operations.js` 调用 `/api/operation-logs`
2. `operation_log_controller.py` 处理列表、详情和导出
3. `operation_log_service.py` 读取 `operation_logs` 表并返回审计数据

## 5. 当前结构的几个事实性限制

1. 统一 HTTP 分发仍集中在 `resume_controller.py`。
2. `recruitment_service.py` 仍是控制器层统一依赖的 facade。
3. Repository 层仍偏薄，除了候选人仓储外，大部分 SQL 仍在 service 层。
4. 前端没有模块打包和共享基础库，跨页面通用逻辑仍以函数复制为主。
5. 操作记录页当前入口是 `/static/operations.html`，没有单独的 `/operations` 路由。

## 6. 后续维护建议

1. 新增业务能力时，优先新增独立 service 文件，不要再把主逻辑堆回 `candidate_service.py`。
2. 继续下沉数据访问时，优先补齐 `jobs`、`users`、`candidate_auto_scores`、`operation_logs` 的 repository。
3. 若要新增页面，保持 `web/<page>.html + web/<page>.js` 的双文件模式，并在 `system_controller.py` 或导航入口同步更新。
4. 若后续引入框架，应先抽离 Controller 通用能力，再替换 HTTP 承载层，避免一次性回归过大。
