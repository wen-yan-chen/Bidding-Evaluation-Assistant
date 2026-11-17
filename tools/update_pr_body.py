"""用 `docs/PR说明.md` 更新 PR #170 的描述。

用法：
    # 令牌优先取环境变量（推荐，避免子进程捕获）
    $env:GITCODE_TOKEN = "<private-token>"
    python tools/update_pr_body.py

    # 没设环境变量时，回退到 git credential fill（需要本机已存 gitcode.com 凭据）
    python tools/update_pr_body.py

正文只维护 `docs/PR说明.md` 一个来源，避免脚本里的字符串与仓库里的说明再次漂移。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BODY_FILE = ROOT / "docs" / "PR说明.md"
PR_URL = "https://gitcode.com/api/v5/repos/ModelEngine/AgentsHub/pulls/170"


def token_from_git() -> str:
    cred = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=gitcode.com\n\n",
        text=True,
        capture_output=True,
        check=True,
    )
    data = dict(line.split("=", 1) for line in cred.stdout.splitlines() if "=" in line)
    return data["password"]


def main() -> int:
    body_file = Path(sys.argv[1]) if len(sys.argv) > 1 else BODY_FILE
    body = body_file.read_text(encoding="utf-8")
    token = os.getenv("GITCODE_TOKEN") or token_from_git()

    resp = requests.patch(
        PR_URL,
        headers={"PRIVATE-TOKEN": token, "Content-Type": "application/json"},
        json={"body": body},
        timeout=30,
    )
    print(f"status: {resp.status_code}")
    if resp.status_code >= 300:
        print(resp.text[:800])
        return 1

    payload = resp.json()
    print(f"state : {payload.get('state')}")
    print(f"title : {payload.get('title')}")
    print(f"chars : {len(body)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
