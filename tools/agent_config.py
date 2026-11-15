"""agent.json ↔ prompt.md 的单一来源维护 + 配置校验。

为什么要这个脚本：提示词会被写进两处（prompt.md 给人读、agent.json 给平台导入），
手改必然漂移。这里固定"只从 prompt.md 写入 JSON"一个方向，check 在 CI / PR 前跑。

用法：
  python tools/agent_config.py sync            # prompt.md → agent.json.prompt
  python tools/agent_config.py check           # 校验（有 ERROR 退出码 1）
  python tools/agent_config.py check --strict  # PR 前用：占位符未替换也算失败
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
AGENT_FILE = ROOT / "agent.json"
PROMPT_FILE = ROOT / "prompt.md"
DISCLAIMER = "AI 辅助评审结果，最终以评标委员会评审结论为准"

PLACEHOLDER_TOKENS = ("REPLACE_ME", "TODO", "your-")

LEVEL_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2, "OK": 3}
LEVEL_MARK = {"ERROR": "[ERROR]", "WARN": "[WARN ]", "INFO": "[INFO ]", "OK": "[ OK  ]"}


def load_agent() -> dict[str, Any]:
    return json.loads(AGENT_FILE.read_text(encoding="utf-8"))


def prompt_text() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8").strip()


def agent_body(agent: dict[str, Any]) -> dict[str, Any]:
    return (agent.get("agent_info") or {}).get("0") or {}


def cmd_sync() -> int:
    agent = load_agent()
    body = agent_body(agent)
    text = prompt_text()
    before = body.get("prompt") or ""

    body["prompt"] = text
    AGENT_FILE.write_text(
        json.dumps(agent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"已同步 prompt.md → agent.json.prompt（{len(text)} 字符）")
    if not before:
        print("  首次写入")
    elif before == text:
        print("  内容无变化")
    else:
        print(f"  内容已更新（旧 {len(before)} 字符 → 新 {len(text)} 字符），记得跑 check")
    return 0


def collect(agent: dict[str, Any], strict: bool) -> list[tuple[str, str, str]]:
    """返回 [(level, 检查项, 说明)]。strict 下 INFO 也升级为 WARN。"""
    rows: list[tuple[str, str, str]] = []
    body = agent_body(agent)
    mcp = agent.get("mcp_info") or []
    tools = [t for entry in mcp for t in entry.get("tools") or []]
    index_names = [
        name
        for t in body.get("tools") or []
        if t.get("class_name") == "KnowledgeBaseSearchTool"
        for name in (t.get("params") or {}).get("index_names") or []
    ]

    def add(level: str, item: str, detail: str) -> None:
        rows.append((level, item, detail))

    # ---- 结构 ----
    if not body:
        add("ERROR", "agent_info['0'] 存在", "缺失，平台导入会失败")
        return rows
    add("OK", "agent_info['0'] 存在", f"name={body.get('name')}")

    if body.get("prompt"):
        add("OK", "prompt 非空", f"{len(body['prompt'])} 字符")
    else:
        add("ERROR", "prompt 非空", "为空，先跑 `python tools/agent_config.py sync`")

    # ---- 一致性与硬参数 ----
    text = prompt_text()
    same = (body.get("prompt") or "").strip() == text
    add(
        "OK" if same else "ERROR",
        "prompt 与 prompt.md 逐字一致",
        "一致" if same else "不一致，跑 `sync` 重新生成（禁止手改 JSON）",
    )

    temp = (
        ((body.get("model_params_override") or {}).get("0") or {}).get("extra_params")
        or {}
    ).get("temperature")
    add(
        "OK" if temp == 0 else "ERROR",
        "temperature = 0",
        f"当前 {temp!r}" + ("（否则同一输入多次结论不一致）" if temp != 0 else ""),
    )

    max_steps = body.get("max_steps")
    add(
        "OK" if isinstance(max_steps, int) and 5 <= max_steps <= 20 else "WARN",
        "max_steps 合理（5–20）",
        f"当前 {max_steps!r}",
    )

    skills = body.get("skill_names") or []
    add(
        "OK" if len(skills) >= 4 else "WARN",
        "skill_names ≥ 4",
        f"当前 {len(skills)} 个：{', '.join(skills) or '无'}",
    )

    add(
        "OK" if len(tools) >= 6 else "WARN",
        "MCP 工具 ≥ 6",
        f"当前 {len(tools)} 个：{', '.join(t.get('name', '?') for t in tools) or '无'}",
    )

    # ---- 环境相关（必须留给导入方改的地方）----
    if index_names:
        dirty = [n for n in index_names if any(tok in str(n) for tok in PLACEHOLDER_TOKENS)]
        if dirty:
            add(
                "ERROR" if strict else "WARN",
                "知识库 index_names 已替换",
                f"占位：{dirty[0]}（导入后检索会被权限过滤，输出退化为“未检索到权威依据”）",
            )
        else:
            add("OK", "知识库 index_names 已替换", f"{len(index_names)} 个索引")
    else:
        add("WARN", "知识库 index_names 非空", "未配置知识库检索工具")

    author = body.get("author") or ""
    if any(tok in author for tok in PLACEHOLDER_TOKENS):
        add(
            "ERROR" if strict else "WARN",
            "author 已填",
            f"占位：{author}，提交前改成 AtomGit ID",
        )
    else:
        add("OK", "author 已填", author)

    model_names = body.get("model_names") or []
    if model_names:
        add("INFO", "model_names", f"写死 {model_names}，换环境可能导入失败")
    else:
        add("INFO", "model_names 留空", "导入后由平台选择本环境模型，符合手册 §5.4 建议")

    urls = [entry.get("mcp_url") or "" for entry in mcp]
    bad_urls = [u for u in urls if "localhost" in u]
    if bad_urls:
        add("WARN", "mcp_url 不用 localhost", f"{bad_urls[0]}（平台内解析不到）")
    else:
        add("OK", "mcp_url 非 localhost", urls[0] if urls else "未配置")

    if DISCLAIMER in (body.get("prompt") or ""):
        add("OK", "提示词含免责声明原文", DISCLAIMER)
    else:
        add("ERROR", "提示词含免责声明原文", "缺失，赛题第 6 条要求三处提示")

    if strict:
        rows = [
            ("WARN", item, detail) if level == "INFO" else (level, item, detail)
            for level, item, detail in rows
        ]
    return rows


def cmd_check(strict: bool) -> int:
    try:
        agent = load_agent()
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] agent.json 无法解析：{exc}")
        return 1

    rows = collect(agent, strict)
    rows.sort(key=lambda r: LEVEL_ORDER[r[0]])

    width = max(len(r[1]) for r in rows) if rows else 0
    for level, item, detail in rows:
        print(f"{LEVEL_MARK[level]} {item.ljust(width)}  {detail}")

    errors = sum(1 for r in rows if r[0] == "ERROR")
    warns = sum(1 for r in rows if r[0] == "WARN")
    oks = sum(1 for r in rows if r[0] == "OK")
    print()
    print(f"合计 {len(rows)} 项：OK {oks} / WARN {warns} / ERROR {errors}"
          + ("（strict 模式）" if strict else ""))
    if errors:
        print("结论：不通过。ERROR 项必须修掉再提交。")
        return 1
    if strict and warns:
        print("结论：strict 模式不允许 WARN，请处理。")
        return 1
    print("结论：结构可用。WARN/INFO 为环境相关项，导入前按 README 处理。")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="agent.json 配置维护与校验")
    ap.add_argument("command", choices=["sync", "check"], help="sync 写入 / check 校验")
    ap.add_argument("--strict", action="store_true", help="占位符、model_names 也视为不通过")
    args = ap.parse_args(argv)

    if args.command == "sync":
        return cmd_sync()
    return cmd_check(args.strict)


if __name__ == "__main__":
    sys.exit(main())
