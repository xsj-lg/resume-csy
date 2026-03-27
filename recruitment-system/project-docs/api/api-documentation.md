# API 文档

本文档记录当前仓库中已经实现的 HTTP 接口与静态页面入口，基于 `app/backend/controllers/*.py` 和 `web/*.js` 的实际调用情况整理。

## 1. 基础约定

| 项目 | 当前实现 |
| --- | --- |
| API 前缀 | `/api` |
| 服务类型 | Python `ThreadingHTTPServer` 单体服务 |
| 认证方式 | 登录成功后下发 `RS_SESSION` HttpOnly Cookie |
| Cookie 属性 | `Path=/; HttpOnly; SameSite=Lax` |
| 默认会话时长 | 7 天 |
| 请求体 | JSON 或 multipart/form-data |
| 统一成功结构 | `{"item": ...}` / `{"items": [...]}` / `{"ok": true}` |
| 统一错误结构 | `{"error": "..."}` |

重要纠正：

- 当前实现没有使用 `/api/v1`。
- 当前实现没有使用 JWT Bearer Token。
- 当前实现没有统一 `code/message/requestId` 包装层。

## 2. 公共页面与无需登录接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 工作台首页，返回 `web/index.html` |
| GET | `/login` | 登录页 |
| GET | `/users` | 用户管理页 |
| GET | `/jobs` | 岗位管理页 |
| GET | `/static/operations.html` | 操作记录页静态入口 |
| GET | `/static/<file>` | 静态资源，如 `app.js`、`jobs.js`、`operations.js`、`styles.css` |
| GET | `/api/healthz` | 健康检查，返回 `{ok, time}` |

说明：

- 页面资源虽然可直接访问，但业务接口除登录外都要求已登录。
- 当前没有单独的 `/operations` 路由，操作记录页通过静态路径访问。

## 3. 认证接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/login` | 登录并写入 Cookie |
| GET | `/api/auth/me` | 获取当前登录用户 |
| PUT | `/api/auth/change-password` | 修改本人密码 |
| POST | `/api/auth/logout` | 退出登录并清空 Cookie |

## 4. 用户与角色接口

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/roles/definitions` | 已登录 | 获取角色定义 |
| GET | `/api/users` | 管理员 | 获取用户列表 |
| GET | `/api/users/options` | 已登录 | 获取活跃用户选项 |
| POST | `/api/users` | 管理员 | 创建用户 |
| PUT | `/api/users/{user_id}` | 管理员 | 更新用户 |
| POST | `/api/users/{user_id}/reset-password` | 管理员 | 重置用户密码 |
| GET | `/api/settings/llm-config` | 管理员 | 查看 LLM 运行配置摘要 |

## 5. 操作记录接口

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/operation-logs` | 管理员 | 获取操作记录列表 |
| GET | `/api/operation-logs/{log_id}` | 管理员 | 获取单条操作记录详情 |
| GET | `/api/operation-logs/export` | 管理员 | 导出操作记录 |

列表与导出支持的筛选参数：

- `keyword`
- `module`
- `operation_type`
- `operator_user_id`
- `operator_name`
- `biz_object_type`
- `biz_object_id`
- `biz_object_name`
- `operation_result`
- `request_source`
- `operated_from`
- `operated_to`
- `format`

`/api/operation-logs/export` 当前支持：

- `format=json`
- `format=csv`

## 6. 岗位接口

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/jobs` | 管理员 / HR / 部门负责人 | 查询岗位列表 |
| POST | `/api/jobs/bulk` | 管理员 / HR | 批量保存岗位 |
| POST | `/api/score-table/preview` | 管理员 / HR | 评分表上传前预览 |
| POST | `/api/jobs/{job_id}/score-table` | 管理员 / HR | 上传岗位评分表 |
| GET | `/api/jobs/{job_id}/score-table` | 管理员 / HR / 部门负责人 | 查看当前生效评分表预览 |
| DELETE | `/api/jobs/{job_id}/score-table/{version_no}` | 管理员 / HR | 删除岗位评分表版本 |

## 7. 候选人与简历接口

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/candidates` | 已登录 | 查询候选人列表 |
| GET | `/api/resumes/{candidate_id}` | 已登录且可见 | 获取简历 PDF |
| POST | `/api/resumes/upload` | 管理员 / HR | 上传 PDF 简历 |
| POST | `/api/resumes/sync` | 管理员 / HR | 同步本地简历目录 |
| DELETE | `/api/candidates/{candidate_id}` | 管理员 / HR | 删除候选人 |
| GET | `/api/interviews/calendar` | 已登录 | 获取面试日历 |

候选人列表支持的常用筛选字段：

- `keyword`
- `job_id`
- `department_scope`
- `stage_status`
- `school`
- `education`
- `duration`
- `score_min`
- `score_max`
- `upload_date`
- `upload_from`
- `upload_to`

## 8. 候选人评估接口

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/evaluations/{candidate_id}` | 已登录且可见 | 查询候选人评估详情 |
| PUT | `/api/evaluations/{candidate_id}/profile` | 可写档案角色 | 更新候选人通用信息 |
| PUT | `/api/evaluations/{candidate_id}/star` | 可见角色 | 更新星标 |
| PUT | `/api/evaluations/{candidate_id}/rounds/{stage}` | 可写轮次角色 | 保存单轮面评 |
| PUT | `/api/evaluations/{candidate_id}` | 可写档案角色 | 同时保存档案与面评 |
| POST | `/api/evaluations/{candidate_id}/transition` | 可推进流程角色 | 推进阶段 |
| POST | `/api/evaluations/{candidate_id}/auto-score` | 已登录且可见 | 重新触发自动评分，优先复用数据库中的简历解析缓存 |
| POST | `/api/evaluations/{candidate_id}/resume-extract` | 已登录且可见 | 重新触发简历结构化抽取，优先复用数据库中的简历解析缓存 |

## 9. 常见错误与权限码

| 状态码 | 错误值 | 说明 |
| --- | --- | --- |
| `400` | `invalid payload` / 各类校验错误 | 请求参数非法 |
| `401` | `unauthorized` | 未登录或 Session 失效 |
| `403` | `forbidden` | 当前角色无权限 |
| `403` | `must_change_password` | 用户必须先修改密码 |
| `403` | `operation_logs_forbidden` | 非管理员访问操作记录接口 |
| `404` | `Not Found` / `job not found` / `operation log not found` | 资源不存在 |

## 10. 当前接口实现特点

1. 认证基于 Cookie Session，不需要前端手工拼 `Authorization`。
2. 文件上传统一使用 `multipart/form-data`。
3. 控制器层通过 `recruitment_service.py` 聚合导出服务函数。
4. 操作记录页是独立静态页面，但数据完全来自后端接口，不是纯前端 mock。
