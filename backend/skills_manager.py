"""Agent Skills 系统 —— Bootstrap 扫描与快照生成。

遵循"指令遵循"(Instruction-following) 范式：Skills 是教 Agent 如何用 Core Tools
完成任务的说明书（SKILL.md），而非预写的函数。

本模块扫描 backend/skills/ 下每个子目录的 SKILL.md，读取其 frontmatter
（name / description），汇总生成 SKILLS_SNAPSHOT.md（<available_skills> XML 格式），
该快照会被拼进 System Prompt 顶部，供 Agent 感知可用能力。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from config import BACKEND_DIR, SKILLS_DIR, SKILLS_SNAPSHOT_FILE

# 解析 YAML frontmatter（位于文件开头的 --- ... --- 块）
_FRONTMATTER_RE = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class SkillMeta:
    name: str
    description: str
    location: str  # 相对项目根目录的路径（PRD 要求相对路径）


def _parse_frontmatter(text: str) -> dict[str, str]:
    """解析 frontmatter 的 `key: value`，支持多行值。

    在简单单行键值基础上，额外支持两种多行写法，避免 description 写长被截断：
      1. 续行：后续比键更深缩进、或不含 `:` 的行，视为上一个键值的延续。
      2. 块标量：`key: |` 或 `key: >` 起头，其后的缩进块全部并入该键。
    多行值各行以空格拼接，保持单行快照整洁。
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}

    meta: dict[str, str] = {}
    cur_key: str | None = None
    block_mode = False  # 是否处于 |/> 块标量收集中

    for raw_line in m.group(1).splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        indented = raw_line[:1].isspace()

        # 块标量收集：缩进行并入当前键；遇到顶格新行则结束块
        if block_mode and indented:
            meta[cur_key] = (meta[cur_key] + " " + line.strip()).strip()  # type: ignore[index]
            continue
        block_mode = False

        # 顶格且形如 key: value —— 开启新键
        if not indented and ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip("'\"")
            if val in ("|", ">"):  # 块标量起头，值在后续缩进行
                meta[key] = ""
                cur_key = key
                block_mode = True
            else:
                meta[key] = val
                cur_key = key
            continue

        # 缩进行或无冒号行：作为上一个键值的续行
        if cur_key is not None:
            meta[cur_key] = (meta[cur_key] + " " + line.strip()).strip()

    return meta


def scan_skills() -> list[SkillMeta]:
    """扫描 skills 目录，返回所有有效技能的元数据。"""
    skills: list[SkillMeta] = []
    if not SKILLS_DIR.exists():
        return skills

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        text = skill_md.read_text(encoding="utf-8")
        meta = _parse_frontmatter(text)
        name = meta.get("name") or skill_dir.name
        description = meta.get("description", "（无描述）")

        # location 相对 backend/（与 read_file 的 root_dir、terminal 的 cwd 一致），
        # 统一正斜杠跨平台。Agent 可直接 read_file(location) 命中，无需路径试探。
        rel = skill_md.relative_to(BACKEND_DIR).as_posix()
        location = rel

        skills.append(SkillMeta(name=name, description=description, location=location))
    return skills


def render_snapshot(skills: list[SkillMeta]) -> str:
    """渲染为 <available_skills> XML 文本（PRD 2.1 示例格式）。"""
    if not skills:
        return "<available_skills>\n  （当前无可用技能）\n</available_skills>"

    blocks: list[str] = ["<available_skills>"]
    for s in skills:
        blocks.append("  <skill>")
        blocks.append(f"    <name>{s.name}</name>")
        blocks.append(f"    <description>{s.description}</description>")
        blocks.append(f"    <location>{s.location}</location>")
        blocks.append("  </skill>")
    blocks.append("</available_skills>")
    return "\n".join(blocks)


def generate_snapshot() -> str:
    """扫描并把快照写入 SKILLS_SNAPSHOT.md，返回快照文本。"""
    skills = scan_skills()
    snapshot = render_snapshot(skills)
    SKILLS_SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    SKILLS_SNAPSHOT_FILE.write_text(snapshot, encoding="utf-8")
    return snapshot
