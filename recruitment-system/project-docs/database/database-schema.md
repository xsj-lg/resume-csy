# 数据库表结构文档

本文档基于当前仓库的 `db_service.init_db()` 初始化逻辑、`operation_log_service.ensure_operation_log_table()` 以及现有服务读写路径整理，数据库类型为 SQLite。

## 1. 基本信息

| 项目 | 当前实现 |
| --- | --- |
| 数据库文件 | `data/recruitment.sqlite3` |
| 数据库类型 | SQLite |
| 连接方式 | Python `sqlite3` |
| Journal 模式 | 优先启用 `WAL` |
| Synchronous | `NORMAL` |
| 自动初始化入口 | `app/backend/services/db_service.py:init_db()` |

说明：

- 系统启动时会自动创建缺失表，并对部分历史字段执行增量迁移。
- 当前没有显式启用外键约束，表间关系主要由业务代码保证。
- 主键多为 `TEXT`，候选人和用户 ID 由系统生成随机/UUID 风格字符串。

## 2. 表清单

当前数据库包含 8 张核心表：

| 表名 | 用途 | 主键 |
| --- | --- | --- |
| `users` | 系统用户与角色信息 | `id` |
| `user_sessions` | 登录会话 | `session_token` |
| `jobs` | 岗位配置与评分表版本 | `job_id` |
| `candidate_files` | 简历文件入库记录 | `candidate_id` |
| `candidate_profiles` | 候选人档案与流程主表 | `candidate_id` |
| `interview_round_notes` | 分轮面评记录 | `(candidate_id, stage)` |
| `candidate_auto_scores` | 自动评分历史 | `score_id` |
| `operation_logs` | 操作记录审计表 | `log_id` |

## 3. 表结构说明

### 3.1 `users`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `TEXT` | 用户主键 |
| `username` | `TEXT` | 登录用户名，唯一 |
| `display_name` | `TEXT` | 显示名 |
| `password_hash` | `TEXT` | PBKDF2-SHA256 哈希 |
| `is_active` | `INTEGER` | 是否启用，0/1 |
| `is_admin` | `INTEGER` | 是否管理员，0/1 |
| `role_code` | `TEXT` | 角色码，如 `administrator` |
| `department_scope` | `TEXT` | 部门负责人对应的部门范围 |
| `must_change_password` | `INTEGER` | 是否首次登录必须改密 |
| `created_at` | `TEXT` | 创建时间 |
| `updated_at` | `TEXT` | 更新时间 |

### 3.2 `user_sessions`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `session_token` | `TEXT` | Session 主键 |
| `user_id` | `TEXT` | 对应用户 ID |
| `expires_at` | `INTEGER` | 过期时间戳（秒） |
| `created_at` | `TEXT` | 创建时间 |

### 3.3 `jobs`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `job_id` | `TEXT` | 岗位主键 |
| `job_code` | `TEXT` | 岗位编码，唯一 |
| `title` | `TEXT` | 岗位名称 |
| `department` | `TEXT` | 所属部门 |
| `headcount` | `INTEGER` | 招聘人数 |
| `location` | `TEXT` | 工作地点 |
| `recruiter_user_id` | `TEXT` | 招聘负责人 |
| `hiring_manager_user_id` | `TEXT` | 用人经理 |
| `jd` | `TEXT` | 岗位说明 |
| `requirements` | `TEXT` | 任职要求 |
| `process_json` | `TEXT` | 固定流程评价要求 JSON |
| `criteria_json` | `TEXT` | 筛选标准 JSON |
| `templates_json` | `TEXT` | 评分表版本列表 JSON |
| `active_template_version` | `INTEGER` | 当前生效评分表版本 |
| `score_table_storage_rel_path` | `TEXT` | 当前生效评分表相对路径 |
| `auto_score_enabled` | `INTEGER` | 是否启用自动评分 |
| `status` | `TEXT` | `open` / `closed` |
| `logs_json` | `TEXT` | 岗位内关键操作日志 JSON |
| `created_at` | `TEXT` | 创建时间 |
| `updated_at` | `TEXT` | 更新时间 |
| `closed_at` | `TEXT` | 关闭时间 |

