# 业务术语定义

## 0. 文档信息

- 当前版本: `0.1.15`
- 对应平台版本: `0.1.15`
- 作用: 定义业务术语、枚举与流程语义，作为需求与实现统一语义基线。
- GOVERNED_BY: `docs/00-governance/gov-02-requirements.md`

### 最近更新（最新 5 条）

| date | version | 对应平台版本 | summary |
| --- | --- | --- | --- |
| `2026-03-26` | `0.1.15` | `0.1.15` | 1. 回填操作记录审计语义：统一日志记录表、日志详情比对、筛选导出与只读审计边界。<br>2. 回填工作台最近查看恢复语义：跨页返回时恢复上次查看候选人/简历上下文并支持安全降级。<br>3. 回填自动评分明细复核语义：评分项得分累加校验维度分和总分，并展示证据与置信度。<br>4. 回填分段评分表解析术语与协作治理补充语义。<br>5. 明确用户确认“已发布完成”时必须同步完成状态迁移。 |
| `2026-03-24` | `0.1.14` | `0.1.14` | 1. 回填自动评分输入收敛语义：评分表规范化、结构化候选人信息优先入模、阈值策略与严格 JSON 输出约束。<br>2. 回填候选人高级筛选语义：流程状态、学校、学历、年限、评分区间与上传日期筛选口径。<br>3. 回填 `v0.1.14` 发布闭环：`REQ-v0.1.14-001/002` 已归档到 `roadmap-01` 并完成事实回填。 |
| `2026-03-24` | `0.1.13` | `0.1.13` | 1. 回填“结构化抽取与通用信息融合展示”术语：统一通用信息主展示口径与同口径去重规则。<br>2. 回填字段映射与刷新语义：抽取结果按映射回填通用信息并由“更新抽取”驱动同步刷新。<br>3. 回填兼容边界语义：历史无结构化数据与抽取失败场景均按通用信息可用优先。<br>4. 对齐历史归档表述：`0.1.9/0.1.10/0.1.11` 相关术语已按已完成状态归档到 `roadmap-01`。 |
| `2026-03-18` | `0.1.12` | `0.1.12` | 1. 回填岗位管理语义：岗位生命周期操作（新增/编辑/查看/关闭/复制）与岗位基础信息字段。<br>2. 回填岗位评分语义：评分表版本管理、生效控制、自动评分启停与评分结果结构。<br>3. 回填岗位关联上传语义：上传简历必须绑定岗位，并写入 `job_id/job_code/job_title` 与岗位快照。<br>4. 回填后端分层语义：后端拆分为控制层/服务层/数据库交互层/工具层，`app/server.py` 仅保留启动入口职责。<br>5. 补齐 `0.1.11` 已发布语义：上传/筛选部门维度与 PDF 核心信息识别。 |
| `2026-03-17` | `0.1.10` | `0.1.10` | 1. 回填用户管理编辑语义：用户编辑入口支持显示名、状态、角色与部门范围统一编辑。<br>2. 回填角色编码语义：用户角色统一为 `administrator/hr_specialist/interviewer/hiring_manager`。<br>3. 回填部门范围语义：限定 `销售部/研发部/算法部/项目部/人事部`，并约束部门负责人必填。 |

## 1. 核心术语定义

| term_code | name_zh | desc_zh |
| --- | --- | --- |
| `Project` | 项目 | 业务目标和交付范围的管理边界。 |
| `Requirement` | 需求条目 | 版本内可追踪、可执行、可验收的最小需求单位。 |
| `Release` | 发布 | 达成目标版本并完成回填后的可对外宣告状态。 |

## 2. 枚举定义总则

- 稳定值统一使用英文大写 `SNAKE_CASE`。
- 新增枚举先更新本文档，再进入代码实现。

## 3. 示例枚举

### 3.1 `requirement_status`

| code | name_zh | desc_zh |
| --- | --- | --- |
| `DRAFT` | 讨论中 | 需求仍在讨论，尚未进入执行。 |
| `CONFIRMED` | 已确认 | 需求可进入执行平移。 |
| `DEFERRED` | 延后 | 延后到后续版本。 |
| `REJECTED` | 否决 | 不进入执行。 |

