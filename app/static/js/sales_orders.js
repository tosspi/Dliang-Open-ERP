const msgEl = document.getElementById("msg");
const showMsg = (m, err = false) => {
  msgEl.textContent = m;
  msgEl.className = err ? "msg err" : "msg ok";
};

const localStatusText = (s) =>
  ({
    draft: "草稿",
    pending_payment: "待付款",
    pending_ship: "待发货",
    partial_shipped: "部分发货",
    shipped: "已发货",
    completed: "已完成",
    closed: "已关闭",
    other: "其他",
  }[s] || s);

const invoiceStatusText = (s) =>
  ({
    none: "未开票",
    pending: "待开票",
    issued: "已开票",
    not_required: "不开票",
  }[s] || s || "—");

const channelText = (c) =>
  c === "woocommerce" ? "WooCommerce" : c === "taobao" ? "淘宝" : c === "manual" ? "手工单" : c || "—";

function fmtMoney(v) {
  const x = Number(v);
  return Number.isFinite(x) ? x.toFixed(2) : "—";
}

function parseDec(v) {
  const x = Number(String(v).replace(",", "."));
  return Number.isFinite(x) ? x : NaN;
}

function canTaobaoShip(r) {
  return (
    r.channel === "taobao" &&
    r.platform_status === "WAIT_SELLER_SEND_GOODS" &&
    !r.taobao_consigned_at
  );
}

function canWooShip(r) {
  return (
    r.channel === "woocommerce" &&
    (r.platform_status === "processing" || r.platform_status === "on-hold") &&
    !r.taobao_consigned_at
  );
}

function canManualShip(r) {
  return r.channel === "manual" && r.local_status === "pending_ship";
}

function canManualEdit(r) {
  return r.channel === "manual" && r.local_status === "draft";
}

function canManualConfirm(r) {
  return r.channel === "manual" && r.local_status === "draft";
}

async function loadDefaultLogisticsTaobao() {
  try {
    const res = await fetch("/integrations/taobao/config");
    if (!res.ok) return;
    const c = await res.json();
    if (c.taobao_default_logistics_code) {
      document.getElementById("so_company_code").value = c.taobao_default_logistics_code;
    }
  } catch (_) {}
}

function openShipModal(orderId, channel, hint) {
  document.getElementById("so_ship_order_id").value = String(orderId);
  document.getElementById("so_ship_channel").value = channel;
  document.getElementById("so-ship-hint").textContent = hint || "";
  const pt = document.getElementById("ship_panel_taobao");
  const pw = document.getElementById("ship_panel_woo");
  const pm = document.getElementById("ship_panel_manual");
  const title = document.getElementById("so_ship_title");
  pt.classList.add("hidden");
  pw.classList.add("hidden");
  pm.classList.add("hidden");
  if (channel === "manual") {
    title.textContent = "手工单本地发货";
    pm.classList.remove("hidden");
    document.getElementById("so_manual_tracking").value = "";
    document.getElementById("so_manual_carrier").value = "";
  } else if (channel === "woocommerce") {
    title.textContent = "WooCommerce 发货 / 运单回写";
    pw.classList.remove("hidden");
    document.getElementById("so_wc_tracking").value = "";
    document.getElementById("so_wc_carrier").value = "";
    document.getElementById("so_wc_completed").checked = true;
  } else {
    title.textContent = "淘宝线下发货回写";
    pt.classList.remove("hidden");
    document.getElementById("so_out_sid").value = "";
    loadDefaultLogisticsTaobao();
  }
  document.getElementById("so-ship-modal").classList.remove("hidden");
}

function platformRefCol(r) {
  if (r.channel === "manual") return r.platform_order_no || "—";
  return r.platform_order_no || r.platform_tid || "—";
}

/** @type {Array<Record<string, unknown>> | null} */
let _productsCache = null;

