# Latest Features

## 1. 文档元信息（置顶）

- 当前版本: `0.1.16`
- 对应平台版本: `0.1.16`
- 作用: 记录当前系统已支持能力，仅描述事实。
- GOVERNED_BY: `docs/00-governance/gov-02-requirements.md`

### 最近更新（最新 5 条）

| date | version | 对应平台版本 | summary |
| --- | --- | --- | --- |
| `2026-03-27` | `0.1.16` | `0.1.16` | 1. 发布 PDF 解析服务接口读取、数据库缓存复用与结构化抽取/自动评分统一事实源。<br>2. 发布结构化抽取字段级融合回显：规则初抽先展示，大模型结果按“有值覆盖、无值保留”替换，并同步候选人名称。<br>3. 发布 PDF 解析配置文件外置与失败自动回退旧工具能力。 |
| `2026-03-26` | `0.1.15` | `0.1.15` | 1. 发布操作记录页：支持日志查询、详情查看、同对象上一条记录比对与 JSON/CSV 导出。<br>2. 发布工作台最近查看恢复：跨页返回后自动恢复上次查看的候选人/简历上下文。<br>3. 发布自动评分明细复核：总分按评分项累加校验，并完整展示评分项证据与置信度。<br>4. 发布评分表分段结构解析增强与协作治理执行校验补充。<br>5. 明确用户确认“已发布完成”时，文档状态必须同步闭环更新。 |
| `2026-03-24` | `0.1.14` | `0.1.14` | 1. 发布自动评分输入收敛：评分表去重规范化、结构化候选人信息优先入模、阈值参数一致性与严格 JSON 输出。<br>2. 发布候选人多维筛选增强：支持流程状态、学校、学历、年限、评分区间、上传日期下拉与自定义区间。<br>3. 发布左栏筛选区与面试日历滚动优化：多列排布下支持内部滚动查看。 |
| `2026-03-24` | `0.1.13` | `0.1.13` | 1. 发布简历结构化抽取与通用信息融合展示：候选人详情页按通用信息统一展示抽取结果并去除同口径重复块。<br>2. 发布抽取刷新联动：点击“更新抽取”后通用信息区域同步刷新。<br>3. 发布兼容保障：历史无结构化数据与抽取失败场景均保留通用信息可用性。<br>4. 对齐历史归档表述：`0.1.9/0.1.10/0.1.11` 能力记录已按已发布状态归档到 `roadmap-01`。 |
| `2026-03-18` | `0.1.12` | `0.1.12` | 1. 发布岗位管理页面：支持岗位新增/编辑/查看/关闭/复制、流程配置、筛选标准和评分表版本管理。<br>2. 发布岗位关联上传与自动评分：上传简历必须绑定岗位，支持上传后自动评分与手动重评。<br>3. 发布评分结果回显与配置外置：工作台可查看结构化评分结果，LLM 配置外置并支持管理员只读查看。<br>4. 发布后端分层拆分：后端新增控制层/服务层/数据库交互层/工具层，`app/server.py` 收敛为启动入口。<br>5. 补齐 `0.1.11` 已发布能力归档：上传/筛选部门维度与 PDF 核心信息识别。 |

## 2. 状态枚举

- `available`: 已支持并可稳定使用。
- `partial`: 部分支持或有限制。
- `not_supported`: 当前不支持。

## 3. 能力列表