### 3.2 `candidate_evaluation_fields`（简历人工录入字段）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `base_location` | Base 工作地 | `北京` / `深圳` | 候选人拟入职工作地，仅允许二选一。 |
| `salary_mode` | 意向薪资模式 | `月薪` / `年包` | 薪资录入的计量方式。 |
| `salary_range` | 意向薪资区间 | 区间字符串（如 `30k-40k`、`45w-60w`） | 必须使用区间表达。 |
| `experience_type` | 候选人类型 | `应届生` / `已工作` | 决定填写“预期毕业年限”或“工作年限”。 |
| `hire_type` | 拟录取形式 | `实习` / `正式` | 录用形态枚举。 |

### 3.3 `interview_stage_workflow`（面试流程语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `interview_stage` | 面试阶段节点 | `初筛` / `一面` / `二面` / `HR面` | 固定四阶段节点。 |
| `stage_status` | 阶段节点状态 | `pending` / `passed` / `ended` / `active`(UI态) | `pending`=未到达(灰)，`passed`=通过(绿)，`ended`=该节点结束(红)，`active`=当前进行中未完成(红)。 |
| `stage_action` | 阶段操作 | `next` / `end` / `reset` | `next` 进入下一阶段（`HR面` 节点显示为 `通过面试`），`end` 在当前阶段结束（按钮文案为 `未通过X`），`reset` 重置阶段状态且不清空轮次面评数据。 |
| `save_scope` | 保存范围 | `round_only` / `profile_only` | 阶段面评信息与候选人通用信息分离保存。 |
| `stage_interviewer_user_id` | 阶段面试人 | 有效用户 `id` 或空值 | 每个阶段可分配一位系统内可用用户作为面试人。 |

### 3.4 `candidate_list_stage_and_sort`（左侧候选人语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `candidate_interview_status` | 候选人面试状态 | `待初筛` / `待一面` / `待二面` / `待HR面` / `通过` / `未通过初筛` / `未通过一面` / `未通过二面` / `未通过HR面` | 左侧候选人状态标签，独立于右侧阶段节点状态。 |
| `is_starred` | 星标状态 | `0` / `1` | `1` 表示星标候选人，默认排序优先。 |
| `candidate_sort_mode` | 候选人排序方式 | `star_time` / `time` / `name` | 默认 `star_time`：星标优先，再按最近面试时间优先。 |
| `show_all_candidates` | 显示范围开关 | `false` / `true` | 默认 `false` 隐藏所有 `未通过X` 候选人；`true` 显示全部候选人。 |
| `failed_sort_rule` | 未通过候选人排序规则 | `terminated_at desc` | 在“显示全部”视图中，未通过候选人按终止时间倒序展示。 |

### 3.5 `interview_calendar`（面试日历语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `calendar_scope` | 日历展示范围 | `future_only` | 仅展示未来安排，不展示历史记录。 |
| `calendar_sort_rule` | 日历排序规则 | `nearest_first` | 按离当前时间最近优先排序。 |
| `calendar_item_format` | 日历条目格式 | `<候选人>-<轮次>-<时间>` | 统一条列格式，例如：`张三-二面-2026-03-05 14:00`。 |

### 3.6 `auth_and_user_management`（登录与用户管理语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `auth_mode` | 登录态模式 | `cookie_session` | 使用服务端会话，浏览器 Cookie 持有会话标识。 |
| `must_change_password` | 首登改密标识 | `0` / `1` | `1` 表示用户必须先修改密码后方可进入业务页面。 |
| `user_role_code` | 用户角色编码 | `administrator` / `hr_specialist` / `interviewer` / `hiring_manager` | 用户主角色编码，决定用户管理与业务页面权限边界。 |
| `user_status` | 用户状态 | `active` / `disabled` | `disabled` 用户不可登录。 |
| `department_scope` | 部门范围 | `销售部` / `研发部` / `算法部` / `项目部` / `人事部` | 用于部门负责人数据范围控制；非部门负责人角色不生效。 |
| `department_scope_required_rule` | 部门范围必填规则 | `required_when_hiring_manager` | 当 `user_role_code=hiring_manager` 时必须填写部门范围。 |
| `registration_policy` | 注册策略 | `disabled` | 系统不提供用户自注册入口与接口。 |