async function ensureProducts() {
  if (_productsCache) return _productsCache;
  const res = await fetch("/products");
  if (!res.ok) throw new Error("加载产品列表失败");
  const raw = await res.json();
  _productsCache = raw.filter((p) => p.is_active !== false);
  _productsCache.sort((a, b) =>
    String(a.product_code || "").localeCompare(String(b.product_code || ""), "zh-CN")
  );
  return _productsCache;
}

function applyProductToRow(tr, productIdStr) {
  const id = Number(productIdStr);
  const p = (_productsCache || []).find((x) => x.id === id);
  if (!p) return;
  const titleEl = tr.querySelector(".so-m-title");
  const priceEl = tr.querySelector(".so-m-price");
  if (titleEl) titleEl.value = p.product_name || "";
  if (priceEl) priceEl.value = p.sale_price_with_tax != null ? String(p.sale_price_with_tax) : "";
  const codeEl = tr.querySelector(".so-m-code");
  const midEl = tr.querySelector(".so-m-mid");
  if (codeEl) codeEl.value = "";
  if (midEl) midEl.value = "";
  const ltEl = tr.querySelector(".so-m-lt");
  if (ltEl) ltEl.value = "";
}

function buildProductSelect(selectedId) {
  const sel = document.createElement("select");
  sel.className = "so-m-product";
  sel.style.width = "100%";
  sel.style.maxWidth = "240px";
  const o0 = document.createElement("option");
  o0.value = "";
  o0.textContent = "— 选产品 —";
  sel.appendChild(o0);
  for (const p of _productsCache || []) {
    const o = document.createElement("option");
    o.value = String(p.id);
    const label = `${p.product_code || ""} · ${p.product_name || ""}`.trim();
    o.textContent = label.length > 58 ? `${label.slice(0, 56)}…` : label;
    if (selectedId != null && String(p.id) === String(selectedId)) o.selected = true;
    sel.appendChild(o);
  }
  return sel;
}

function addManualLineRow(tb, obj = {}) {
  const tr = document.createElement("tr");
  tr.className = "so-m-line";
  const mkCell = (child) => {
    const td = document.createElement("td");
    td.appendChild(child);
    return td;
  };
  const tProd = buildProductSelect(obj.product_id);
  const tTitle = document.createElement("input");
  tTitle.type = "text";
  tTitle.className = "so-m-title";
  tTitle.style.width = "100%";
  tTitle.value = obj.title || "";
  const tCode = document.createElement("input");
  tCode.type = "text";
  tCode.className = "so-m-code";
  tCode.style.width = "100%";
  tCode.value = obj.material_code || obj.outer_iid || "";
  tCode.placeholder = "可选";
  const tMid = document.createElement("input");
  tMid.type = "hidden";
  tMid.className = "so-m-mid";
  tMid.value = obj.material_id != null ? String(obj.material_id) : "";
  tCode.addEventListener("input", () => {
    tMid.value = "";
    tProd.value = "";
  });
  tProd.addEventListener("change", () => {
    if (tProd.value) applyProductToRow(tr, tProd.value);
  });
  const tQty = document.createElement("input");
  tQty.type = "number";
  tQty.className = "so-m-qty";
  tQty.step = "any";
  tQty.style.width = "100%";
  tQty.value = obj.qty != null ? String(obj.qty) : "";
  const tPrice = document.createElement("input");
  tPrice.type = "number";
  tPrice.className = "so-m-price";
  tPrice.step = "0.01";
  tPrice.style.width = "100%";
  tPrice.value = obj.price != null ? String(obj.price) : "";
  const tLt = document.createElement("input");
  tLt.type = "number";
  tLt.className = "so-m-lt";
  tLt.step = "0.01";
  tLt.style.width = "100%";
  tLt.placeholder = "自动";
  tLt.value = obj.line_total != null ? String(obj.line_total) : "";
  const rm = document.createElement("button");
  rm.type = "button";
  rm.className = "btn sm";
  rm.textContent = "删";
  rm.addEventListener("click", () => {
    tr.remove();
    const body = document.getElementById("so_m_lines");
    if (body.querySelectorAll(".so-m-line").length === 0) addManualLineRow(body);
  });
  tr.appendChild(mkCell(tProd));
  tr.appendChild(mkCell(tTitle));
  tr.appendChild(mkCell(tCode));
  tr.appendChild(mkCell(tQty));
  tr.appendChild(mkCell(tPrice));
  tr.appendChild(mkCell(tLt));
  const tdAct = document.createElement("td");
  tdAct.appendChild(tMid);
  tdAct.appendChild(rm);
  tr.appendChild(tdAct);
  tb.appendChild(tr);
}

