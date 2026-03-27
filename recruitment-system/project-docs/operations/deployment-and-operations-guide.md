# 部署与运维说明

本文档记录当前项目的实际部署方式、运行依赖、环境变量、打包产物和备份建议。

## 1. 当前部署形态

| 项目 | 当前实现 |
| --- | --- |
| 服务进程 | 单个 Python 进程 |
| HTTP 服务 | `ThreadingHTTPServer` |
| 静态资源 | 由同一进程直接提供 |
| 数据存储 | 本地 SQLite |
| 简历文件存储 | 本地文件系统 |
| 岗位评分表存储 | 本地文件系统 |
| 标准发布形式 | Linux tar.gz 离线包 |

说明：当前项目不是分布式部署，也没有独立的前后端服务拆分。

## 2. 目录与运行资产

### 2.1 关键路径

| 路径 | 用途 |
| --- | --- |
| `app/server.py` | 启动入口 |
| `web/` | 静态页面资源 |
| `data/recruitment.sqlite3` | SQLite 数据库 |
| `data/cv/ais/` | 简历 PDF 根目录 |
| `data/job_templates/` | 评分表文件根目录 |
| `config/llm-config.json` | LLM 运行配置 |
| `config/llm-prompts.json` | Prompt 配置 |
| `config/pdf-parser-config.json` | PDF 解析服务运行配置 |
| `scripts/resume_app_up.sh` | Linux 启动脚本 |
| `scripts/package_linux_release.py` | Linux 打包脚本 |
| `release/linux/` | 打包产物目录 |

### 2.2 已有发布产物

仓库当前已存在：

- `release/linux/recruitment-system-linux-0.1.8.tar.gz`
- `release/linux/recruitment-system-linux-0.1.13.tar.gz`
- `release/linux/recruitment-system-linux-0.1.14.tar.gz`

这说明项目当前已有 Linux 离线发包流程。

## 3. 启动方式

### 3.1 直接启动

```bash
python app/server.py
```

默认访问地址：

- `http://127.0.0.1:8080`

### 3.2 Linux 后台启动

```bash
bash scripts/resume_app_up.sh
```

脚本行为：

- 检查旧 PID 是否仍在运行
- 后台启动 `python3 app/server.py`
- 写入 PID 文件
- 将标准输出/错误输出写入日志文件

默认文件位置：

- PID：`/tmp/recruitment-system-resume-app.pid`
- 日志：`/tmp/recruitment-system-resume-app.log`

## 4. 环境变量

### 4.1 服务启动相关

| 变量名 | 默认值 | 说明 |
| --- | --- | --- |
| `RESUME_APP_HOST` | `127.0.0.1` | 服务监听地址 |
| `RESUME_APP_PORT` | `8080` | 服务端口 |
| `RESUME_APP_ADMIN_PASSWORD` | `admin123456` | 空库初始化时默认管理员密码 |
| `RESUME_APP_LLM_CONFIG_PATH` | `config/llm-config.json` | 自定义 LLM 配置文件路径 |
| `RESUME_APP_PDF_PARSER_CONFIG_PATH` | `config/pdf-parser-config.json` | 自定义 PDF 解析配置文件路径 |
| `RESUME_APP_PDF_PARSER_URL` | 取 `pdf-parser-config.json` | 覆盖 PDF 解析服务地址 |
| `RESUME_APP_PDF_PARSER_TIMEOUT_SECONDS` | 取 `pdf-parser-config.json` | 覆盖 PDF 解析服务超时秒数 |
| `RESUME_APP_PDF_PARSER_FALLBACK_ENABLED` | 取 `pdf-parser-config.json` | 覆盖解析服务失败时是否启用旧工具回退 |

### 4.2 启动脚本附加变量

| 变量名 | 默认值 | 说明 |
| --- | --- | --- |
| `RESUME_APP_PID_FILE` | `/tmp/recruitment-system-resume-app.pid` | PID 文件位置 |
| `RESUME_APP_LOG_FILE` | `/tmp/recruitment-system-resume-app.log` | 日志文件位置 |

## 5. 运行前准备

1. 安装 Python 3。
2. 确保运行用户对以下目录有读写权限：
   - `data/`
   - `config/`
   - `release/`（若需要打包）
3. 首次启动会自动创建：
   - SQLite 数据库文件
   - 简历目录
   - 岗位评分表目录
4. 若启用 LLM 能力，需准备可用的 `llm-config.json` 与 `llm-prompts.json`。
5. 准备 `config/pdf-parser-config.json`，并确认其中的 PDF 解析服务地址、超时和回退开关符合当前环境。
6. 若本地 PDF 解析服务不可用，确保旧的 PDF 文本提取依赖可用；否则简历抽取与自动评分输入会整体失败。
7. 数据库升级时会自动为 `candidate_files` 增加 PDF 解析缓存字段，首次启动新版本时需保证 SQLite 文件可写。

