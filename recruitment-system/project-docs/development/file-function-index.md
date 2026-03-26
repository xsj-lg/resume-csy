# 文件功能索引

本文档按文件整理当前主要 Python 文件的功能入口，重点覆盖控制器、服务和仓储层。第一版以公开函数和主职责为主，不展开每个内部辅助函数的全部细节。

## 1. 启动与分发

### `app/server.py`

- 作用：启动服务进程。
- 入口：
  - 直接启动 `ThreadingHTTPServer`

### `app/backend/controllers/resume_controller.py`

- 作用：统一 HTTP 请求分发。
- 关键入口：
  - `run`
- 内部职责：
  - 处理 GET / POST / PUT / DELETE
  - JSON / multipart 解析
  - Cookie 解析
  - 统一响应输出

## 2. 控制器层

### `app/backend/controllers/system_controller.py`

- 作用：公共页面和健康检查。
- 关键入口：
  - `handle_public_get`

### `app/backend/controllers/auth_controller.py`

- 作用：认证与会话控制。
- 关键入口：
  - `handle_get_auth_me`
  - `handle_put_change_password`
  - `handle_post_login`
  - `handle_post_logout`

### `app/backend/controllers/user_role_controller.py`

- 作用：用户、角色、LLM 配置摘要接口。
- 关键入口：
  - `handle_get_user_role_routes`
  - `handle_put_user_role_routes`
  - `handle_post_user_role_routes`

### `app/backend/controllers/job_controller.py`

- 作用：岗位与评分表接口。
- 关键入口：
  - `handle_get_job_routes`
  - `handle_put_job_routes`
  - `handle_post_job_routes`
  - `handle_delete_job_routes`

### `app/backend/controllers/candidate_controller.py`

- 作用：候选人、简历、评估、流程接口。
- 关键入口：
  - `handle_get_candidate_routes`
  - `handle_put_candidate_routes`
  - `handle_post_candidate_routes`
  - `handle_delete_candidate_routes`
- 辅助函数：
  - 候选人列表调试和上传日期摘要相关函数

### `app/backend/controllers/operation_log_controller.py`

- 作用：操作记录审计接口。
- 关键入口：
  - `handle_get_operation_log_routes`

## 3. 服务层总览

### `app/backend/services/recruitment_service.py`

- 作用：Facade 聚合层。
- 特点：
  - 向控制器统一 re-export 其他 service 的公开能力
  - 不是业务主实现文件

### `app/backend/services/candidate_service.py`

- 作用：兼容聚合 + 通用工具。
- 当前保留的主要函数：
  - `infer_department_scope`
  - `today_dataset_dir`
  - `today_date_tag`
  - `is_uuid_candidate_id`
  - `normalize_date_tag`
  - `infer_inflow_date_from_rel_path`
  - `sanitize_uploaded_filename`
  - `resolve_storage_path`
  - `resolve_job_template_path`
  - `ensure_pdf_content`
  - `utc_now_iso`
  - `now_ts`
  - `execute_sql_with_retry`
  - `json_loads_or_empty_object`
  - `json_loads_or_empty_list`
  - `json_dumps_compact`
  - `parse_job_payload`
- 说明：
  - 大部分候选人相关业务已迁出
  - 当前更多承担兼容导出职责

## 4. 候选人域服务

### `app/backend/services/candidate_query_service.py`

- 作用：候选人查询与列表聚合。
- 关键入口：
  - `parse_candidate_filters`
  - `filter_candidates`
  - `list_candidates`
  - `candidate_map`
  - `list_candidates_for_user`
  - `list_interview_calendar`
  - `list_interview_calendar_for_user`
- 主要功能：
  - 候选人筛选解析
  - 列表聚合
  - 面试日历
  - 按用户可见范围过滤

### `app/backend/services/candidate_command_service.py`

- 作用：候选人命令型操作。
- 关键入口：
  - `sync_resumes_from_storage`
  - `resolve_resume_path`
  - `delete_candidate`
  - `create_candidate_from_upload`
- 主要功能：
  - 扫描本地简历目录
  - 上传创建候选人
  - 删除候选人及关联文件
  - 调度异步抽取和自动评分

### `app/backend/services/candidate_workflow_service.py`

- 作用：候选人权限与流程应用服务。
- 关键入口：
  - `visible_candidate_ids_for_user`
  - `can_access_candidate`
  - `can_upload_resume`
  - `can_sync_resumes`
  - `can_delete_candidate`
  - `can_write_profile`
  - `can_transition_stage`
  - `can_write_round`
  - `get_evaluation`
  - `resolve_profile_job_binding`
  - `transition_stage`
  - `save_profile_only`
  - `save_round_only`
  - `save_star_only`
  - `save_evaluation`
- 主要功能：
  - 候选人权限判断
  - 评估详情聚合
  - 档案和轮次保存
  - 流程推进

### `app/backend/services/candidate_domain_service.py`

- 作用：候选人领域规则。
- 关键入口：
  - `stage_index`
  - `normalize_stage_name`
  - `stage_status_template`
  - `build_stage_statuses`
  - `decode_stage_statuses`
  - `dump_stage_statuses`
  - `parse_interview_datetime`
  - `format_interview_datetime`
  - `derive_interview_status`
  - `validate_profile_payload`
  - `validate_round_payload`
  - `validate_stage_action_payload`
  - `validate_star_payload`
  - `current_active_stage`
