# 智训云（zhixun-cloud）

> 企业 AI 培训考核平台：上传企业文档，AI 生成培训题目与考前知识卡，管理员审核后组卷发布，员工在微信小程序中学习、考试、复盘。

## 一、项目简介

智训云面向连锁零售、餐饮、制造等有大量一线员工培训需求的企业，把 SOP、制度、合规资料转化为可执行的学习与考核任务。

核心闭环：

```text
管理员上传文档
  → AI 生成草稿题与考前知识卡
  → 管理员审核/编辑
  → 组卷并指派到部门或员工
  → 员工考前看知识卡
  → 员工微信答题
  → 服务端判分
  → 成绩、解析、错题重练
  → 管理后台看板与 Excel 导出
```

项目由三部分组成：

| 端 | 目录 | 技术栈 | 使用者 |
|---|---|---|---|
| 员工端小程序 | `frontend/` | Taro 4 + React 18 + TypeScript + Sass | 员工 |
| 企业管理后台 | `admin-web/` | React 18 + Vite + Ant Design 5 | 企业管理员 |
| 后端服务 | `backend/` | Python 3.11 + FastAPI + LangChain + MySQL | 全平台 |

## 二、已实现能力

### 企业管理

- 租户、部门树（增删改）、员工导入、手动添加员工、加入申请审核
- 知识库文档上传与解析（PDF / Word / Markdown / TXT），租户级配额（200 篇 / 2GB）
- 基于文档的 AI 出题：全文均匀抽样、题干去重、来源引用、审核通过/驳回/批量审核
- 题目编辑（改后回到草稿）与软删除；知识卡生成、编辑、发布、下线
- 考试创建（含说明）、组卷、知识卡关联、按部门/员工指派、已发布追加指派
- 发布前通知预览与二次确认；考试关闭；导出成绩
- 考试看板：完成率、通过率、平均分、成绩分布、知识卡查看率
- 成绩明细、逐题正确率、薄弱知识点、部门对比
- 通知送达统计：已通知、已读、未绑定微信名单
- 全局搜索：员工、题目、考试、知识卡、知识库文档
- 真实数据趋势图（最近 6 场考试）
- 审计日志：覆盖审核、发布、指派、编辑、删除、导出等关键操作
- 管理员登录失败限流（5 次 / 分钟锁定）

### 员工学习

- 小程序申请加入企业，管理员审核通过后进入培训
- 首页与企业培训入口展示未读角标，考试列表标记「新」
- 消息中心：全部/未读、全部已读、点击跳转；可开关截止提醒
- 微信订阅消息（配置模板后启用，未授权时自动降级为站内通知）
- 考前知识卡阅读与已读记录
- 限时答题、答题卡、500ms 防抖自动保存、断点续答、超时自动交卷
- 保存状态提示（保存中 / 已保存 / 失败重试）
- 服务端判分、成绩与逐题解析、重考
- 个人错题本、错题重练、连续答对标记掌握
- 保留自由练习/闯关模式

### 平台能力

- 管理员账号与角色鉴权，员工停用后旧 token 立即失效
- 租户数据隔离
- 站内通知中心、微信订阅消息、截止前 24 小时定时提醒
- 审计日志只追加不修改
- 异步出题任务
- AI 出题、知识卡、报告生成
- 文档解析、向量检索、AI 配图

## 三、技术选型

| 层面 | 技术 |
|---|---|
| 小程序 | Taro 4、React 18、TypeScript、Sass |
| 管理后台 | React 18、Vite、Ant Design 5、React Router |
| 后端 | Python 3.11、FastAPI、Pydantic v2、aiomysql |
| AI 编排 | LangChain、LangGraph、langchain-openai |
| 大模型 | DeepSeek（出题/知识卡/报告） |
| 检索与向量库 | 阿里云百炼 Embedding、Chroma |
| 数据存储 | MySQL 8、腾讯云 COS（可选） |
| 鉴权 | JWT、微信 `jscode2session`、企业加入审核、员工状态实时校验 |
| 通知 | 站内通知表、未读角标、微信订阅消息（可选） |
| 审计 | `audit_logs` 追加式日志 |
| 测试 | pytest、pytest-asyncio、端到端验证脚本 |

## 四、目录结构

```text
zhixun-cloud/
├── admin-web/            # 企业管理后台
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/          # 路由
│   │   ├── core/         # 配置、数据库、鉴权
│   │   ├── llm/          # LangChain 链
│   │   ├── models/       # Pydantic 模型
│   │   ├── prompts/      # Prompt 模板
│   │   ├── repositories/ # 数据访问
│   │   └── services/     # 业务服务
│   ├── scripts/          # 初始化与端到端测试脚本
│   └── tests/            # pytest
├── frontend/             # 员工端 Taro 小程序
├── docs/                 # 需求、方案、运行指南
├── test-documents/       # 企业培训测试文档
└── prototypes/           # UI 原型
```

