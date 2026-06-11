"""RAG 索引引擎（LlamaIndex Hybrid Search）。

- 扫描 knowledge/ 下的 PDF/MD/TXT，构建索引
- 混合检索：BM25（关键词，本地零成本）+ Vector（向量，bge-m3）
- 持久化到 storage/，二次启动直接加载，无需重建

向量 embedding 走 OpenAI 兼容端点（默认硅基流动 bge-m3）。
"""
from __future__ import annotations

from pathlib import Path

from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding

from config import EMBED_API_KEY, EMBED_BASE_URL, EMBED_MODEL, KNOWLEDGE_DIR, STORAGE_DIR

# LlamaIndex 默认会找 OpenAI LLM 做合成；这里只做检索，关闭 LLM 依赖
Settings.llm = None
Settings.embed_model = OpenAIEmbedding(
    model_name=EMBED_MODEL,
    api_key=EMBED_API_KEY,
    api_base=EMBED_BASE_URL,
    embed_batch_size=16,
)
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=64)

_PERSIST_DIR = STORAGE_DIR / "kb_index"


def _has_knowledge_files() -> bool:
    if not KNOWLEDGE_DIR.exists():
        return False
    exts = {".pdf", ".md", ".txt"}
    return any(p.suffix.lower() in exts for p in KNOWLEDGE_DIR.rglob("*") if p.is_file())


def build_index(force: bool = False) -> VectorStoreIndex | None:
    """构建（或加载已有）向量索引并持久化。

    knowledge/ 为空时返回 None（无可索引内容）。
    """
    if not _has_knowledge_files():
        return None

    if _PERSIST_DIR.exists() and not force:
        storage = StorageContext.from_defaults(persist_dir=str(_PERSIST_DIR))
        return load_index_from_storage(storage)

    docs = SimpleDirectoryReader(
        input_dir=str(KNOWLEDGE_DIR),
        recursive=True,
        required_exts=[".pdf", ".md", ".txt"],
    ).load_data()
    index = VectorStoreIndex.from_documents(docs)
    _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(_PERSIST_DIR))
    return index


def remove_file_from_index(filename: str) -> bool:
    """从索引中删除某个文件的所有节点（增量删除，不动其他文件）。

    用于「删除知识库文件」：先删磁盘文件对应的索引节点，避免检索到已删内容。
    返回是否执行了删除操作。无持久化索引时直接返回 False（无需处理）。
    """
    if not _PERSIST_DIR.exists():
        return False
    storage = StorageContext.from_defaults(persist_dir=str(_PERSIST_DIR))
    index = load_index_from_storage(storage)
    ref_ids = {
        node.ref_doc_id
        for node in index.docstore.docs.values()
        if node.metadata.get("file_name") == filename and node.ref_doc_id
    }
    if not ref_ids:
        return False
    for ref_id in ref_ids:
        try:
            index.delete_ref_doc(ref_id, delete_from_docstore=True)
        except Exception:  # noqa: BLE001 —— 个别节点删除失败不阻断
            pass
    index.storage_context.persist(persist_dir=str(_PERSIST_DIR))
    return True
    """增量入库：只对新上传的单个文件做 embedding 并插入已有索引。

    避免「上传即删全量索引、下次搜索重嵌入整个知识库」的浪费。
    - 尚无索引（首次上传）：直接全量构建（此时通常就这一个文件，等价增量）。
    - 已有索引：仅读取该文件做 embedding 后插入；重复上传同名文件时
      先按 file_name 删除旧节点去重，防止检索结果重复。
    返回更新后的索引；该文件不存在或知识库为空时返回 None。
    """
    target = KNOWLEDGE_DIR / filename
    if not target.exists():
        return None

    # 首次上传，尚无持久化索引：全量构建即可
    if not _PERSIST_DIR.exists():
        return build_index(force=True)

    storage = StorageContext.from_defaults(persist_dir=str(_PERSIST_DIR))
    index = load_index_from_storage(storage)

    # 去重：删除同名文件对应的旧 ref_doc（重复上传同名文件的情形）
    stale_ref_ids = {
        node.ref_doc_id
        for node in index.docstore.docs.values()
        if node.metadata.get("file_name") == filename and node.ref_doc_id
    }
    for ref_id in stale_ref_ids:
        try:
            index.delete_ref_doc(ref_id, delete_from_docstore=True)
        except Exception:  # noqa: BLE001 —— 个别节点删除失败不阻断插入
            pass

    # 仅对该文件做 embedding 并插入
    docs = SimpleDirectoryReader(input_files=[str(target)]).load_data()
    for doc in docs:
        index.insert(doc)
    index.storage_context.persist(persist_dir=str(_PERSIST_DIR))
    return index
