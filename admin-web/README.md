# 智训云 · 企业管理后台

智训云企业管理后台，基于 React 18 + Vite + Ant Design 5，用于维护组织与员工、上传培训文档、审核 AI 生成题目和知识卡、组卷发布考试、查看成绩与导出报表。

## 启动

```bash
cd admin-web
npm install
npm run dev
```

默认地址：`http://localhost:5174`，开发服务器将 `/api` 代理到 `http://127.0.0.1:8000`。

生产构建：

```bash
npm run build
npm run preview
```

## 技术栈

- React 18 + TypeScript
- Vite 5
- Ant Design 5
- React Router 6

## 页面

| 路由 | 页面 | 说明 |
|---|---|---|
| `/login` | 登录页 | 租户编码 + 管理员账号 + 密码 |
| `/dashboard` | 工作台 | 待办、完成率、最近考试、薄弱知识点 |
| `/search` | 全局搜索 | 跨员工、题目、考试、知识卡、知识库文档搜索 |
| `/org` | 组织与员工 | 部门树、员工列表、文件导入、手动添加、启停 |
| `/join-requests` | 加入审核 | 审核员工加入申请、分配部门并绑定微信 |
| `/knowledge` | 知识库 | 多文件上传、解析状态、删除 |
| `/questions` | 题库审核 | 按状态/题库筛选、搜索、单题审核、批量通过 |
| `/cards` | 知识卡 | 生成、编辑、发布/下线、查看阅读情况 |
| `/exams` | 考试管理 | 新建（含指派与知识卡）、发布、关闭、详情、导出 |
| `/exports` | 导出中心 | 导出任务列表与下载 |
| `/admins` | 管理员 | 管理员列表、新增、重置密码、启用/停用 |
| `/settings` | 设置 | 租户信息与默认考试规则 |

## 登录

```http
POST /api/v1/auth/admin/login
Content-Type: application/json

{
  "tenant_code": "demo",
  "login_name": "admin",
  "password": "demo1234"
}
```

管理员账号存储在 MySQL 的 `admin_users` 表，密码使用 bcrypt 哈希。首次运行或重置密码时：

```bash
cd backend
python scripts/seed_admin.py
```

`seed_admin.py` 从以下环境变量读取初始化信息：

```text
ADMIN_TENANT_CODE=demo
ADMIN_LOGIN_NAME=admin
ADMIN_PASSWORD=demo1234
ADMIN_DISPLAY_NAME=李培训
```

登录成功后前端保存 `admin-web-token` 和 `admin-web-user`，受保护页面由 `RequireAuth` 校验。

## 主要接口

- `POST /api/v1/auth/admin/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/admin/dashboard`
- `GET/POST /api/v1/admin/org-units`
- `GET/POST /api/v1/admin/employees`
- `POST /api/v1/admin/employees/import`
- `PUT /api/v1/admin/employees/{id}/status`
- `POST /api/v1/admin/employees/{id}/reset-invite`
- `GET/POST /api/v1/admin/documents`
- `POST /api/v1/admin/documents/{id}/generate-questions`
- `GET /api/v1/admin/questions`
- `POST /api/v1/admin/questions/{id}/review`
- `POST /api/v1/admin/questions/bulk-review`
- `GET/POST /api/v1/admin/knowledge-cards`
- `GET/PUT /api/v1/admin/knowledge-cards/{id}`
- `PUT /api/v1/admin/knowledge-cards/{id}/status`
- `GET/POST /api/v1/admin/exams`
- `GET /api/v1/admin/exams/{id}`
- `GET/PUT /api/v1/admin/exams/{id}/knowledge-cards`
- `GET/PUT /api/v1/admin/exams/{id}/assignments`
- `POST /api/v1/admin/exams/{id}/publish`
- `POST /api/v1/admin/exams/{id}/close`
- `POST /api/v1/admin/exams/{id}/export`
- `GET /api/v1/admin/exports`
- `GET /api/v1/admin/exports/{id}/download`
- `GET/PUT /api/v1/admin/settings`

## 企业闭环验证

```bash
cd backend
python scripts/test_enterprise_mvp.py
```

覆盖：上传文档 → AI 出题/知识卡 → 审核 → 指派 → 发布 → 员工阅读/考试 → 超时判分 → 错题重练 → Excel 导出。脚本使用真实 MySQL 和 DeepSeek，结束后自动清理测试数据。

## 初始化演示数据

```bash
cd backend
python scripts/seed_admin.py
python scripts/seed_question_bank.py
python scripts/seed_knowledge_cards.py
python scripts/seed_admin_console.py
```

## 员工端

员工端小程序位于 `frontend/`，入口为「我的」→「企业培训」。员工提交加入申请后，需要在后台「加入审核」中通过。

```text
企业编码：demo
```

本地调试：

```bash
cd frontend
npm run dev:weapp
```

然后用微信开发者工具打开 `frontend/dist`。