function openManualModalCreate() {
  document.getElementById("so_manual_title").textContent = "新建手工订单";
  document.getElementById("so_manual_order_id").value = "";
  document.getElementById("so_m_buyer").value = "";
  document.getElementById("so_m_cust_ref").value = "";
  document.getElementById("so_m_recv_name").value = "";
  document.getElementById("so_m_recv_mobile").value = "";
  document.getElementById("so_m_recv_addr").value = "";
  document.getElementById("so_m_remark").value = "";
  document.getElementById("so_m_post_fee").value = "0";
  document.getElementById("so_m_confirm_now").checked = false;
  document.getElementById("so_m_confirm_wrap").classList.remove("hidden");
  const tb = document.getElementById("so_m_lines");
  tb.innerHTML = "";
  addManualLineRow(tb);
  addManualLineRow(tb);
  document.getElementById("so-manual-modal").classList.remove("hidden");
}

function collectManualLines() {
  const lines = [];
  for (const tr of document.querySelectorAll("#so_m_lines tr.so-m-line")) {
    const pidStr = tr.querySelector(".so-m-product")?.value?.trim() || "";
    const title = tr.querySelector(".so-m-title")?.value?.trim() || "";
    const material_code = tr.querySelector(".so-m-code")?.value?.trim() || "";
    const midStr = tr.querySelector(".so-m-mid")?.value?.trim() || "";
    const qty = parseDec(tr.querySelector(".so-m-qty")?.value);
    const priceRaw = tr.querySelector(".so-m-price")?.value?.trim();
    const price = priceRaw === "" || priceRaw == null ? NaN : parseDec(priceRaw);
    const ltRaw = tr.querySelector(".so-m-lt")?.value?.trim();
    if (!pidStr && !title && !material_code && !midStr && !Number.isFinite(qty) && !Number.isFinite(price)) continue;
    if (!Number.isFinite(qty)) throw new Error("每行需填写有效数量");
    const ltExtra =
      ltRaw !== ""
        ? (() => {
            const lt = parseDec(ltRaw);
            return Number.isFinite(lt) ? lt : null;
          })()
        : null;
    if (pidStr) {
      const pid = parseInt(pidStr, 10);
      if (!Number.isFinite(pid)) throw new Error("产品选择无效");
      const row = { product_id: pid, qty };
      if (title) row.title = title;
      if (Number.isFinite(price)) row.price = price;
      if (ltExtra != null) row.line_total = ltExtra;
      lines.push(row);
      continue;
    }
    if (!Number.isFinite(price)) throw new Error("未选产品时该行须填写单价");
    const row = { title, qty, price };
    if (midStr) {
      const mid = parseInt(midStr, 10);
      if (!Number.isFinite(mid)) throw new Error("物料 ID 无效");
      row.material_id = mid;
    } else if (material_code) row.material_code = material_code;
    if (ltExtra != null) row.line_total = ltExtra;
    lines.push(row);
  }
  return lines;
}

