# 文件结构清单

本文档提供当前工作区的文件级目录结构清单，重点标注主入口、核心实现文件、兼容聚合文件和历史备份文件。

## 1. 根目录关键文件

| 路径 | 类型 | 作用 |
| --- | --- | --- |
| `VERSION` | 版本文件 | 当前工作区版本号 |
| `README.md` | 根说明 | 项目根说明与治理入口 |
| `app/server.py` | 启动入口 | 启动 HTTP 服务 |

## 2. 后端目录

### 2.1 `app/backend/controllers/`

| 文件 | 角色 | 说明 |
| --- | --- | --- |
| `resume_controller.py` | 主入口 | 统一 HTTP 分发、请求解析、响应输出 |
| `system_controller.py` | 公共入口 | 静态页面和 `/api/healthz` |
| `auth_controller.py` | 认证控制器 | 登录、退出、当前用户、改密 |
| `user_role_controller.py` | 用户控制器 | 用户列表、角色定义、LLM 摘要 |
| `job_controller.py` | 岗位控制器 | 岗位 CRUD、评分表上传/删除/预览 |
| `candidate_controller.py` | 候选人控制器 | 列表、上传、详情、流程、评分、抽取 |
| `operation_log_controller.py` | 审计控制器 | 操作记录列表、详情、导出 |

### 2.2 `app/backend/services/`

| 文件 | 角色 | 说明 |
| --- | --- | --- |
| `recruitment_service.py` | Facade | 控制器统一导入入口 |
| `role_user_service.py` | 真实实现 | 用户、角色、密码、Session |
| `job_service.py` | 真实实现 | 岗位管理、评分表版本管理 |
| `score_table_service.py` | 真实实现 | 评分表解析、预览、评分项整理 |
| `candidate_query_service.py` | 真实实现 | 候选人列表聚合、筛选、日历 |
| `candidate_command_service.py` | 真实实现 | 上传、同步、删除、异步任务调度 |
| `candidate_workflow_service.py` | 真实实现 | 权限、详情、流程流转、保存 |
| `candidate_domain_service.py` | 真实实现 | 状态机、字段校验、状态推导 |
| `resume_extract_service.py` | 真实实现 | PDF 文本提取、结构化抽取 |
| `auto_score_service.py` | 真实实现 | 自动评分、规则降级、评分落库 |
| `llm_service.py` | 真实实现 | LLM 配置、Prompt、流式调用 |
| `db_service.py` | 真实实现 | 建表、迁移、兼容升级 |
| `operation_log_service.py` | 真实实现 | 审计日志写入、查询、导出 |
| `candidate_service.py` | 兼容聚合 | 旧入口兼容 + 通用工具函数 |
| `__init__.py` | 包文件 | services 包标记 |

说明：

- 当前主要业务实现已经从 `candidate_service.py` 拆分到专门 service。
- `candidate_service.py` 仍保留对外兼容导出，不建议继续新增主逻辑。

### 2.3 `app/backend/repositories/`

| 文件 | 角色 | 说明 |
| --- | --- | --- |
| `sqlite_helpers.py` | 基础设施 | SQLite 连接与连接选项 |
| `candidate_repository.py` | 仓储实现 | 候选人文件、档案、轮次和补种逻辑 |
| `__init__.py` | 包文件 | repositories 包标记 |

### 2.4 `app/backend/utils/`

| 文件 | 角色 | 说明 |
| --- | --- | --- |
| `time_utils.py` | 工具 | 时间戳、UTC 时间、当日目录 |
| `__init__.py` | 包文件 | utils 包标记 |

## 3. 前端目录 `web/`

| 文件 | 角色 | 说明 |
| --- | --- | --- |
| `index.html` | 主页面 | 候选人工作台 |
| `app.js` | 主脚本 | 工作台交互、筛选、详情、流程、记忆最近查看 |
| `jobs.html` | 页面 | 岗位管理页 |
| `jobs.js` | 页面脚本 | 岗位列表、编辑、评分表管理 |
| `users.html` | 页面 | 用户管理页 |
| `users.js` | 页面脚本 | 用户管理、LLM 配置摘要 |
| `operations.html` | 页面 | 操作记录审计页 |
| `operations.js` | 页面脚本 | 审计列表、详情、导出和比对 |
| `login.html` | 页面 | 登录页 |
| `login.js` | 页面脚本 | 登录和改密 |
| `styles.css` | 样式 | 全站样式 |
| `app.recovered.js` | 历史恢复文件 | 非当前主入口 |
| `app.corrupted.backup.js` | 历史备份文件 | 非当前主入口 |

## 4. 配置与脚本

### 4.1 `config/`

| 文件 | 作用 |
| --- | --- |
| `llm-config.json` | LLM 运行配置 |
| `llm-prompts.json` | Prompt 模板配置 |

### 4.2 `scripts/`

| 文件 | 作用 |
| --- | --- |
| `resume_app_up.sh` | Linux 后台启动 |
| `package_linux_release.py` | Linux 离线包打包 |

## 5. 文档目录

### 5.1 `project-docs/`

| 文件 | 作用 |
| --- | --- |
| `README.md` | 文档目录入口 |
| `api/api-documentation.md` | 接口事实文档 |
| `database/database-schema.md` | 数据库结构文档 |
| `development/project-structure-and-module-spec.md` | 模块级结构说明 |
| `development/development-and-integration-guidelines.md` | 联调与开发规范 |
| `development/file-structure-inventory.md` | 文件级结构清单 |
| `development/file-function-index.md` | 文件功能索引 |
| `operations/deployment-and-operations-guide.md` | 部署与运维说明 |
| `product/feature-list.md` | 产品能力清单 |

## 6. 当前主入口与过渡文件

### 6.1 主入口

- 后端启动入口：`app/server.py`
- HTTP 分发入口：`app/backend/controllers/resume_controller.py`
- 控制器统一服务入口：`app/backend/services/recruitment_service.py`
- 前端主页面：`web/index.html`
- 前端主脚本：`web/app.js`

### 6.2 兼容与过渡

- `app/backend/services/candidate_service.py`
  - 兼容旧调用入口
  - 提供少量通用工具
- `web/app.recovered.js`
  - 历史恢复文件
- `web/app.corrupted.backup.js`
  - 历史备份文件

## 7. 维护建议

1. 新增文件时，优先补到本清单。
2. 文件职责变化时，同时更新 [project-structure-and-module-spec.md](/d:/AIS/code/AIS/python/recruitment-system/project-docs/development/project-structure-and-module-spec.md)。
3. 新增“真实实现文件”时，应标明原文件是否变为兼容聚合或废弃过渡文件。