### 3.4 `candidate_files`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `candidate_id` | `TEXT` | 候选人主键 |
| `candidate_name` | `TEXT` | 候选人名称 |
| `original_filename` | `TEXT` | 原始文件名 |
| `storage_rel_path` | `TEXT` | 相对 `data/cv/ais/` 的存储路径 |
| `inflow_date` | `TEXT` | 简历流入日期标签，通常为 `YYYYMMDD` |
| `uploaded_at` | `TEXT` | 上传时间 |
| `uploaded_by` | `TEXT` | 上传人用户 ID |
| `is_active` | `INTEGER` | 是否有效 |

### 3.5 `candidate_profiles`

这是候选人业务主表，承载档案、岗位绑定、阶段状态和结构化抽取结果。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `candidate_id` | `TEXT` | 候选人主键 |
| `base_location` | `TEXT` | Base |
| `salary_mode` | `TEXT` | 月薪 / 年包 |
| `salary_range` | `TEXT` | 薪资区间 |
| `experience_type` | `TEXT` | 应届生 / 已工作 |
| `graduation_year` | `TEXT` | 毕业年份 |
| `work_years` | `TEXT` | 工作年限 |
| `hire_type` | `TEXT` | 实习 / 正式 |
| `preset_position` | `TEXT` | 预设岗位文本 |
| `highest_education` | `TEXT` | 最高学历 |
| `school_name` | `TEXT` | 学校名称 |
| `applied_position` | `TEXT` | 申请岗位 |
| `department_scope` | `TEXT` | 所属部门 |
| `job_ref_id` | `TEXT` | 当前关联岗位引用 ID |
| `job_id` | `TEXT` | 岗位 ID（兼容字段） |
| `job_code` | `TEXT` | 岗位编码 |
| `job_title` | `TEXT` | 岗位名称 |
| `job_snapshot_json` | `TEXT` | 冻结的岗位快照 |
| `resume_structured_json` | `TEXT` | 简历结构化抽取结果 |
| `resume_extract_status` | `TEXT` | 抽取状态 |
| `resume_extract_source` | `TEXT` | 抽取来源 |
| `resume_extract_model` | `TEXT` | 抽取使用模型 |
| `resume_extract_error` | `TEXT` | 抽取错误信息 |
| `resume_extract_updated_at` | `TEXT` | 抽取更新时间 |
| `current_stage` | `TEXT` | 当前阶段 |
| `stage_closed_from` | `TEXT` | 若流程终止，从哪个阶段结束 |
| `stage_status_json` | `TEXT` | 各阶段状态 JSON |
| `is_starred` | `INTEGER` | 是否星标 |
| `terminated_at` | `TEXT` | 终止时间 |
| `updated_at` | `TEXT` | 更新时间 |

### 3.6 `interview_round_notes`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `candidate_id` | `TEXT` | 候选人 ID |
| `stage` | `TEXT` | 阶段名，联合主键之一 |
| `interview_time` | `TEXT` | 面试时间 |
| `interviewer_user_id` | `TEXT` | 面试人用户 ID |
| `planned_questions` | `TEXT` | 拟提问 |
| `interview_review` | `TEXT` | 面评内容 |
| `updated_at` | `TEXT` | 更新时间 |