### 3.7 `resume_ingestion_and_lifecycle`（简历导入与生命周期语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `candidate_id_strategy` | 候选人主键策略 | `uuid32` | 候选人统一使用 32 位十六进制 UUID，避免文件名耦合。 |
| `resume_storage_layout` | 简历存储目录规则 | `data/cv/ais/YYYYMMDD/` | 简历文件按日期目录本地落盘。 |
| `upload_conflict_policy` | 上传冲突策略 | `global_filename_unique_reject` | 任意日期目录出现同名 PDF 均拒绝上传。 |
| `candidate_delete_mode` | 候选人删除模式 | `hard_delete` | 删除候选人时联动删除映射、档案、轮次记录及本地 PDF。 |
| `resume_sync_mode` | 目录同步模式 | `manual_sync` | 通过手动按钮/API 触发目录扫描入库，不依赖重启服务。 |

### 3.8 `resume_inflow_and_batch_upload`（流入日期与批量上传语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `resume_inflow_date_format` | 简历流入日期格式 | `YYYYMMDD`（存储）/`YYYY-MM-DD`（展示） | 存储层使用 `YYYYMMDD`，候选人列表展示层使用 `YYYY-MM-DD`。 |
| `resume_inflow_date_fallback` | 流入日期回退策略 | `infer_from_storage_dir_or_today` | 优先从 `storage_rel_path` 的日期目录推断，无法推断则回退到当日。 |
| `batch_upload_mode` | 批量上传模式 | `frontend_multi_file_sequential` | 前端上传弹框支持多文件，逐个提交并允许部分成功。 |
| `batch_upload_result_policy` | 批量上传结果策略 | `success_failure_summary` | 上传结束后输出成功/失败数量与失败原因摘要。 |
| `candidate_list_inflow_tag` | 左侧流入日期标签 | `date_only_or_unknown` | 左侧候选人标签区仅显示日期文本（或 `未知`），不带前缀文案。 |

### 3.9 `candidate_filtering_and_left_panel_layout`（筛选与左栏排版语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `candidate_name_filter_mode` | 候选人名称筛选模式 | `fuzzy` | 名称筛选采用模糊匹配（包含关系）。 |
| `applied_position_filter_mode` | 申请岗位筛选模式 | `fuzzy` / `exact` | 岗位支持模糊匹配与精确匹配。 |
| `candidate_filter_logic` | 多条件组合逻辑 | `and` | 名称与岗位同时输入时按交集过滤。 |
| `candidate_filter_reset_behavior` | 筛选重置行为 | `clear_then_reload_default` | 重置后清空全部筛选条件并恢复默认候选人列表。 |
| `candidate_count_display_mode` | 候选人数量展示口径 | `visible_filtered_total` | 显示可见数、筛选结果数与全量数，并标识隐藏未通过数量。 |
| `sort_control_layout_mode` | 排序控件布局模式 | `header_dropdown` | 排序方式入口位于左栏头部，使用下拉菜单选择。 |
| `left_panel_collapsible_sections` | 左栏可折叠区块 | `filter` / `calendar` | 左栏中的筛选区和面试日历支持展开/收起。 |

### 3.10 `job_management_and_auto_scoring`（岗位管理与自动评分语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `job_lifecycle_action` | 岗位生命周期操作 | `create` / `edit` / `view` / `close` / `copy` | 岗位管理支持新增、编辑、查看、关闭和复制。 |
| `job_owner_fields` | 岗位责任人字段 | `recruiter_user_id`(required) / `hiring_manager_user_id`(optional) | 招聘负责人必填，用人经理可选。 |
| `job_binding_on_upload` | 上传岗位绑定策略 | `required` | 上传简历时必须选择岗位并写入岗位标识。 |
| `job_binding_fields` | 候选人岗位关联字段 | `job_id` / `job_code` / `job_title` / `job_snapshot_json` | 候选人档案中持久化岗位关联与岗位快照。 |
| `score_template_file_type` | 评分表文件类型 | `xlsx` / `xls` / `csv` | 岗位评分表支持多版本上传与生效控制。 |
| `score_template_version_mode` | 评分表版本策略 | `multi_version_one_active` | 同一岗位可维护多版本评分表，且仅一个生效版本。 |
| `auto_score_switch` | 自动评分开关 | `enabled` / `disabled` | 岗位维度配置自动评分启停。 |
| `candidate_auto_score_source` | 自动评分来源 | `llm` / `fallback` | 优先 LLM 评分；失败时降级规则评分。 |
| `candidate_auto_score_fields` | 自动评分结果字段 | `total_score` / `max_score` / `match_level` / `dimension_scores` / `risk_flags` / `summary` | 候选人详情回显自动评分结构化结果。 |
| `auto_score_trigger_mode` | 自动评分触发方式 | `upload_auto` / `manual_retrigger` | 上传后自动触发，支持工作台手动重评。 |
| `job_audit_action` | 岗位审计动作 | `template_upload` / `template_replace` / `auto_score_toggle` / `score_trigger` | 关键操作需要记录用于追溯与审计。 |

