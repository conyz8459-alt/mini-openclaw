# Mini-OpenClaw

一个本地运行、前后端分离的轻量级 AI Agent 系统，复刻 OpenClaw（原 Moltbot/Clawdbot）的核心体验。

## 核心理念

- **文件即记忆**：所有对话、记忆、用户画像都以 Markdown/JSON 文件存在，人类可读、可直接编辑。
- **技能即插件**：Skills 遵循"指令遵循"范式——是教 Agent 如何用基础工具完成任务的说明书（`SKILL.md`），而非预写函数。拖入文件夹即可扩展能力。
- **透明可控**：System Prompt 拼接、工具调用、记忆读写全程可见。

## 技术栈（后端）

- Python 3.10+ / FastAPI（端口 8002，SSE 流式）
- LangChain 1.x `create_agent`（LangGraph 运行时）
- 5 个 Core Tools：`terminal`、`python_repl`、`fetch_url`、`read_file`、`search_knowledge_base`
- 模型：OpenAI 兼容接口（DeepSeek / OpenRouter / Claude 直连）
- RAG：LlamaIndex Hybrid Search（BM25 + 向量，Phase 4）

## 快速开始（后端）

```bash
cd backend

# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置模型（复制模板并填入 API Key）
cp .env.example .env
#   编辑 .env，填入 LLM_API_KEY，按需调整 LLM_BASE_URL / LLM_MODEL

# 3a. 命令行对话测试（无需前端）
python cli_chat.py

# 3b. 或启动 API 服务
python app.py        # http://localhost:8002 ，文档 /docs
```

## 快速开始（前端）

```bash
cd frontend

# 安装依赖（国内建议用镜像源）
npm install --registry=https://registry.npmmirror.com

# 启动开发服务器（需后端已在 8002 运行）
npm run dev          # http://localhost:3000
```

三栏 IDE：左侧会话列表、中间对话流（思考链可折叠）、右侧 Monaco 编辑器（实时查看/编辑 MEMORY.md 与 SKILL.md）。

## 目录结构

```
backend/
├── app.py              # FastAPI 入口（Port 8002）
├── config.py           # 路径与模型配置
├── agent_core.py       # create_agent 编排 + 动态 prompt 中间件
├── prompt_builder.py   # 6 段 System Prompt 动态拼接
├── skills_manager.py   # Skills 扫描 → SKILLS_SNAPSHOT.md
├── session_store.py    # 会话 JSON 持久化
├── chat_service.py     # LangGraph 事件流 → SSE
├── cli_chat.py         # 命令行测试入口
├── tools/              # Core Tools 实现
├── skills/             # Agent Skills（get_weather 示例）
├── workspace/          # System Prompts（SOUL/IDENTITY/USER/AGENTS + 快照）
├── memory/             # MEMORY.md + logs/
├── sessions/           # JSON 会话记录
├── knowledge/          # RAG 知识库源文件
└── storage/            # RAG 索引持久化
```

## System Prompt 构成（按序拼接）

1. `SKILLS_SNAPSHOT.md`（能力列表，实时生成）
2. `SOUL.md`（核心设定）
3. `IDENTITY.md`（自我认知）
4. `USER.md`（用户画像）
5. `AGENTS.md`（行为准则 & 记忆操作指南）
6. `MEMORY.md`（长期记忆）

单文件超 20k 字符时截断并标注 `...[truncated]`。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | SSE 流式对话（token / tool_start / tool_end / final）|
| GET  | `/api/files?path=` | 读取项目内文件 |
| POST | `/api/files` | 保存文件（Memory / Skill 编辑）|
| GET  | `/api/sessions` | 历史会话列表 |
| POST | `/api/upload` | 上传文件到知识库（PDF/MD/TXT，供 RAG 使用）|
| GET  | `/api/knowledge` | 列出知识库文件 |

## 状态

- [x] Phase 0 脚手架与配置
- [x] Phase 1 Core Tools（terminal / python_repl / fetch_url / read_file）
- [x] Phase 2 Skills 系统（指令遵循范式）
- [x] Phase 3 Agent 编排 + 记忆 + 会话
- [x] Phase 5 FastAPI 接口层（SSE）
- [x] Phase 4 RAG（LlamaIndex Hybrid Search：BM25 + 向量）
- [x] Phase 6 前端 Next.js 三栏 IDE