async function openManualModalEdit(orderId) {
  try {
    await ensureProducts();
  } catch (e) {
    return showMsg(e.message || String(e), true);
  }
  const res = await fetch(`/sales/orders/${orderId}`);
  if (!res.ok) return showMsg("加载订单失败", true);
  const r = await res.json();
  if (r.channel !== "manual") return showMsg("仅可编辑手工单", true);
  document.getElementById("so_manual_title").textContent = `编辑手工单 ${r.internal_order_no}`;
  document.getElementById("so_manual_order_id").value = String(orderId);
  document.getElementById("so_m_buyer").value = r.buyer_nick || "";
  document.getElementById("so_m_cust_ref").value = r.platform_order_no || "";
  document.getElementById("so_m_recv_name").value = r.receiver_name || "";
  document.getElementById("so_m_recv_mobile").value = r.receiver_mobile || "";
  document.getElementById("so_m_recv_addr").value = r.receiver_address || "";
  document.getElementById("so_m_remark").value = r.header_remark || "";
  document.getElementById("so_m_post_fee").value = fmtMoney(r.post_fee);
  document.getElementById("so_m_confirm_wrap").classList.add("hidden");
  const tb = document.getElementById("so_m_lines");
  tb.innerHTML = "";
  (r.lines || []).forEach((ln) => {
    addManualLineRow(tb, {
      product_id: ln.product_id,
      title: ln.title,
      outer_iid: ln.outer_iid || "",
      qty: ln.qty,
      price: ln.price,
      line_total: ln.line_total,
      material_id: ln.material_id,
    });
  });
  if (!tb.querySelector(".so-m-line")) addManualLineRow(tb);
  document.getElementById("so-manual-modal").classList.remove("hidden");
}

function openInvoiceModal(r) {
  document.getElementById("so_inv_order_id").value = String(r.id);
  document.getElementById("so_inv_status").value = r.invoice_status || "none";
  document.getElementById("so_inv_no").value = r.invoice_no || "";
  const at = r.invoiced_at;
  let local = "";
  if (at) {
    const s = String(at).replace("Z", "").replace("T", " ").slice(0, 19);
    local = s.replace(" ", "T").slice(0, 16);
  }
  document.getElementById("so_inv_at").value = local;
  document.getElementById("so-invoice-modal").classList.remove("hidden");
}

async function loadList() {
  const res = await fetch("/sales/orders");
  if (!res.ok) return showMsg("加载销售订单失败", true);
  const rows = await res.json();
  const tb = document.getElementById("so-tbody");
  tb.innerHTML = rows
    .map((r) => {
      const platRef = platformRefCol(r);
      const shipInfo = r.taobao_out_sid
        ? `${r.taobao_logistics_code || ""} ${r.taobao_out_sid}`.trim()
        : r.taobao_consign_error
          ? String(r.taobao_consign_error).slice(0, 60) +
            (String(r.taobao_consign_error).length > 60 ? "…" : "")
          : "—";
      const inv = invoiceStatusText(r.invoice_status || "none");
      const btns = [];
      if (canTaobaoShip(r)) {
        btns.push(
          `<button type="button" class="btn sm" data-ship="1" data-channel="taobao" data-id="${r.id}" data-hint="交易号 ${r.platform_tid}">淘宝发货</button>`
        );
      }
      if (canWooShip(r)) {
        btns.push(
          `<button type="button" class="btn sm" data-ship="1" data-channel="woocommerce" data-id="${r.id}" data-hint="订单 #${platRef}">Woo 发货</button>`
        );
      }
      if (canManualShip(r)) {
        btns.push(
          `<button type="button" class="btn sm" data-ship="1" data-channel="manual" data-id="${r.id}" data-hint="内部 ${r.internal_order_no}">本地发货</button>`
        );
      }
      if (canManualConfirm(r)) {
        btns.push(`<button type="button" class="btn sm" data-confirm-manual="${r.id}">确认</button>`);
      }
      if (canManualEdit(r)) {
        btns.push(`<button type="button" class="btn sm" data-edit-manual="${r.id}">编辑</button>`);
      }
      btns.push(`<button type="button" class="btn sm" data-inv-id="${r.id}">发票</button>`);
      return `<tr>
    <td>${r.internal_order_no}</td>
    <td>${channelText(r.channel)}</td>
    <td>${platRef}</td>
    <td>${r.buyer_nick || "—"}</td>
    <td>${r.platform_status || "—"}</td>
    <td>${localStatusText(r.local_status)}</td>
    <td>${inv}</td>
    <td>${fmtMoney(r.total_amount)}</td>
    <td>${r.pay_time ? String(r.pay_time).slice(0, 19).replace("T", " ") : "—"}</td>
    <td style="max-width:180px;word-break:break-all;font-size:12px;">${shipInfo}</td>
    <td style="white-space:normal;max-width:220px;">${btns.join(" ")}</td>
  </tr>`;
    })
    .join("");
  const tot = document.getElementById("so-total");
  if (tot) tot.textContent = `共 ${rows.length} 条`;
}

