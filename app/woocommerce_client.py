"""WooCommerce REST API（/wp-json/wc/v3），使用 Consumer Key + Secret 的 Basic 鉴权。"""

from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_TIMEOUT = 90


def _basic_auth_header(consumer_key: str, consumer_secret: str) -> str:
    token = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def wc_request(
    site_url: str,
    consumer_key: str,
    consumer_secret: str,
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    base = site_url.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    url = base + "/wp-json/wc/v3" + path
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)
    data = None
    headers = {
        "Authorization": _basic_auth_header(consumer_key.strip(), consumer_secret.strip()),
        "Accept": "application/json",
    }
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(raw)
            msg = err.get("message") or err.get("code") or raw[:400]
        except json.JSONDecodeError:
            msg = raw[:400]
        raise RuntimeError(f"WooCommerce HTTP {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"WooCommerce 网络错误: {e}") from e
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"WooCommerce 返回非 JSON: {raw[:200]}") from e


def list_orders(
    site_url: str,
    consumer_key: str,
    consumer_secret: str,
    *,
    after_iso: str | None = None,
    statuses: list[str] | None = None,
    page: int = 1,
    per_page: int = 50,
) -> list[dict[str, Any]]:
    q: dict[str, Any] = {
        "page": page,
        "per_page": per_page,
        "orderby": "modified",
        "order": "asc",
    }
    if after_iso:
        q["modified_after"] = after_iso
    if statuses:
        q["status"] = ",".join(statuses)
    data = wc_request(site_url, consumer_key, consumer_secret, "GET", "/orders", query=q)
    if not isinstance(data, list):
        return []
    return data


def update_order(
    site_url: str,
    consumer_key: str,
    consumer_secret: str,
    order_id: int,
    body: dict[str, Any],
) -> dict[str, Any]:
    out = wc_request(site_url, consumer_key, consumer_secret, "PUT", f"/orders/{order_id}", json_body=body)
    if not isinstance(out, dict):
        raise RuntimeError("WooCommerce 更新订单返回异常")
    return out
