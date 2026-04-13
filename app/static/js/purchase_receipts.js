const msgEl = document.getElementById("msg");
const showMsg = (m, err = false) => {
  msgEl.textContent = m;
  msgEl.className = err ? "msg err" : "msg ok";
};

const fmt2 = (n) => {
  const x = Number(n);
  if (!Number.isFinite(x)) return "0.00";
  return x.toFixed(2);
};

const fmt3 = (n) => {
  const x = Number(n);
  if (!Number.isFinite(x)) return "0.000";
  return x.toFixed(3);
};

const OPEN_EPS = 1e-9;

const PO_STATUS_META = {
  draft: { text: "草稿", cls: "po-st-draft" },
  sent: { text: "已发送", cls: "po-st-sent" },
  confirmed: { text: "已确认", cls: "po-st-confirmed" },
  partial_received: { text: "部分入库", cls: "po-st-partial_received" },
  received: { text: "已全部入库", cls: "po-st-received" },
  closed: { text: "已关闭", cls: "po-st-closed" },
};

function escAttr(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

function statusBadgeHtml(status) {
  const m = PO_STATUS_META[status] || { text: status || "—", cls: "po-st-unknown" };
  const t = String(m.text).replace(/</g, "");
  return `<span class="po-status-tag ${m.cls}">${t}</span>`;
}

/** 单行待入库数量（与后端 qty_open 一致） */
function lineQtyOpen(l) {
  return Number(l.qty_open != null ? l.qty_open : Math.max(0, Number(l.qty) - Number(l.received_qty ?? 0)));
}

function poHasOpenQty(r) {
  return (r.lines || []).some((l) => lineQtyOpen(l) > OPEN_EPS);
}

/** 仅草稿/关闭不可操作；是否出现「加载明细」完全看是否还有待入数量（避免状态显示已全部入库仍可点） */
function poEligibleForReceipt(r) {
  if (r.status === "draft" || r.status === "closed") return false;
  return poHasOpenQty(r);
}

let allOrders = [];
let currentDetail = null;
let currentLoadedId = null;

function isoDateOnly(s) {
  return s ? String(s).slice(0, 10) : "";
}

function receiptSummary(r) {
  const lines = r.lines || [];
  let openSum = 0;
  let openLines = 0;
  for (const l of lines) {
    const o = lineQtyOpen(l);
    if (o > OPEN_EPS) {
      openSum += o;
      openLines += 1;
    }
  }
  if (openLines === 0) return '<span class="muted-hint">无待入</span>';
  return `${openLines} 行 · 待入合计 ${fmt3(openSum)}`;
}

function opCellHtml(r) {
  if (r.status === "draft") {
    return '<span class="muted-hint" title="请先在采购订单页下达">须先下达</span>';
  }
  if (r.status === "closed") {
    return '<span class="muted-hint">已关闭</span>';
  }
  if (!poEligibleForReceipt(r)) {
    return '<span class="muted-hint">已收齐</span>';
  }
  return `<button type="button" class="btn sm pr-load-detail" data-id="${r.id}">加载明细</button>`;
}

function highlightLoadedRow(id) {
  currentLoadedId = id;
  document.querySelectorAll("#pr_order_tbody tr").forEach((tr) => {
    tr.classList.toggle("pr-row-active", tr.getAttribute("data-po-id") === String(id));
  });
}

function clearRowHighlight() {
  currentLoadedId = null;
  document.querySelectorAll("#pr_order_tbody tr").forEach((tr) => tr.classList.remove("pr-row-active"));
}

function openReceiptModal() {
  document.getElementById("pr_modal").classList.remove("hidden");
}

function closeReceiptModal() {
  document.getElementById("pr_modal").classList.add("hidden");
  currentDetail = null;
  clearRowHighlight();
}

async function loadOrderTable() {
  const res = await fetch("/purchase-orders");
  if (!res.ok) return showMsg("加载订单列表失败", true);
  allOrders = await res.json();
  const sorted = [...allOrders].sort((a, b) => b.id - a.id);
  const tb = document.getElementById("pr_order_tbody");
  tb.innerHTML = sorted
    .map(
      (r) => `<tr data-po-id="${r.id}">
    <td>${escAttr(r.order_no)}</td>
    <td>${isoDateOnly(r.order_date)}</td>
    <td>${escAttr(r.supplier_company || "")}</td>
    <td>${statusBadgeHtml(r.status)}</td>
    <td>${fmt2(r.total_with_tax)}</td>
    <td>${receiptSummary(r)}</td>
    <td>${opCellHtml(r)}</td>
  </tr>`
    )
    .join("");
  document.getElementById("pr_total").textContent = `共 ${sorted.length} 条`;
  if (currentLoadedId) highlightLoadedRow(currentLoadedId);
}

function renderDetail(po) {
  currentDetail = po;
  document.getElementById("pr_title").textContent = `入库 — ${po.order_no} · ${po.supplier_company || ""}`;
  const st = PO_STATUS_META[po.status]?.text || po.status;
  document.getElementById("pr_meta").textContent = `单据状态：${st} · 日期 ${isoDateOnly(po.order_date)} · 待入库行已标出，请填写本次实收数量`;

  const linesTb = document.getElementById("pr_tbody");
  const lines = [...(po.lines || [])].sort((a, b) => a.line_no - b.line_no);
  linesTb.innerHTML = lines
    .map((ln) => {
      const open = lineQtyOpen(ln);
      return `<tr data-line-id="${ln.id}">
      <td>${ln.line_no}</td>
      <td>${String(ln.material_code || "").replace(/</g, "")}</td>
      <td>${String(ln.material_name || "").replace(/</g, "")}</td>
      <td>${String(ln.unit || "").replace(/</g, "")}</td>
      <td>${fmt3(ln.qty)}</td>
      <td>${fmt3(ln.received_qty ?? 0)}</td>
      <td>${fmt3(open)}</td>
      <td><input type="number" class="pr-recv" min="0" step="0.0001" value="0" style="width:100px" ${open <= OPEN_EPS ? "disabled" : ""}></td>
    </tr>`;
    })
    .join("");

  highlightLoadedRow(po.id);
  openReceiptModal();
}

document.getElementById("pr_order_tbody").addEventListener("click", async (e) => {
  const btn = e.target.closest(".pr-load-detail");
  if (!btn) return;
  const id = btn.getAttribute("data-id");
  if (!id) return;
  const res = await fetch(`/purchase-orders/${id}`);
  if (!res.ok) return showMsg("加载订单失败", true);
  const po = await res.json();
  if (po.status === "draft") return showMsg("草稿订单不能入库，请先在采购订单页改为「已发送供方」等", true);
  if (po.status === "closed") return showMsg("订单已关闭，不能入库", true);
  if (!poHasOpenQty(po)) return showMsg("该订单没有待入库数量，无法继续入库", true);
  renderDetail(po);
  showMsg("请在弹窗中填写本次入库数量");
});

document.getElementById("pr_submit").addEventListener("click", async () => {
  if (!currentDetail) return showMsg("请先在列表中点击「加载明细」", true);
  const id = currentDetail.id;
  const lines = [];
  document.querySelectorAll("#pr_tbody tr").forEach((tr) => {
    const lid = tr.getAttribute("data-line-id");
    const inp = tr.querySelector(".pr-recv");
    if (!lid || !inp || inp.disabled) return;
    const q = Number(inp.value || 0);
    if (q > 0) lines.push({ line_id: Number(lid), qty: q });
  });
  if (!lines.length) return showMsg("请至少在一行填写大于 0 的本次入库数量", true);
  const res = await fetch(`/purchase-orders/${id}/receive`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lines }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    return showMsg(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail) || "入库失败", true);
  }
  const po = await res.json();
  if (poHasOpenQty(po)) {
    await loadOrderTable();
    showMsg("入库已记账；本单仍有待入，可继续在本窗口操作");
    renderDetail(po);
  } else {
    closeReceiptModal();
    await loadOrderTable();
    showMsg("入库已记账，本单已全部收齐");
  }
});

document.getElementById("pr_close").addEventListener("click", closeReceiptModal);

loadOrderTable();