## 6. 健康检查与巡检

### 6.1 健康检查

- 接口：`GET /api/healthz`
- 返回：

```json
{
  "ok": true,
  "time": "2026-03-23T12:00:00+00:00"
}
```

### 6.2 基本巡检项

1. 服务端口是否监听正常。
2. `/api/healthz` 是否返回 `ok=true`。
3. 登录页 `/login` 是否可访问。
4. SQLite 文件是否存在且可写。
5. `data/cv/ais/` 和 `data/job_templates/` 是否存在。
6. 若启用 LLM，管理员页能否读取 `/api/settings/llm-config`。
7. 若需要审计能力，管理员能否访问 `/static/operations.html` 并正常拉取 `/api/operation-logs`。
8. 本地 PDF 解析服务是否可达，且对真实 PDF 返回合法 JSON。
9. 抽样检查 `candidate_files.resume_parsed_text` / `resume_parser_payload_json` 是否已写入，确认解析缓存可复用。

## 7. 日志与故障排查

### 7.1 当前日志来源

- 前台启动：终端标准输出
- Linux 脚本启动：`/tmp/recruitment-system-resume-app.log`

### 7.2 常见故障排查

#### 服务无法启动

排查顺序：

1. 检查 Python 版本与命令是否可用。
2. 检查端口是否被占用。
3. 查看日志中是否有 SQLite 文件权限错误。
4. 检查 `config/llm-config.json` 是否为合法 JSON。

#### 登录失败

排查顺序：

1. 确认数据库中是否已写入默认管理员。
2. 若为新库，检查 `RESUME_APP_ADMIN_PASSWORD` 是否与预期一致。
3. 检查浏览器是否允许 Cookie。

#### 上传简历失败

排查顺序：

1. 文件是否为 PDF。
2. 文件大小是否超过 `20MB`。
3. 上传时是否选择了岗位与部门。
4. `data/cv/ais/` 是否可写。
5. `config/pdf-parser-config.json` 是否为合法 JSON，且 `service_url`、`timeout_seconds`、`fallback_enabled` 配置正确。
6. 本地 PDF 解析服务是否正常运行；若服务异常，确认旧的 PDF 文本提取回退链路是否仍可用。
7. 若文件仍在但重复评分/抽取明显变慢，检查 `candidate_files` 中是否存在解析缓存写入失败。

#### 评分表上传失败

排查顺序：

1. 文件后缀是否为 `csv/xls/xlsx`。
2. 文件大小是否超过 `8MB`。
3. `data/job_templates/` 是否可写。
4. 当前用户是否具备岗位管理权限。

#### 自动评分失败

排查顺序：

1. 候选人是否已绑定岗位快照。
2. 岗位是否有生效评分表版本。
3. LLM 配置是否有效。
4. 即使 LLM 不可用，也应确认是否已回退到规则评分而不是整条链路异常。
5. 若 PDF 解析服务临时不可用，但候选人已存在解析缓存，自动评分仍应可复用数据库中的简历文本继续执行。

## 8. 备份与恢复

### 8.1 建议备份范围

必须一起备份：

- `data/recruitment.sqlite3`
- `data/cv/ais/`
- `data/job_templates/`
- `config/llm-config.json`
- `config/llm-prompts.json`
- `VERSION`

### 8.2 恢复步骤

1. 停止服务。
2. 恢复数据库文件和 `data/` 下附件目录。
3. 恢复 `config/` 配置文件。
4. 重新启动服务。
5. 访问 `/api/healthz`、`/login` 和一个已知候选人详情页验证恢复结果。

## 9. 打包发布

### 9.1 生成 Linux 离线包

```bash
python scripts/package_linux_release.py
```

打包逻辑：

- 读取 `VERSION`
- 将 `app`、`web`、`data`、`deploy`（存在时）、`scripts`、`templates` 及根目录说明文件复制到临时目录
- 自动生成 `run.sh`
- 输出到 `release/linux/recruitment-system-linux-<version>.tar.gz`

### 9.2 离线包运行

解压后可执行：

```bash
bash run.sh
```

该脚本内部仍调用 `scripts/resume_app_up.sh`。

## 10. 当前运维限制

1. SQLite 只适合单机部署，多实例共享写入风险高。
2. 服务端没有进程守护器配置示例（如 systemd/supervisor），目前仅有 Bash 启动脚本。
3. 仓库中的 `.gitlab-ci.yml` 目前是通用 Auto DevOps 模板，未体现项目专用部署步骤。
4. 没有现成的监控、指标采集和告警配置，当前主要依赖健康检查和日志排查。
5. 若配置文件中直接内联密钥，会带来明显安全风险；生产环境建议改为环境变量注入。
