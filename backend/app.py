"""Mini-OpenClaw 后端入口（FastAPI, Port 8002）。

接口（PRD 第五节 + 扩展）：
  POST /api/chat      —— SSE 流式对话
  GET  /api/files     —— 读取项目内文件
  POST /api/files     —— 保存对 Memory / Skill 文件的修改
  GET  /api/sessions  —— 历史会话列表
  POST /api/upload    —— 上传文件到知识库（扩展，供 RAG 使用）
  GET  /api/knowledge —— 列出知识库文件（扩展）
"""
from __future__ import annotations

import shutil
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import BACKEND_DIR, CORS_ORIGINS, KNOWLEDGE_DIR, SENSITIVE_FILENAMES, STORAGE_DIR, WORKSPACE_DIR, SERVER_HOST, SERVER_PORT, ensure_dirs
from chat_service import stream_chat
from session_store import delete_session, list_sessions, read_session_raw, rename_session
from skills_manager import scan_skills


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """应用生命周期：启动时确保核心目录存在（替代废弃的 on_event）。"""
    ensure_dirs()
    yield


app = FastAPI(title="Mini-OpenClaw API", version="0.1.0", lifespan=_lifespan)

# 前后端分离：放行本地前端来源（默认仅 localhost:3000，可经 CORS_ORIGINS 配置）
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 数据模型 ----------
class ChatRequest(BaseModel):
    message: str
    session_id: str = "main_session"
    stream: bool = True


class FileSaveRequest(BaseModel):
    path: str
    content: str


# ---------- 路径沙箱 ----------
def _safe_path(rel_path: str) -> Path:
    """把前端传入的相对路径解析为 backend/ 内的绝对路径，越界或命中敏感文件则拒绝。"""
    target = (BACKEND_DIR / rel_path).resolve()
    try:
        target.relative_to(BACKEND_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="路径越界：禁止访问项目目录之外的文件")
    if target.name in SENSITIVE_FILENAMES:
        raise HTTPException(status_code=403, detail=f"禁止访问敏感文件：{target.name}")
    return target


# ---------- 1. 核心对话接口（SSE）----------
@app.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_chat(req.message, req.session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------- 2. 文件管理接口 ----------
@app.get("/api/files")
def read_file_api(path: str = Query(...)) -> dict[str, str]:
    target = _safe_path(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"文件不存在：{path}")
    return {"path": path, "content": target.read_text(encoding="utf-8")}


@app.post("/api/files")
def save_file_api(req: FileSaveRequest) -> dict[str, str]:
    target = _safe_path(req.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(req.content, encoding="utf-8")
    return {"status": "ok", "path": req.path}


# ---------- 3. 会话管理接口 ----------
@app.get("/api/sessions")
def sessions_api() -> dict[str, list]:
    return {"sessions": list_sessions()}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, list]:
    """读取单个会话的消息（用于历史回放，仅 user/assistant 文字）。"""
    return {"messages": read_session_raw(session_id)}


@app.delete("/api/sessions/{session_id}")
def delete_session_api(session_id: str) -> dict[str, str]:
    """删除一个会话。"""
    deleted = delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"会话不存在：{session_id}")
    return {"status": "ok", "session_id": session_id}


class SessionRenameRequest(BaseModel):
    new_id: str


@app.patch("/api/sessions/{session_id}")
def rename_session_api(session_id: str, req: SessionRenameRequest) -> dict[str, str]:
    """重命名会话 = 修改显示标题（文件名不变），返回生效的标题。"""
    new_name = (req.new_id or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="新名称不能为空")
    try:
        title = rename_session(session_id, new_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"会话不存在：{session_id}")
    return {"status": "ok", "session_id": session_id, "title": title}


@app.get("/api/skills")
def list_skills_api() -> dict[str, list]:
    """列出所有技能（供检查器动态显示）。"""
    skills = [
        {"name": s.name, "description": s.description, "location": s.location}
        for s in scan_skills()
    ]
    return {"skills": skills}


# ---------- 4. 知识库文件上传（RAG）----------
_ALLOWED_EXTS = {".pdf", ".md", ".txt"}