### 3.11 `backend_layered_architecture`（后端分层架构语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `backend_layer_scope` | 后端分层目录 | `controllers` / `services` / `repositories` / `utils` | 后端代码按职责拆分为控制层、服务层、数据库交互层、工具层。 |
| `server_entry_mode` | 启动入口模式 | `thin_entrypoint` | `app/server.py` 仅负责导入并执行 `run`，不承载业务实现。 |
| `controller_responsibility` | 控制层职责 | `http_routing_and_response` | 控制层负责 HTTP 路由分发、请求解析与响应输出。 |
| `service_responsibility` | 服务层职责 | `business_orchestration` | 服务层负责业务规则、流程编排与领域逻辑处理。 |
| `repository_responsibility` | 数据库交互层职责 | `sqlite_access_helpers` | 数据库交互层提供 SQLite 连接与通用访问辅助能力。 |
| `utility_responsibility` | 工具层职责 | `shared_runtime_helpers` | 工具层提供时间等可复用的通用函数。 |

### 3.12 `department_scope_resume_flow`（上传与筛选部门维度语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `upload_department_scope` | 上传部门字段 | `销售部` / `研发部` / `算法部` / `项目部` / `人事部` | 上传简历时可选择部门并写入候选人档案。 |
| `candidate_department_filter` | 候选人部门筛选 | `department_scope` | 候选人列表支持按部门筛选。 |
| `hiring_manager_filter_visibility` | 部门负责人筛选可见性 | `hidden` | 部门负责人角色不显示部门筛选控件。 |
| `candidate_department_edit_permission` | 候选人部门编辑权限 | `administrator` / `hr_specialist` | 管理员与 HR 可修改候选人部门并保存生效。 |

### 3.13 `pdf_core_info_extraction`（PDF 核心信息识别语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `pdf_parse_source` | PDF 解析来源 | `local_pdf_text_pipeline` | 使用本地解析链路提取 PDF 文本信息。 |
| `pdf_extracted_fields` | 核心识别字段 | `school_name` / `phone_number` / `email` | 自动识别学校、电话、邮箱并写入候选人档案。 |
| `pdf_extraction_failure_policy` | 识别失败策略 | `upload_not_blocked` | 识别失败不阻塞上传流程，字段允许后续人工补录。 |
| `pdf_profile_editability` | 识别字段可编辑性 | `editable` | 已识别字段支持人工修改并持久化回显。 |

### 3.14 `structured_profile_general_info_merge`（结构化抽取与通用信息融合语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `profile_display_fact_source` | 主展示事实源 | `general_info_only` | 候选人详情页以“通用信息”为唯一主展示区域，不再并列展示同口径结构化块。 |
| `profile_field_mapping_mode` | 字段映射模式 | `structured_to_general_info` | 结构化抽取字段按映射关系回填通用信息字段并保持口径一致。 |
| `profile_update_trigger` | 抽取刷新触发 | `manual_refresh_then_sync` | 触发“更新抽取”后，同步刷新通用信息展示与保存态数据。 |
| `profile_compatibility_policy` | 历史兼容策略 | `fallback_to_existing_general_info` | 历史无结构化数据时按现有通用信息展示，不中断业务流程。 |
| `profile_extraction_failure_policy` | 抽取失败策略 | `keep_general_info_and_show_status` | 抽取失败时保留既有通用信息，并展示失败状态提示。 |

### 3.15 `candidate_auto_score_input_contract`（自动评分输入收敛语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `score_table_normalization_mode` | 评分表规范化策略 | `dimension_point_criterion_aggregate` | 评分表入模前按维度/评估点/标准聚合，去除重复规则并保留分值。 |
| `score_candidate_fact_source` | 候选人评分事实源 | `structured_profile_first` | 自动评分优先使用结构化候选人信息组织输入，`resume_text` 仅作缺失字段补充。 |
| `score_threshold_strategy` | 评分阈值策略 | `request_thresholds_with_conservative_fallback` | 请求显式携带强推/推荐/复核阈值，并在字段缺失时按保守策略降级。 |
| `score_output_contract` | 评分输出契约 | `strict_json` | 模型返回必须为可解析严格 JSON，至少包含总分、维度得分、评分依据、风险提示和推荐结论。 |