| capability | status | evidence | limitations |
| --- | --- | --- | --- |
| 文档治理闭环 | `available` | `docs/00-governance/*`, `docs/01-requirements/*`, `docs/02-roadmap/*` | 仅覆盖流程治理，不包含业务代码实现。 |
| 协作治理开工重读与 `project-docs` 同步约束 | `available` | `docs/00-governance/gov-03-agent-collaboration.md`, `project-docs/development/development-and-integration-guidelines.md` | 仅约束仓库协作与文档同步流程，不直接提供业务功能。 |
| 用户确认发布后的状态同步闭环 | `available` | `docs/00-governance/gov-02-requirements.md`, `docs/00-governance/gov-03-agent-collaboration.md`, `docs/02-roadmap/*`, `docs/01-requirements/*` | 依赖用户明确给出“已发布完成”类确认；确认后需同步更新 `roadmap-00/roadmap-01/req-01/req-02`。 |
| AIS 简历筛选工作台（三栏） | `available` | `web/index.html`, `web/app.js`, `web/styles.css` | 当前为本地前后端一体形态。 |
| 简历筛选后端与 SQLite 持久化 | `available` | `app/server.py`, `app/backend/services/recruitment_service.py`, `app/backend/repositories/sqlite_helpers.py` | 当前为本地单机服务，不含远程部署。 |
| 后端分层架构（控制/服务/仓储/工具） | `available` | `app/server.py`, `app/backend/controllers/resume_controller.py`, `app/backend/services/recruitment_service.py`, `app/backend/repositories/sqlite_helpers.py`, `app/backend/utils/time_utils.py` | 现阶段仍在同一代码仓内单体运行，尚未拆分为独立部署单元。 |
| 登录与会话鉴权（Cookie Session） | `available` | `app/server.py`, `web/login.html`, `web/login.js`, `web/app.js` | 当前不支持第三方 SSO。 |
| 用户管理（管理员操作） | `available` | `app/server.py`, `web/users.html`, `web/users.js`, `web/styles.css` | 当前无细粒度 RBAC，仅区分管理员门禁与普通用户。 |
| 角色定义模块（四类角色） | `available` | `app/server.py`, `web/users.js`, `web/app.js` | 角色定义已标准化，但部分业务页权限仍在持续收敛中。 |
| 用户管理编辑弹窗（状态/角色/部门范围） | `available` | `web/users.html`, `web/users.js`, `app/server.py` | 仅管理员可编辑用户；当前编辑范围不包含用户名与密码（密码需走重置流程）。 |
| 用户角色与部门范围联动校验 | `available` | `app/server.py`, `web/users.js`, `web/users.html` | `hiring_manager` 角色要求必填部门范围；其他角色不保留部门范围。 |
| 上传与筛选支持部门维度 | `available` | `web/index.html`, `web/app.js`, `app/backend/services/recruitment_service.py`, `app/backend/controllers/resume_controller.py` | 部门负责人视角不显示部门筛选，候选人部门编辑仅管理员与 HR 可操作。 |
| PDF 核心信息识别（学校/电话/邮箱） | `available` | `app/backend/services/recruitment_service.py`, `web/app.js`, `web/index.html` | 识别质量依赖 PDF 文本可解析性，失败场景需人工补录。 |
| PDF 解析服务接口读取与数据库缓存复用 | `available` | `app/backend/services/resume_extract_service.py`, `app/backend/services/auto_score_service.py`, `app/backend/controllers/candidate_controller.py` | PDF 文本默认走本地解析服务接口；解析文本与原始载荷写入 `candidate_files`，后续结构化抽取与自动评分优先复用数据库缓存。 |
| PDF 解析配置外置与失败自动回退 | `available` | `config/pdf-parser-config.json`, `app/backend/services/resume_extract_service.py`, `project-docs/operations/deployment-and-operations-guide.md` | 解析服务 URL、超时和回退开关已外置到独立配置文件；服务不可达、超时或异常时会自动回退旧工具并继续写库。 |
| 简历结构化抽取与通用信息融合展示 | `available` | `web/index.html`, `web/app.js`, `app/backend/services/resume_extract_service.py`, `app/backend/services/candidate_command_service.py` | 规则初抽先回显，结构化抽取结果按字段映射写入通用信息；空值不覆盖已有值，姓名会同步更新候选人主名称字段。 |
| 岗位管理页面与生命周期操作 | `available` | `web/jobs.html`, `web/jobs.js`, `web/index.html`, `app/server.py` | 岗位数据已接入后端持久化；当前仍为本地单机服务形态，不含远程部署与并发协同控制。 |
| 岗位评分表版本管理与生效控制 | `available` | `web/jobs.js`, `web/jobs.html`, `app/server.py` | 评分表解析优先走后端结构化预览与规则降级；复杂格式表格仍可能需要人工复核。 |
| 评分表分段结构解析与维度归属修复 | `available` | `app/backend/services/score_table_service.py`, `app/backend/services/job_service.py` | 支持“维度标题行 + 评分项行 + 续行标准”版式；极端复杂的合并单元格评分表仍建议人工复核。 |
| 大模型配置外置与管理员只读查看 | `available` | `config/llm-config.json`, `config/llm-prompts.json`, `app/server.py`, `web/users.html`, `web/users.js` | 仅提供只读查看，在线修改仍需手动更新配置文件并重启服务。 |
| 默认管理员首登改密 | `available` | `app/server.py`, `web/login.html`, `web/login.js` | 仅内置单个默认管理员种子策略。 |
| 操作记录页与统一日志审计 | `available` | `web/operations.html`, `web/operations.js`, `app/backend/controllers/operation_log_controller.py`, `app/backend/services/operation_log_service.py` | 当前仅管理员可见；导出支持 `JSON/CSV`，后端异常时前端有本地兜底展示。 |
| 简历流入日期记录与回填 | `available` | `app/server.py`, `web/app.js` | 以日粒度 `YYYYMMDD` 存储，展示为 `YYYY-MM-DD`。 |
| 候选人列表流入日期标签 | `available` | `web/app.js`, `web/styles.css` | 左侧标签仅展示日期文本，不支持按该标签筛选。 |
| 前端批量上传 PDF | `available` | `web/index.html`, `web/app.js`, `web/styles.css`, `app/server.py` | 当前为前端顺序提交，未实现并发队列与断点续传。 |
| 简历上传与入库映射 | `available` | `app/server.py`, `web/index.html`, `web/app.js` | 仅支持 PDF，且同名文件执行全局唯一拒绝。 |
| 候选人 UUID 映射与历史迁移 | `available` | `app/server.py`, `data/recruitment.sqlite3` | 当前 UUID 由系统生成，不支持外部导入指定主键。 |
| 候选人删除联动本地文件删除 | `available` | `app/server.py`, `web/index.html`, `web/app.js` | 删除为硬删除，当前无回收站恢复能力。 |
| 候选人名称编辑与持久化回显 | `available` | `web/index.html`, `web/app.js`, `app/server.py` | 名称编辑入口位于通用信息区域。 |
| 本地目录手动同步导入 | `available` | `web/index.html`, `web/app.js`, `app/server.py` | 同步为手动触发，不含后台定时任务。 |
| 面试阶段节点交互增强 | `available` | `web/app.js`, `web/styles.css`, `web/index.html`, `app/server.py` | 四节点阶段（初筛/一面/二面/HR面）流转与重置已支持；阶段状态颜色含当前进行中红点语义。 |
| 阶段面试人分配与回显 | `available` | `app/server.py`, `web/index.html`, `web/app.js` | 每阶段当前仅支持单个面试人。 |
| 阶段/通用信息分离保存 | `available` | `web/app.js`, `web/index.html`, `app/server.py` | 提供阶段信息与通用信息分离保存入口；保留旧聚合接口兼容。 |
| 候选人列表名称/岗位筛选 | `available` | `app/server.py`, `web/app.js`, `web/index.html` | 支持名称模糊筛选、岗位精确/模糊筛选和组合筛选，支持一键重置。 |
| 候选人列表多维筛选（含上传日期） | `available` | `web/index.html`, `web/app.js`, `web/styles.css`, `app/backend/controllers/candidate_controller.py`, `app/backend/services/candidate_service.py`, `project-docs/api/api-documentation.md` | 支持 `stage_status`、`school`、`education`、`duration`、`score_min/score_max`、`upload_date/uploaded_from/uploaded_to`；筛选质量依赖候选人字段完整度。 |
| 工作台最近查看候选人恢复 | `available` | `web/index.html`, `web/app.js`, `project-docs/development/development-and-integration-guidelines.md` | 依赖前端本地存储；当候选人已删除或当前不可见时自动降级到首条可用记录或空态。 |
| 候选人筛选计数联动 | `available` | `app/server.py`, `web/app.js` | 返回并展示 `total_count/filtered_count`；界面显示可见数、筛选结果数与全量数。 |
| 左栏排序下拉与模块折叠 | `available` | `web/index.html`, `web/app.js`, `web/styles.css` | 左栏头部提供排序下拉；筛选区与面试日历支持展开/收起。 |
| 左侧候选人管理增强（状态细分/星标/排序/隐藏） | `available` | `web/index.html`, `web/app.js`, `web/styles.css`, `app/server.py` | 候选人状态支持 `待初筛` 与 `未通过X`；未通过候选人默认隐藏，仅在“显示全部”开关开启后展示。 |
| 阶段结果文案联动 | `available` | `web/app.js`, `web/index.html`, `app/server.py` | `HR面` 阶段推进按钮显示 `通过面试`；结束按钮按当前阶段显示 `未通过X`。 |
| 面试日历（未来安排） | `available` | `web/index.html`, `web/app.js`, `app/server.py` | 仅展示未来已安排时间；未配置时间的节点不会进入日历。 |
| 一键后台启动脚本 | `available` | `scripts/resume_app_up.sh` | 默认仅本机 `127.0.0.1:8080`。 |
| 简历上传岗位关联与候选人岗位回显 | `available` | `web/app.js`, `app/server.py` | 上传时依赖后端岗位接口已有岗位数据；无岗位时上传会被拦截。 |
| 候选人自动评分与手动重评 | `available` | `web/app.js`, `app/server.py`, `config/llm-prompts.json` | LLM 不可用时自动降级规则评分，评分质量受简历文本提取质量影响。 |
| 自动评分输入收敛与严格 JSON 输出 | `available` | `app/backend/services/recruitment_service.py`, `app/backend/services/auto_score_service.py`, `web/app.js`, `config/llm-prompts.json` | 评分稳定性提升依赖结构化简历字段质量；字段缺失场景采用保守降级策略。 |
| 自动评分总分校验与评分项明细展示 | `available` | `app/backend/services/auto_score_service.py`, `web/app.js` | 历史无评分项明细的记录按兼容模式展示；完整复核能力依赖评分结果中存在评分项明细。 |

