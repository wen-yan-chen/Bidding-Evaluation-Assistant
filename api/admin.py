"""管理员会话：登录、签名 Cookie、鉴权依赖。

这是**演示用的轻量门禁**，不是完整的账号体系：
- 账号密码来自环境变量 `ADMIN_USER` / `ADMIN_PASSWORD`；
- 成功登录后写入 HttpOnly 签名 Cookie，默认 8 小时；
- 删除等管理接口用 `Depends(require_admin)` 保护；
- `/api/health` / `/api/info` 仍保持公开（容器探针、版本核对需要），
  真正的数据删改接口都在 `/api/admin/*` 下。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import Cookie, Depends, HTTPException, Response, status

from api import config

COOKIE_NAME = "bid_admin"


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_token(user: str) -> str:
    payload = {
        "u": user,
        "exp": int(time.time()) + config.admin_session_ttl(),
    }
    body = _b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    signature = hmac.new(
        config.admin_session_secret().encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{body}.{signature}"


def verify_token(token: str | None) -> str | None:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    expected = hmac.new(
        config.admin_session_secret().encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_b64decode(body).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("u"), str):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload["u"]


def current_admin_optional(
    bid_admin: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> str | None:
    return verify_token(bid_admin)


def require_admin(user: str | None = Depends(current_admin_optional)) -> str:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要管理员登录后才能执行该操作",
        )
    return user


def check_credentials(username: str, password: str) -> bool:
    expected_password = config.admin_password()
    if not expected_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="管理员账号未配置：请在 .env 设置 ADMIN_USER / ADMIN_PASSWORD 后重启服务",
        )
    user_ok = hmac.compare_digest(username or "", config.admin_user())
    password_ok = hmac.compare_digest(password or "", expected_password)
    return user_ok and password_ok


def set_session_cookie(response: Response, user: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_token(user),
        max_age=config.admin_session_ttl(),
        httponly=True,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")
