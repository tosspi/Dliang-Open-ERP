const msgEl = document.getElementById("msg");
const showMsg = (m, err = false) => {
  msgEl.textContent = m;
  msgEl.className = err ? "msg err" : "msg ok";
};

function showUrlParamsHint() {
  const q = new URLSearchParams(window.location.search);
  const sp = q.get("sales_platform");
  if (sp === "taobao_ok") showMsg("淘宝店铺授权成功，可到「销售订单」同步订单。");
  if (sp === "taobao_error") {
    const r = q.get("reason") || "";
    showMsg("淘宝授权未完成：" + decodeURIComponent(r), true);
  }
}

async function loadTaobaoConfig() {
  const hint = document.getElementById("tb_callback_hint");
  if (hint) {
    hint.textContent = `${window.location.origin}/integrations/taobao/callback`;
  }
  const res = await fetch("/integrations/taobao/config");
  if (!res.ok) return;
  const c = await res.json();
  document.getElementById("tb_app_key").value = c.taobao_app_key || "";
  document.getElementById("tb_redirect_uri").value =
    c.taobao_redirect_uri || `${window.location.origin}/integrations/taobao/callback`;
  document.getElementById("tb_default_logistics").value = c.taobao_default_logistics_code || "";
  const st = document.getElementById("tb_auth_status");
  if (st) {
    if (c.taobao_authorized) {
      st.textContent = `已授权店铺：${c.taobao_seller_nick || "—"}${c.taobao_token_expire_time ? "；Token 到期：" + String(c.taobao_token_expire_time).slice(0, 19) : ""}`;
    } else {
      st.textContent = "尚未完成淘宝授权，请保存 App 配置后点击「跳转淘宝授权」。";
    }
  }
}

document.getElementById("tb_save").addEventListener("click", async () => {
  const payload = {
    taobao_app_key: document.getElementById("tb_app_key").value.trim() || null,
    taobao_redirect_uri: document.getElementById("tb_redirect_uri").value.trim() || null,
    taobao_default_logistics_code: document.getElementById("tb_default_logistics").value.trim() || null,
  };
  const sec = document.getElementById("tb_app_secret").value;
  if (sec) payload.taobao_app_secret = sec;
  const res = await fetch("/integrations/taobao/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail) || "保存失败", true);
  }
  document.getElementById("tb_app_secret").value = "";
  showMsg("淘宝配置已保存");
  loadTaobaoConfig();
});

document.getElementById("tb_oauth").addEventListener("click", async () => {
  const res = await fetch("/integrations/taobao/oauth-url", { method: "POST" });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail) || "无法生成授权链接", true);
  }
  const data = await res.json();
  window.location.href = data.authorization_url;
});

async function loadWooCommerceConfig() {
  const res = await fetch("/integrations/woocommerce/config");
  if (!res.ok) return;
  const c = await res.json();
  const urlEl = document.getElementById("wc_site_url");
  if (!urlEl) return;
  urlEl.value = c.woocommerce_site_url || "";
  document.getElementById("wc_ck").value = "";
  const hint = document.getElementById("wc_sync_hint");
  if (hint) {
    hint.textContent = c.woocommerce_last_sync
      ? `上次同步锚点（UTC 存库）：${String(c.woocommerce_last_sync).slice(0, 19)}`
      : "尚未成功同步过；首次将按回溯小时数拉取修改过的订单。";
  }
}

document.getElementById("wc_save").addEventListener("click", async () => {
  const payload = {
    woocommerce_site_url: document.getElementById("wc_site_url").value.trim() || null,
  };
  const ck = document.getElementById("wc_ck").value.trim();
  const cs = document.getElementById("wc_cs").value;
  if (ck) payload.woocommerce_consumer_key = ck;
  if (cs) payload.woocommerce_consumer_secret = cs;
  const res = await fetch("/integrations/woocommerce/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail) || "保存失败", true);
  }
  document.getElementById("wc_cs").value = "";
  document.getElementById("wc_ck").value = "";
  showMsg("WooCommerce 配置已保存");
  loadWooCommerceConfig();
});

showUrlParamsHint();
loadTaobaoConfig();
loadWooCommerceConfig();