### 3.7 `candidate_auto_scores`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `score_id` | `TEXT` | 评分记录主键 |
| `candidate_id` | `TEXT` | 候选人 ID |
| `score_source` | `TEXT` | `llm` / `fallback` |
| `score_status` | `TEXT` | `success` / `failed` 等 |
| `model_name` | `TEXT` | 模型名 |
| `prompt_id` | `TEXT` | Prompt ID |
| `total_score` | `REAL` | 总分 |
| `max_score` | `REAL` | 满分 |
| `match_level` | `TEXT` | 匹配等级 |
| `summary` | `TEXT` | 总结 |
| `risk_flags_json` | `TEXT` | 风险提示数组 |
| `dimension_scores_json` | `TEXT` | 维度得分数组 |
| `error_message` | `TEXT` | 错误信息 |
| `created_at` | `TEXT` | 评分时间 |

### 3.8 `operation_logs`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `log_id` | `TEXT` | 日志主键 |
| `operation_module` | `TEXT` | 操作模块 |
| `operation_type` | `TEXT` | 操作类型 |
| `biz_object_type` | `TEXT` | 业务对象类型 |
| `biz_object_id` | `TEXT` | 业务对象 ID |
| `biz_object_name` | `TEXT` | 业务对象名称 |
| `operator_user_id` | `TEXT` | 操作人用户 ID |
| `operator_name` | `TEXT` | 操作人名称 |
| `operated_at` | `TEXT` | 操作时间 |
| `operation_result` | `TEXT` | `success` / `failed` |
| `client_ip` | `TEXT` | 客户端 IP |
| `request_source` | `TEXT` | 请求来源 |
| `remark` | `TEXT` | 备注 |
| `extra_context_json` | `TEXT` | 扩展上下文 JSON |
| `created_at` | `TEXT` | 创建时间 |

## 4. 索引

当前显式创建的索引：

| 索引名 | 表 | 字段 |
| --- | --- | --- |
| `idx_candidate_files_original_filename_nocase` | `candidate_files` | `original_filename COLLATE NOCASE` |
| `idx_jobs_updated_at` | `jobs` | `updated_at DESC` |
| `idx_candidate_auto_scores_candidate_created` | `candidate_auto_scores` | `(candidate_id, created_at DESC)` |
| `idx_candidate_profiles_job_ref_id` | `candidate_profiles` | `job_ref_id` |
| `idx_operation_logs_operated_at` | `operation_logs` | `operated_at DESC` |
| `idx_operation_logs_operator_user_id` | `operation_logs` | `operator_user_id` |
| `idx_operation_logs_module_type` | `operation_logs` | `(operation_module, operation_type)` |
| `idx_operation_logs_object` | `operation_logs` | `(biz_object_type, biz_object_id)` |

另外，由主键和唯一约束天然形成的索引包括：

- `users.username`
- `jobs.job_code`
- `candidate_files.original_filename`
- `candidate_files.storage_rel_path`
- `interview_round_notes(candidate_id, stage)`

## 5. 逻辑关系

| 主体 | 关系 | 客体 |
| --- | --- | --- |
| `users` | 1:N | `user_sessions` |
| `jobs` | 1:N | `candidate_profiles`（通过 `job_ref_id/job_id` 逻辑关联） |
| `candidate_files` | 1:1 | `candidate_profiles` |
| `candidate_profiles` | 1:N | `interview_round_notes` |
| `candidate_profiles` | 1:N | `candidate_auto_scores` |
| 各业务对象 | 1:N | `operation_logs`（按对象类型和对象 ID 逻辑关联） |

说明：

- 候选人与岗位关联同时保留了 `job_ref_id` 和 `job_id` 两套兼容字段，查询时优先使用 `job_ref_id`。
- `operation_logs` 不使用外键约束，而是由业务代码在写日志时保留对象标识和可读名称。

## 6. 初始化与迁移特点

1. 启动时由 `db_service.init_db()` 自动补齐缺失表和字段。
2. 历史兼容迁移仍然保留在代码中，包括候选人 ID、流入日期、阶段状态模型和轮次名称迁移。
3. 操作记录表由 `operation_log_service.ensure_operation_log_table()` 保证存在，并在初始化时一并创建索引。
