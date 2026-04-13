"""淘宝开放平台 TOP 调用与 OAuth（文档以 open.taobao.com 为准，参数名/网关若有变更请按控制台调整）。"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any

TOP_GATEWAY = "https://eco.taobao.com/router/rest"
OAUTH_AUTHORIZE = "https://oauth.taobao.com/authorize"
OAUTH_TOKEN = "https://oauth.taobao.com/token"


def _top_sign(params: dict[str, Any], app_secret: str) -> str:
    keys = sorted(k for k in params if k != "sign" and params[k] is not None and params[k] != "")
    s = app_secret
    for k in keys:
        s += k + str(params[k])
    s += app_secret
    return hashlib.md5(s.encode("utf-8")).hexdigest().upper()


def top_request(
    app_key: str,
    app_secret: str,
    method: str,
    session: str | None,
    biz_params: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    biz_params = biz_params or {}
    params: dict[str, Any] = {
        "method": method,
        "app_key": app_key,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "format": "json",
        "v": "2.0",
        "sign_method": "md5",
        **biz_params,
    }
    if session:
        params["session"] = session
    params["sign"] = _top_sign(params, app_secret)
    body = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(TOP_GATEWAY, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded;charset=utf-8")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"TOP HTTP {e.code}: {raw[:500]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"TOP 网络错误: {e}") from e
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"TOP 返回非 JSON: {raw[:300]}") from e
    err = data.get("error_response")
    if err:
        msg = err.get("sub_msg") or err.get("msg") or str(err)
        code = err.get("code", "")
        raise RuntimeError(f"TOP error {code}: {msg}")
    return data


def oauth_exchange_code(app_key: str, app_secret: str, code: str, redirect_uri: str) -> dict[str, Any]:
    params = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": app_key,
        "client_secret": app_secret,
        "redirect_uri": redirect_uri,
    }
    body = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(OAUTH_TOKEN, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded;charset=utf-8")
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    if "error" in data or "error_description" in data:
        raise RuntimeError(data.get("error_description") or data.get("error") or str(data))
    return data


def build_authorize_url(app_key: str, redirect_uri: str, state: str) -> str:
    q = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": app_key,
            "redirect_uri": redirect_uri,
            "state": state,
            "view": "web",
        }
    )
    return f"{OAUTH_AUTHORIZE}?{q}"


def parse_increment_trades(resp: dict[str, Any]) -> list[dict[str, Any]]:
    """解析 taobao.trades.sold.increment.get 的 JSON 主体，兼容 trade 单条或列表。"""
    key = "trades_sold_increment_get_response"
    if key not in resp:
        for k, v in resp.items():
            if k.endswith("_response") and isinstance(v, dict) and "trades" in v:
                block = v
                break
        else:
            return []
    else:
        block = resp[key]
    trades = block.get("trades")
    if not trades:
        return []
    t = trades.get("trade")
    if t is None:
        return []
    if isinstance(t, list):
        return t
    if isinstance(t, dict):
        return [t]
    return []


def parse_trade_fullinfo(resp: dict[str, Any]) -> dict[str, Any] | None:
    key = "trade_fullinfo_get_response"
    if key not in resp:
        for k, v in resp.items():
            if k.endswith("_response") and isinstance(v, dict) and "trade" in v:
                return v.get("trade")
        return None
    return resp[key].get("trade")