def _invalidate_retriever_cache() -> None:
    """清空进程内检索器缓存（RAG 依赖可能未装，容错处理）。"""
    try:
        from tools.knowledge_base import invalidate_retriever_cache

        invalidate_retriever_cache()
    except Exception:  # noqa: BLE001
        pass


def _invalidate_kb_index() -> None:
    """删除已持久化的索引并清空检索器缓存，使下次检索基于新文件重建。"""
    persist = STORAGE_DIR / "kb_index"
    if persist.exists():
        shutil.rmtree(persist, ignore_errors=True)
    _invalidate_retriever_cache()


def _index_uploaded_file(filename: str) -> None:
    """上传后入库：优先增量（仅 embedding 新文件），失败则降级为删全量索引。"""
    try:
        from rag_index import add_file_to_index

        add_file_to_index(filename)
        _invalidate_retriever_cache()  # 索引已更新，让检索器重新加载
    except Exception as exc:  # noqa: BLE001 —— 增量失败时退回旧行为，保证可用
        print(f"[upload] 增量入库失败（{exc}），降级为重建全量索引。")
        _invalidate_kb_index()


@app.post("/api/upload")
async def upload_knowledge(file: UploadFile = File(...)) -> dict[str, str]:
    """上传文件到 knowledge/ 供 RAG 检索。仅接受 pdf/md/txt。"""
    name = Path(file.filename or "").name
    ext = Path(name).suffix.lower()
    if not name or ext not in _ALLOWED_EXTS:
        raise HTTPException(
            status_code=400, detail="仅支持上传 .pdf / .md / .txt 文件"
        )
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    dest = KNOWLEDGE_DIR / name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    # 增量入库：仅 embedding 新文件并插入已有索引（失败自动降级重建）
    _index_uploaded_file(name)
    return {"status": "ok", "filename": name}


@app.get("/api/knowledge")
def list_knowledge() -> dict[str, list]:
    """列出知识库中的文件。"""
    files: list[dict[str, object]] = []
    if KNOWLEDGE_DIR.exists():
        for p in sorted(KNOWLEDGE_DIR.rglob("*")):
            if p.is_file() and p.suffix.lower() in _ALLOWED_EXTS:
                files.append({"name": p.name, "size": p.stat().st_size})
    return {"files": files}


@app.delete("/api/knowledge/{filename}")
def delete_knowledge(filename: str) -> dict[str, str]:
    """删除知识库文件，并同步移除其索引节点（增量删除，不动其他文件）。"""
    name = Path(filename).name  # 防路径穿越
    target = KNOWLEDGE_DIR / name
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"知识库文件不存在：{name}")
    # 先删索引节点（失败则降级为删全量索引），再删磁盘文件
    try:
        from rag_index import remove_file_from_index

        remove_file_from_index(name)
        _invalidate_retriever_cache()
    except Exception as exc:  # noqa: BLE001 —— 增量删除失败时退回重建全量索引
        print(f"[delete] 增量删除索引失败（{exc}），降级为重建全量索引。")
        _invalidate_kb_index()
    target.unlink()
    return {"status": "ok", "filename": name}


# ---------- 5. 对话临时文件（不进知识库，供 Agent 用 read_file 读取）----------
_TEMP_DIR = WORKSPACE_DIR / "temp"


@app.post("/api/upload/temp")
async def upload_temp(file: UploadFile = File(...)) -> dict[str, str]:
    """上传临时文件到 workspace/temp/，返回相对路径供对话引用。

    不限制类型为 pdf/md/txt——临时看文件可能是各种文本/代码文件。
    """
    name = Path(file.filename or "").name
    if not name:
        raise HTTPException(status_code=400, detail="文件名无效")
    _TEMP_DIR.mkdir(parents=True, exist_ok=True)
    dest = _TEMP_DIR / name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    # 返回相对 backend/ 的路径，Agent 可直接 read_file 读取
    rel = dest.relative_to(BACKEND_DIR).as_posix()
    return {"status": "ok", "filename": name, "path": rel}


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mini-openclaw", "status": "running", "port": str(SERVER_PORT)}


if __name__ == "__main__":
    ensure_dirs()
    uvicorn.run("app:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