## 4. 完整更新历史（全量）

| version | date | 对应平台版本 | detail |
| --- | --- | --- | --- |
| `0.1.16` | `2026-03-27` | `0.1.16` | 发布 PDF 解析服务接口读取、解析结果落库缓存与数据库优先复用；发布结构化抽取字段级融合回显与候选人名称同步；发布 PDF 解析配置文件外置与失败自动回退旧工具能力。 |
| `0.1.15` | `2026-03-26` | `0.1.15` | 发布操作记录页、工作台最近查看恢复、自动评分总分校验与评分项明细展示、评分表分段结构解析增强与协作治理补充；明确用户确认“已发布完成”后文档状态需同步闭环更新。 |
| `0.1.14` | `2026-03-24` | `0.1.14` | 发布自动评分输入收敛与严格 JSON 输出能力；发布候选人多维筛选（含上传日期）与左栏滚动优化。 |
| `0.1.13` | `2026-03-19` | `0.1.13` | 发布简历结构化抽取与通用信息融合展示能力：候选人详情页统一按通用信息展示抽取字段、去除同口径重复展示，并支持更新抽取后的同步刷新与失败降级可用。 |
| `0.1.12` | `2026-03-18` | `0.1.12` | 发布岗位管理、评分表版本管理、岗位关联上传、自动评分与手动重评能力，并完成大模型配置外置与管理员只读配置查看；补充后端分层拆分能力（入口收敛 + 控制层/服务层/仓储层/工具层）。 |
| `0.1.11` | `2026-03-18` | `0.1.11` | 发布上传与筛选支持部门维度、PDF 学校/电话/邮箱识别、识别结果回显与人工修正链路。 |
| `0.1.10` | `2026-03-17` | `0.1.10` | 发布用户管理编辑弹窗与角色/状态/部门范围统一编辑能力，并补齐前后端联动校验。 |
| `0.1.9` | `2026-03-17` | `0.1.9` | 发布角色定义基础能力：四类角色编码、角色定义查询与用户角色录入/编辑链路。 |
| `0.1.8` | `2026-03-17` | `0.1.8` | 发布候选人名称/岗位筛选、筛选重置与计数联动能力，并完成左栏排序下拉与筛选/日历折叠排版优化。 |
| `0.1.7` | `2026-03-16` | `0.1.7` | 发布初筛阶段、阶段化未通过状态、阶段按钮文案联动与历史数据兼容能力。 |
| `0.1.6` | `2026-03-11` | `0.1.6` | 发布流入日期持久化与回填、前端批量上传、左侧流入日期标签展示能力。 |
| `0.1.5` | `2026-03-11` | `0.1.5` | 发布简历导入升级、候选人删除与改名能力、手动目录同步能力。 |
| `0.1.4` | `2026-02-28` | `0.1.4` | 发布登录与会话、用户管理、阶段面试人分配能力。 |
| `0.1.3` | `2026-02-28` | `0.1.3` | 发布左侧候选人管理增强与未来面试日历能力。 |
| `0.1.2` | `2026-02-28` | `0.1.2` | 发布阶段节点交互增强与分离保存能力。 |
| `0.1.1` | `2026-02-28` | `0.1.1` | 发布简历筛选系统首版能力事实。 |
| `0.1.0` | `2026-02-28` | `0.1.0` | 初始化能力清单模板。 |
