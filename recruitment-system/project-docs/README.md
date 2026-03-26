# 简历筛选项目文档目录

本目录用于沉淀 `recruitment-system` 当前工作区代码的实现事实，内容以仓库现状为准，不以历史发布文档为准。

## 项目概览

- 当前工作区版本：`0.1.16`
- 代码仓库根目录：`d:\AIS\code\AIS\python\recruitment-system`
- 后端形态：Python 标准库 `http.server` 单体服务
- 前端形态：`web/` 目录下的原生 HTML + CSS + JavaScript 静态页面
- 数据存储：本地 SQLite（`data/recruitment.sqlite3`）
- 运行数据目录：
  - 简历 PDF：`data/cv/ais/`
  - 岗位评分表：`data/job_templates/`
- 配置目录：`config/`

## 文档结构

```text
project-docs/
├── api/
│   └── api-documentation.md
├── database/
│   └── database-schema.md
├── development/
│   ├── development-and-integration-guidelines.md
│   ├── file-function-index.md
│   ├── file-structure-inventory.md
│   └── project-structure-and-module-spec.md
├── operations/
│   └── deployment-and-operations-guide.md
└── product/
    └── feature-list.md
```

## 各文档用途

- `api/`：记录当前 HTTP 路由、认证方式、请求/响应结构、权限限制与常见错误。
- `database/`：记录 SQLite 实际表结构、索引、逻辑关系与初始化/迁移策略。
- `development/`：记录真实目录结构、模块边界、联调方式与常用验证命令。
  - `file-structure-inventory.md`：文件级目录清单、主入口、过渡文件和目录职责。
  - `file-function-index.md`：按文件整理公开函数、主要职责和调用关系。
- `operations/`：记录启动方式、环境变量、日志位置、打包与备份建议。
- `product/`：记录当前已落地能力、角色边界、业务流程与已知限制。

## 当前代码结构重点

- `app/backend/services/` 已按职责拆分为用户角色、岗位、评分表、候选人查询、候选人命令、候选人流程、简历抽取、自动评分、LLM、数据库、操作记录等模块。
- `app/backend/repositories/candidate_repository.py` 已承接候选人档案和文件的仓储读写。
- `candidate_service.py` 当前主要承担聚合导出和少量通用工具，不再是之前的大而全实现文件。
- 前端页面已包含工作台、岗位管理、用户管理、登录页和操作记录页，其中操作记录页入口为 `/static/operations.html`。

## 维护建议

1. 新增页面或模块目录时，同时更新 `development/project-structure-and-module-spec.md`。
2. 新增接口或变更返回结构时，同时更新 `api/api-documentation.md`。
3. 新增表字段、索引或迁移逻辑时，同时更新 `database/database-schema.md`。
4. 新增产品能力、角色权限或关键流程时，同时更新 `product/feature-list.md`。
5. 文档中的模块名、路径名、字段名优先直接复用代码真实命名，避免另造术语。
