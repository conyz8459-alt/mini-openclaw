"""fetch_url 工具：获取网页并清洗为纯文本/Markdown。

PRD 要求：原生 RequestsGetTool 返回原始 HTML，Token 消耗巨大。
此处用 requests 获取后，用 html2text + BeautifulSoup 清洗，仅返回精简文本，
工具名固定为 `fetch_url`。
"""
from __future__ import annotations

from typing import Type

import html2text
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# 单次返回给模型的字符上限，防止超长页面撑爆上下文
_MAX_CHARS = 8_000
_TIMEOUT = 15


class FetchUrlInput(BaseModel):
    url: str = Field(description="要获取内容的完整 URL，需以 http:// 或 https:// 开头")


def _clean_html(html: str) -> str:
    """去除 script/style/nav 等噪声标签后转为 Markdown 文本。"""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg", "nav", "footer"]):
        tag.decompose()

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0  # 不自动换行
    text = h.handle(str(soup))

    # 压缩多余空行
    lines = [ln.rstrip() for ln in text.splitlines()]
    compact: list[str] = []
    blank = 0
    for ln in lines:
        if ln.strip() == "":
            blank += 1
            if blank <= 1:
                compact.append("")
        else:
            blank = 0
            compact.append(ln)
    return "\n".join(compact).strip()


class FetchUrlTool(BaseTool):
    """获取指定 URL 的网页内容，返回清洗后的纯文本/Markdown。"""

    name: str = "fetch_url"
    description: str = (
        "获取指定 URL 的网页内容（Agent 联网的核心）。"
        "输入一个完整 URL，返回清洗后的纯文本/Markdown（已去除 HTML 标签与脚本）。"
        "适用于读取网页、调用返回文本/JSON 的 HTTP 接口。"
    )
    args_schema: Type[BaseModel] = FetchUrlInput

    def _run(self, url: str) -> str:  # type: ignore[override]
        if not url.lower().startswith(("http://", "https://")):
            return f"错误：URL 必须以 http:// 或 https:// 开头，收到的是：{url}"
        try:
            resp = requests.get(
                url,
                timeout=_TIMEOUT,
                headers={"User-Agent": "Mozilla/5.0 (mini-openclaw fetch_url)"},
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            return f"获取 URL 失败：{exc}"

        ctype = resp.headers.get("Content-Type", "")
        # 非 HTML（JSON / 纯文本 / API 响应）直接返回原文
        if "text/html" not in ctype:
            text = resp.text
        else:
            text = _clean_html(resp.text)

        if len(text) > _MAX_CHARS:
            text = text[:_MAX_CHARS] + "\n\n...[truncated]"
        return text or "（页面无可提取的文本内容）"

    async def _arun(self, url: str) -> str:  # type: ignore[override]
        return self._run(url)