document.getElementById("so_new_manual").addEventListener("click", async () => {
  try {
    await ensureProducts();
  } catch (e) {
    return showMsg(e.message || String(e), true);
  }
  openManualModalCreate();
});

document.getElementById("so_m_add_line").addEventListener("click", async () => {
  try {
    await ensureProducts();
  } catch (e) {
    return showMsg(e.message || String(e), true);
  }
  addManualLineRow(document.getElementById("so_m_lines"));
});

document.getElementById("so_manual_cancel").addEventListener("click", () => {
  document.getElementById("so-manual-modal").classList.add("hidden");
});

document.getElementById("so_manual_save").addEventListener("click", async () => {
  let lines;
  try {
    lines = collectManualLines();
  } catch (e) {
    return showMsg(e.message || String(e), true);
  }
  if (!lines.length) return showMsg("请至少填写一行有效明细", true);
  const oid = document.getElementById("so_manual_order_id").value.trim();
  const post_fee = parseDec(document.getElementById("so_m_post_fee").value);
  if (!Number.isFinite(post_fee) || post_fee < 0) return showMsg("运费无效", true);
  const base = {
    buyer_nick: document.getElementById("so_m_buyer").value.trim() || null,
    receiver_name: document.getElementById("so_m_recv_name").value.trim() || null,
    receiver_mobile: document.getElementById("so_m_recv_mobile").value.trim() || null,
    receiver_address: document.getElementById("so_m_recv_addr").value.trim() || null,
    header_remark: document.getElementById("so_m_remark").value.trim() || null,
    customer_ref: document.getElementById("so_m_cust_ref").value.trim() || null,
    post_fee,
    lines,
  };
  try {
    if (oid) {
      const res = await fetch(`/sales/orders/${oid}/manual`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(base),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        return showMsg(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail) || "保存失败", true);
      }
      showMsg("已保存修改");
    } else {
      base.confirm_immediately = document.getElementById("so_m_confirm_now").checked;
      const res = await fetch("/sales/orders/manual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(base),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        const d = e.detail;
        if (Array.isArray(d)) {
          return showMsg(d.map((x) => x.msg || JSON.stringify(x)).join("; ") || "创建失败", true);
        }
        return showMsg(typeof d === "string" ? d : JSON.stringify(d) || "创建失败", true);
      }
      showMsg("已创建手工订单");
    }
    document.getElementById("so-manual-modal").classList.add("hidden");
    loadList();
  } catch (e) {
    showMsg(String(e), true);
  }
});

document.getElementById("so_inv_cancel").addEventListener("click", () => {
  document.getElementById("so-invoice-modal").classList.add("hidden");
});

document.getElementById("so_inv_save").addEventListener("click", async () => {
  const id = document.getElementById("so_inv_order_id").value;
  const invoice_status = document.getElementById("so_inv_status").value;
  const invoice_no = document.getElementById("so_inv_no").value.trim() || null;
  const at = document.getElementById("so_inv_at").value;
  const body = { invoice_status };
  if (invoice_no) body.invoice_no = invoice_no;
  if (at) body.invoiced_at = new Date(at).toISOString();
  const res = await fetch(`/sales/orders/${id}/invoice`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail) || "保存失败", true);
  }
  showMsg("发票信息已更新");
  document.getElementById("so-invoice-modal").classList.add("hidden");
  loadList();
});