### 3.16 `candidate_advanced_filters`（候选人高级筛选语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `candidate_stage_status_filter` | 流程状态筛选 | `stage_status` | 候选人列表支持按当前流程状态筛选。 |
| `candidate_school_filter` | 学校筛选 | `school` | 候选人列表支持按学校名称筛选。 |
| `candidate_education_filter` | 学历筛选 | `education` | 候选人列表支持按学历枚举筛选。 |
| `candidate_duration_filter` | 年限筛选 | `duration` | 候选人列表支持按工作/经历年限筛选。 |
| `candidate_score_range_filter` | 评分区间筛选 | `score_min` / `score_max` | 候选人列表支持按总分区间筛选。 |
| `candidate_upload_date_filter` | 上传日期筛选 | `upload_date` / `uploaded_from` / `uploaded_to` | 候选人列表支持按上传日期下拉或自定义区间筛选。 |

### 3.17 `sectioned_score_template_parsing`（分段评分表解析语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `score_template_layout_mode` | 评分表版式 | `flat_header` / `sectioned_dimension_rows` | 评分表支持平铺表头版式和“维度标题行 + 评分项行 + 续行标准”分段版式。 |
| `score_template_dimension_row_rule` | 维度标题行识别规则 | `dimension_title_only` | 当某行仅包含维度标题且评分标准/分值列为空时，该行视为维度分段起点。 |
| `score_template_point_inheritance_rule` | 评分项继承规则 | `inherit_last_dimension_and_point` | 当续行标准所在行的维度列为空时，继承最近一次有效的维度与评分项归属。 |
| `score_template_preview_contract` | 评分表预览输出契约 | `headers` / `rows` / `dimensions` | 评分表预览继续输出既有结构，`dimensions` 内保留 `dimension/point/criterion/score` 关系。 |

### 3.18 `agent_collaboration_documentation_governance`（协作执行与文档同步语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `agent_startup_read_rule` | 开工重读规则 | `read_docs_index_then_reread_governance` | Agent 每次执行前先读取 `docs/docs-index.md`，再完整重读 `docs/00-governance/` 当前生效治理文档。 |
| `project_docs_sync_trigger` | `project-docs` 同步触发条件 | `required_on_project_file_change` | 涉及代码文件或其他项目文件新增、修改、删除时，必须同步判断并更新受影响的 `project-docs` 描述。 |
| `project_docs_mapping_source` | `project-docs` 映射依据 | `development_guidelines_section_10` | `project-docs` 同步目标文档优先以 `project-docs/development/development-and-integration-guidelines.md` 第 10 节为准；若映射不足，需显式说明缺口或阻塞。 |
| `delivery_sync_disclosure` | 交付披露要求 | `must_state_project_docs_sync_status` | 每次交付必须说明 `project-docs` 是否已同步更新；未同步时必须说明原因。 |

### 3.19 `operation_log_audit_center`（操作记录审计中心语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `operation_log_visibility` | 操作记录可见范围 | `administrator_only` | 操作记录页和相关接口默认仅管理员可见。 |
| `operation_log_storage_mode` | 操作记录存储模式 | `unified_operation_logs_table` | 关键业务操作统一写入独立日志表，作为系统级审计事实源。 |
| `operation_log_compare_mode` | 日志比对模式 | `same_object_previous_record_diff` | 日志详情支持与同一业务对象的上一条记录做关键字段高亮比对。 |
| `operation_log_export_mode` | 日志导出模式 | `json` / `csv` | 支持导出当前筛选结果及单条日志详情。 |

### 3.20 `workspace_last_view_restore`（工作台最近查看恢复语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `workspace_last_selection_storage` | 最近查看存储方式 | `local_storage_candidate_id` | 工作台在前端持久化保存最近查看的候选人标识。 |
| `workspace_last_selection_restore` | 最近查看恢复策略 | `restore_if_visible_else_safe_fallback` | 返回工作台时优先恢复上次查看候选人；若已删除或不可见，则回退到首条可用记录或空态。 |
| `workspace_last_selection_scope` | 最近查看恢复范围 | `selection_detail_preview` | 恢复范围覆盖候选人选中态、详情区与简历预览区。 |