## 五、快速开始

### 1. 前置条件

- Python >= 3.11
- Node.js >= 18
- MySQL >= 8.0
- 微信开发者工具
- DeepSeek API Key（必需）
- Tavily、阿里云百炼、腾讯云 COS（可选）

### 2. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env              # 填写 DEEPSEEK_API_KEY、MYSQL_PASSWORD
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

接口文档：<http://localhost:8000/docs>

首次使用管理后台前，依次执行：

```bash
python scripts/seed_admin.py
python scripts/seed_question_bank.py
python scripts/seed_knowledge_cards.py
python scripts/seed_admin_console.py
```

### 3. 启动管理后台

```bash
cd admin-web
npm install
npm run dev
```

访问 <http://localhost:5174>，开发服务器会代理 `/api` 到 `127.0.0.1:8000`。

默认管理员：租户 `demo`，账号 `admin`，密码 `demo1234`。

### 4. 启动小程序

```bash
cd frontend
npm install
npm run dev:weapp
```

用微信开发者工具打开 `frontend/dist`，本地开发需勾选「不校验合法域名」。

员工端：在小程序「企业培训」输入企业编码 `demo`、姓名和工号提交申请，管理员在后台「加入审核」通过后即可进入考试。

### 5. 通知与微信订阅消息（可选）

站内通知开箱即用。如需微信服务通知，在小程序后台申请订阅消息模板后，在 `backend/.env` 填入：

```text
WECHAT_SUBSCRIBE_EXAM_ASSIGNED=考试指派模板ID
WECHAT_SUBSCRIBE_RESULT_READY=成绩通知模板ID
WECHAT_SUBSCRIBE_DEADLINE=截止提醒模板ID
```

未配置模板时接口返回 `enabled: false`，小程序不展示订阅入口，所有消息走站内通道。模板字段与代码约定不一致时，调整 `backend/app/services/wechat_subscribe_service.py` 中的字段映射。

截止提醒由后端定时任务扫描（启动 60 秒后首轮，之后每 10 分钟一次）；需在管理后台「设置 → 通知」开启「考试结束前 24 小时提醒」。

### 6. 运行测试

```bash
cd backend
pytest
```

当前测试规模：213 个用例。

真实验证脚本（需要 MySQL，部分需要 DeepSeek Key）：

```bash
python scripts/test_enterprise_mvp.py      # 完整企业闭环（含 AI 生成）
python scripts/test_publish_notification.py # 发布考试 -> 员工收到通知
python scripts/test_p1_features.py         # 成绩/关闭/截止提醒/消息列表
python scripts/test_p2_features.py         # 订阅配置、通知偏好、送达统计
python scripts/test_p0_gaps_e2e.py         # 部门编辑、成绩分析、审计、导出有效期
python scripts/verify_question_edit.py     # 题目编辑/删除
python scripts/verify_notifications.py     # 通知读写链路
```

脚本会创建临时数据并在结束后清理，不会保留测试考试与通知。

## 六、测试文档

`test-documents/` 提供食品安全、门店 SOP、新人培训、消防安全、客诉处理、考勤制度等 8 份文档，覆盖 Markdown、TXT、DOCX、PDF 四种格式，可直接在管理后台上传测试。

## 七、部署说明

- `backend/Dockerfile` 可用于容器化部署。
- 密钥类环境变量（数据库密码、API Key、微信 AppSecret、`JWT_SECRET`）通过平台环境变量注入，不要提交到仓库。
- 生产环境建议关闭 `MYSQL_AUTO_INIT`，使用正式迁移流程。
- 截止提醒定时任务与 Web 进程同生命周期；多进程部署时通过 MySQL 命名锁保证同一时间只有一个实例扫描。
- 通知与审计日志均为追加式数据，建议按合同约定设置保留期与归档策略（审计日志至少保留 1 年）。
- 管理员登录限流为单进程内存实现，多实例部署时如需严格限流，可替换为 Redis。
- 小程序上线需要完成服务类目、ICP 备案、域名白名单与代码审核。
- 小程序本地联调使用 `NODE_ENV=development npm run build:weapp`，会把 `config/dev.ts` 中的接口地址注入产物；生产构建需先在 `config/prod.ts` 配置正式域名。

## 八、文档

- [企业培训考核版需求分析文档](docs/企业培训考核版需求分析文档.md)
- [企业方向转型实施方案](docs/企业方向转型实施方案.md)
- [三端交互优化方案](docs/三端交互优化方案.md)
- [方案设计文档](docs/方案设计文档.md)
- [保姆级本地运行指南](保姆级本地运行指南.md)
- [人工测试发现的问题](docs/人工测试发现的问题.md)