document.getElementById("so_sync").addEventListener("click", async () => {
  showMsg("正在同步淘宝…");
  const res = await fetch("/sales/orders/sync-taobao?hours_back=168", { method: "POST" });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail) || "同步失败", true);
  }
  const data = await res.json();
  showMsg(`淘宝：处理 ${data.synced_count} 笔。${data.message || ""}`);
  loadList();
});

document.getElementById("so_sync_wc").addEventListener("click", async () => {
  showMsg("正在同步 WooCommerce…");
  const res = await fetch("/sales/orders/sync-woocommerce?hours_back=720", { method: "POST" });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail) || "同步失败", true);
  }
  const data = await res.json();
  showMsg(`WooCommerce：处理 ${data.synced_count} 条。${data.message || ""}`);
  loadList();
});

document.getElementById("so-tbody").addEventListener("click", (e) => {
  const b = e.target.closest("[data-ship]");
  if (b) {
    openShipModal(
      b.getAttribute("data-id"),
      b.getAttribute("data-channel"),
      b.getAttribute("data-hint") || ""
    );
    return;
  }
  const c = e.target.closest("[data-confirm-manual]");
  if (c) {
    const id = c.getAttribute("data-confirm-manual");
    (async () => {
      const res = await fetch(`/sales/orders/${id}/manual/confirm`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        return showMsg(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail) || "操作失败", true);
      }
      showMsg("已确认，进入待发货");
      loadList();
    })();
    return;
  }
  const ed = e.target.closest("[data-edit-manual]");
  if (ed) {
    openManualModalEdit(ed.getAttribute("data-edit-manual"));
    return;
  }
  const inv = e.target.closest("[data-inv-id]");
  if (inv) {
    const oid = inv.getAttribute("data-inv-id");
    (async () => {
      const res = await fetch(`/sales/orders/${oid}`);
      if (!res.ok) return showMsg("加载订单失败", true);
      openInvoiceModal(await res.json());
    })();
  }
});

document.getElementById("so_ship_cancel").addEventListener("click", () => {
  document.getElementById("so-ship-modal").classList.add("hidden");
});

document.getElementById("so_ship_save").addEventListener("click", async () => {
  const id = document.getElementById("so_ship_order_id").value;
  const channel = document.getElementById("so_ship_channel").value;
  if (channel === "manual") {
    const tracking_number = document.getElementById("so_manual_tracking").value.trim();
    const carrier_name = document.getElementById("so_manual_carrier").value.trim() || null;
    if (!tracking_number) return showMsg("请填写运单号", true);
    const res = await fetch(`/sales/orders/${id}/manual/ship`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tracking_number, carrier_name }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return showMsg(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail) || "失败", true);
    }
    showMsg("已登记本地发货");
  } else if (channel === "woocommerce") {
    const tracking_number = document.getElementById("so_wc_tracking").value.trim();
    const carrier_name = document.getElementById("so_wc_carrier").value.trim() || null;
    const set_status_completed = document.getElementById("so_wc_completed").checked;
    if (!tracking_number) return showMsg("请填写运单号", true);
    const res = await fetch(`/sales/orders/${id}/woocommerce-ship`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tracking_number, carrier_name, set_status_completed }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return showMsg(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail) || "回写失败", true);
    }
    showMsg("已更新 WooCommerce 订单");
  } else {
    const company_code = document.getElementById("so_company_code").value.trim();
    const out_sid = document.getElementById("so_out_sid").value.trim();
    if (!company_code || !out_sid) return showMsg("请填写物流公司编码与运单号", true);
    const res = await fetch(`/sales/orders/${id}/taobao-ship`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_code, out_sid }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return showMsg(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail) || "回写失败", true);
    }
    showMsg("已回写淘宝发货");
  }
  document.getElementById("so-ship-modal").classList.add("hidden");
  loadList();
});

loadList();