### 3.21 `auto_score_itemized_review`（自动评分明细复核语义）

| field | name_zh | allowed_values | desc_zh |
| --- | --- | --- | --- |
| `auto_score_total_validation_mode` | 自动评分总分校验方式 | `sum_item_scores` | 当存在评分项明细时，维度分与总分按评分项得分累加计算。 |
| `auto_score_detail_display_scope` | 自动评分明细展示范围 | `all_dimension_items` | 工作台展示所有维度及其下全部评分项，而非仅展示维度汇总。 |
| `auto_score_detail_fields` | 自动评分明细字段 | `item_score` / `reason` / `criterion` / `evidence` / `confidence` | 单个评分项至少展示得分、判定理由、标准、命中证据和置信度。 |

## 4. 完整更新历史（全量）

| version | date | 对应平台版本 | detail |
| --- | --- | --- | --- |
| `0.1.15` | `2026-03-26` | `0.1.15` | 回填操作记录审计中心、工作台最近查看恢复、自动评分明细复核、分段评分表解析与协作治理补充术语；新增“用户明确确认已发布完成时必须同步完成状态迁移”的协作语义。 |
| `0.1.14` | `2026-03-24` | `0.1.14` | 回填自动评分输入收敛术语：评分表规范化、结构化候选人优先入模、阈值保守策略与严格 JSON 输出；回填候选人高级筛选术语：流程状态、学校、学历、年限、评分区间与上传日期筛选口径。 |
| `0.1.13` | `2026-03-19` | `0.1.13` | 回填结构化抽取与通用信息融合术语：统一主展示事实源、结构化到通用信息字段映射、抽取刷新同步机制与历史/失败场景兼容边界。 |
| `0.1.12` | `2026-03-18` | `0.1.12` | 回填岗位管理与自动评分术语：岗位生命周期、岗位绑定上传、评分表版本管理、自动评分结果结构、手动重评与关键操作审计语义；补充后端分层术语：控制层/服务层/数据库交互层/工具层职责边界与启动入口收敛语义。 |
| `0.1.11` | `2026-03-18` | `0.1.11` | 回填上传与筛选支持部门维度、PDF 核心信息识别语义（学校/电话/邮箱提取、失败不阻塞、可人工修正）。 |
| `0.1.10` | `2026-03-17` | `0.1.10` | 回填用户管理编辑术语：统一编辑字段（显示名/状态/角色/部门范围）、四类角色编码与部门范围枚举及必填规则。 |
| `0.1.9` | `2026-03-17` | `0.1.9` | 回填角色定义与权限边界术语：四类角色编码、职责说明、角色可见范围与操作范围语义。 |
| `0.1.8` | `2026-03-17` | `0.1.8` | 回填候选人名称/岗位筛选语义、筛选重置与计数口径，以及左栏排序下拉与筛选/日历折叠交互语义。 |
| `0.1.7` | `2026-03-16` | `0.1.7` | 回填初筛阶段与阶段化未通过状态术语：四阶段流程、`未通过X` 状态与按钮文案联动规则。 |
| `0.1.6` | `2026-03-11` | `0.1.6` | 回填流入日期与批量上传术语：日粒度流入日期、批量上传结果策略、左侧日期标签展示规则。 |
| `0.1.5` | `2026-03-11` | `0.1.5` | 回填简历导入与生命周期术语：上传入库、UUID 主键、删除联动、目录手动同步。 |
| `0.1.4` | `2026-02-28` | `0.1.4` | 回填登录与用户管理术语，以及阶段面试人分配语义。 |
| `0.1.3` | `2026-02-28` | `0.1.3` | 回填左侧候选人状态枚举、排序/星标语义、终止隐藏策略与面试日历语义。 |
| `0.1.2` | `2026-02-28` | `0.1.2` | 回填面试阶段节点语义、阶段动作语义与分离保存范围定义。 |
| `0.1.1` | `2026-02-28` | `0.1.1` | 回填简历筛选术语与录入字段语义。 |
| `0.1.0` | `2026-02-28` | `0.1.0` | 初始化术语定义模板。 |
