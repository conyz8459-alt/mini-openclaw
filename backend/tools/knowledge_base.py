"""search_knowledge_base 工具：本地知识库混合检索（PRD 第二节 5）。

Hybrid Search = BM25（关键词）+ Vector（向量），用 QueryFusionRetriever 融合两路结果。
工具名固定为 `search_knowledge_base`。

检索器构建较重（加载索引 + 重建 BM25），故进程内缓存；知识库变化时
（上传新文件）由 app.py 调用 invalidate_retriever_cache() 失效，下次检索重建。
"""
from __future__ import annotations

from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class KBSearchInput(BaseModel):
    query: str = Field(description="要在知识库中检索的问题或关键词")


# 进程内缓存：检索器构建较重，避免每次搜索都从磁盘重建。
# None 有两种含义，故用单独的「已构建」标志区分「尚未构建」与「知识库为空」。
_retriever_cache = None
_retriever_built = False


def invalidate_retriever_cache() -> None:
    """使检索器缓存失效（知识库文件变化后调用，下次检索重建）。"""
    global _retriever_cache, _retriever_built
    _retriever_cache = None
    _retriever_built = False


def _build_retriever():
    """构建 BM25 + 向量的融合检索器；知识库为空时返回 None。"""
    from llama_index.core.retrievers import QueryFusionRetriever
    from llama_index.retrievers.bm25 import BM25Retriever

    from rag_index import build_index

    index = build_index()
    if index is None:
        return None

    vector_retriever = index.as_retriever(similarity_top_k=4)
    nodes = list(index.docstore.docs.values())
    bm25_retriever = BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=4)

    # 融合两路检索结果（相对分数融合），输出 top-4
    return QueryFusionRetriever(
        [vector_retriever, bm25_retriever],
        similarity_top_k=4,
        num_queries=1,  # 不做查询改写，避免额外 LLM 调用
        mode="relative_score",
        use_async=False,
        llm=None,
    )


def _get_retriever():
    """返回缓存的检索器；未构建则构建并缓存。"""
    global _retriever_cache, _retriever_built
    if not _retriever_built:
        _retriever_cache = _build_retriever()
        _retriever_built = True
    return _retriever_cache


class KnowledgeBaseTool(BaseTool):
    """在本地知识库中做混合检索（BM25 + 向量）。"""

    name: str = "search_knowledge_base"
    description: str = (
        "检索用户上传的本地知识库文档（PDF/MD/TXT）。"
        "仅在用户明确提到要查阅资料、文档、知识库，或所问内容显然依赖已上传的特定文档时才调用；"
        "对于闲聊、常识问答、可凭自身知识或其他工具回答的问题，不要调用本工具。"
        "采用关键词+向量混合检索，返回最相关的文档片段。"
    )
    args_schema: Type[BaseModel] = KBSearchInput

    def _run(self, query: str) -> str:  # type: ignore[override]
        retriever = _get_retriever()
        if retriever is None:
            return "知识库为空：请先在 backend/knowledge/ 目录放入 PDF/MD/TXT 文件。"
        nodes = retriever.retrieve(query)
        if not nodes:
            return "知识库中未检索到与该问题相关的内容。"
        parts: list[str] = []
        for i, n in enumerate(nodes, 1):
            src = n.node.metadata.get("file_name", "未知来源")
            parts.append(f"【片段 {i}｜来源：{src}｜相关度：{n.score:.3f}】\n{n.node.get_content().strip()}")
        return "\n\n".join(parts)

    async def _arun(self, query: str) -> str:  # type: ignore[override]
        return self._run(query)


def build_knowledge_base_tool() -> BaseTool:
    return KnowledgeBaseTool()
