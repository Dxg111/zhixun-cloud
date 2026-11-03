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

- 租户、部门树、员工导入、手动添加员工、邀请码管理
- 知识库文档上传与解析，支持 PDF / Word / Markdown / TXT，支持多文件上传
- 基于文档的 AI 出题，草稿题库、来源引用、审核通过/驳回/批量审核
- 基于文档的 AI 知识卡生成，管理员编辑、发布、下线
- 考试创建、组卷、知识卡关联、按部门/员工指派、直接发布
- 考试看板：完成率、通过率、成绩分布、知识卡查看率
- 成绩 Excel 导出

### 员工学习

- 邀请码登录，查看待办考试
- 考前知识卡阅读与已读记录
- 限时答题、自动保存、断点续答、超时自动交卷
- 服务端判分、成绩与逐题解析、重考
- 个人错题本、错题重练、连续答对标记掌握
- 保留自由练习/闯关模式

### 平台能力

- 管理员账号与角色鉴权
- 租户数据隔离
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
| 鉴权 | JWT、微信 `jscode2session`、邀请码 |
| 测试 | pytest、pytest-asyncio |

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

员工测试账号：租户 `demo`，邀请码 `INV1001` 或 `INV1002`。

### 5. 运行测试

```bash
cd backend
pytest
```

真实验证企业闭环（需要 MySQL 与 DeepSeek Key）：

```bash
python scripts/test_enterprise_mvp.py
```

脚本覆盖：上传文档 → AI 出题/知识卡 → 审核 → 指派 → 发布 → 员工阅读/考试 → 超时判分 → 错题重练 → Excel 导出，并在结束后清理测试数据。

## 六、测试文档

`test-documents/` 提供食品安全、门店 SOP、新人培训、消防安全、客诉处理、考勤制度等 8 份文档，覆盖 Markdown、TXT、DOCX、PDF 四种格式，可直接在管理后台上传测试。

## 七、部署说明

- `backend/Dockerfile` 可用于容器化部署。
- 密钥类环境变量（数据库密码、API Key、微信 AppSecret、`JWT_SECRET`）通过平台环境变量注入，不要提交到仓库。
- 生产环境建议关闭 `MYSQL_AUTO_INIT`，使用正式迁移流程。
- 小程序上线需要完成服务类目、ICP 备案、域名白名单与代码审核。

## 八、文档

- [企业培训考核版需求分析文档](docs/企业培训考核版需求分析文档.md)
- [企业方向转型实施方案](docs/企业方向转型实施方案.md)
- [方案设计文档](docs/方案设计文档.md)
- [保姆级本地运行指南](docs/保姆级本地运行指南.md)
- [人工测试发现的问题](docs/人工测试发现的问题.md)