- 主要功能：
  - 面试阶段状态机
  - 字段校验
  - 阶段状态序列化/反序列化

## 5. 岗位、评分与 AI

### `app/backend/services/job_service.py`

- 作用：岗位管理。
- 关键入口：
  - `can_view_jobs`
  - `can_manage_jobs`
  - `list_jobs_for_user`
  - `replace_jobs_from_client`
  - `upload_job_score_table`
  - `delete_job_score_table_version`
  - `get_job_score_table_preview`
- 主要功能：
  - 岗位列表与保存
  - 评分表版本维护
  - 岗位日志追加

### `app/backend/services/score_table_service.py`

- 作用：评分表解析和评分项整理。
- 关键入口：
  - `sanitize_score_template_filename`
  - `normalize_score_table_preview_payload`
  - `parse_score_table_preview`
  - `score_to_float`
  - `normalize_score_item`
  - `calculate_score_items_max_score`
  - `dedupe_score_items_for_prompt`
  - `format_score_table_for_prompt`
  - `build_score_items_from_templates`
  - `build_job_snapshot`
- 主要功能：
  - CSV/XLS/XLSX 解析
  - 评分表预览
  - 评分项标准化
  - Prompt 压缩格式生成

### `app/backend/services/auto_score_service.py`

- 作用：自动评分主链路。
- 关键入口：
  - `calculate_match_level`
  - `score_with_fallback_rules`
  - `normalize_llm_auto_score_output`
  - `call_llm_auto_score`
  - `normalize_llm_score_payload`
  - `load_auto_score_by_candidate`
  - `save_auto_score`
  - `trigger_auto_score_for_candidate`
- 主要功能：
  - LLM 自动评分
  - 规则降级评分
  - 评分结果标准化与落库

### `app/backend/services/resume_extract_service.py`

- 作用：简历结构化抽取。
- 关键入口：
  - `extract_pdf_text`
  - `normalize_resume_structured_payload`
  - `extract_and_store_resume_profile`
  - `trigger_resume_extract_for_candidate`
- 主要功能：
  - PDF 文本提取
  - 简历结构化归一化
  - 调用 LLM 抽取并回写候选人档案

### `app/backend/services/llm_service.py`

- 作用：LLM 基础能力。
- 关键入口：
  - `resolve_config_path`
  - `safe_read_json`
  - `resolve_llm_api_key`
  - `load_llm_runtime_config`
  - `public_llm_runtime_config`
  - `load_active_prompt`
  - `parse_llm_json_response`
  - `call_llm_chat_stream`
  - `render_prompt_template`

## 6. 用户、数据库与审计

### `app/backend/services/role_user_service.py`

- 作用：用户、角色和会话。
- 关键入口：
  - `list_role_definitions`
  - `list_users`
  - `list_active_user_options`
  - `get_user_by_id`
  - `get_user_by_username`
  - `create_session`
  - `delete_session`
  - `get_current_user_by_session`
  - `create_user`
  - `update_user`
  - `reset_user_password`
  - `change_password`
  - `validate_login_payload`
  - `validate_change_password_payload`
- 主要功能：
  - 用户管理
  - 密码管理
  - 角色和部门范围处理
  - Session 管理

### `app/backend/services/db_service.py`

- 作用：数据库初始化与历史迁移。
- 关键入口：
  - `has_table`
  - `has_column`
  - `init_db`
  - `migrate_legacy_data`
  - `scan_all_pdf_files`
  - `migrate_candidate_identity`
  - `migrate_candidate_id_to_uuid`
  - `migrate_candidate_file_inflow_date`
  - `migrate_stage_status_model`
  - `migrate_round_stage_names`

### `app/backend/services/operation_log_service.py`

- 作用：操作记录审计。
- 关键入口：
  - `ensure_operation_log_table`
  - `client_ip_from_handler`
  - `request_source_from_handler`
  - `record_operation_log`
  - `record_operation_log_from_request`
  - `can_view_operation_logs`
  - `parse_operation_log_filters`
  - `list_operation_logs`
  - `get_operation_log`
  - `export_operation_logs`

## 7. Repository 层

### `app/backend/repositories/sqlite_helpers.py`

- 作用：SQLite 连接工厂。
- 关键入口：
  - `connect_db`

### `app/backend/repositories/candidate_repository.py`

- 作用：候选人仓储。
- 关键入口：
  - `list_candidate_file_rows`
  - `get_candidate_file_by_id`
  - `get_candidate_file_by_original_filename`
  - `parse_candidate_from_filename`
  - `default_profile`
  - `default_round`
  - `insert_profile_if_missing`
  - `seed_candidate_profiles`
  - `profile_summaries`
  - `load_profile`
  - `load_rounds`

## 8. 阅读顺序建议

1. 先看 [file-structure-inventory.md](/d:/AIS/code/AIS/python/recruitment-system/project-docs/development/file-structure-inventory.md) 了解文件位置。
2. 再看 [project-structure-and-module-spec.md](/d:/AIS/code/AIS/python/recruitment-system/project-docs/development/project-structure-and-module-spec.md) 了解模块边界。
3. 然后按本索引定位具体文件和公开入口。

## 9. 第一版限制

1. 当前以公开函数和主要职责为主，没有逐个展开所有内部辅助函数。
2. `web/*.js` 的函数级索引尚未细化。
3. 后续若需要更细粒度，可以继续补“前端函数索引”和“控制器路由映射表”。
