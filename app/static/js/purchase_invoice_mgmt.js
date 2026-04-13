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

/** 列表「开票状态」列：未开票 / 已开票张数，可选票面合计与订单对比 */
function invoiceStatusCell(r) {
  const invs = r.invoices || [];
  if (!invs.length) {
    return '<span class="pi-inv-badge pi-inv-none">未开票</span>';
  }
  const withAmt = invs.filter((x) => x.amount_with_tax != null);
  const sumAmt = withAmt.reduce((acc, x) => acc + Number(x.amount_with_tax), 0);
  const orderAmt = Number(r.total_with_tax || 0);
  let sub = "";
  if (withAmt.length && orderAmt > 0) {
    const diff = Math.abs(sumAmt - orderAmt);
    if (diff < 0.02) {
      sub = '<br><span class="muted-hint" style="font-weight:400">票面合计与订单含税合计一致</span>';
    } else {
      sub = `<br><span class="muted-hint" style="font-weight:400">票面合计 ${fmt2(sumAmt)} · 订单 ${fmt2(orderAmt)}</span>`;
    }
  } else if (withAmt.length) {
    sub = `<br><span class="muted-hint" style="font-weight:400">票面合计 ${fmt2(sumAmt)}</span>`;
  }
  return `<span class="pi-inv-badge pi-inv-yes">已开票 · ${invs.length} 张</span>${sub}`;
}

let currentPoId = null;

function isoDateOnly(s) {
  return s ? String(s).slice(0, 10) : "";
}

function clearUploadForm() {
  document.getElementById("pi_inv_no").value = "";
  document.getElementById("pi_inv_amt").value = "";
  document.getElementById("pi_inv_remark").value = "";
  document.getElementById("pi_inv_file").value = "";
}

function renderModalInvoices(po) {
  currentPoId = po.id;
  const ul = document.getElementById("pi_modal_list");
  const invs = po.invoices || [];
  if (!invs.length) {
    ul.innerHTML = "<li class=\"muted-hint\">暂无发票记录，可在下方「新增发票」登记。</li>";
    return;
  }
  ul.innerHTML = invs
    .map(
      (inv) => `<li class="po-invoice-li">
    <span class="po-invoice-no">${String(inv.invoice_no || "").replace(/</g, "")}</span>
    ${inv.amount_with_tax != null ? `<span class="muted-hint">含税 ${fmt2(inv.amount_with_tax)}</span>` : ""}
    ${inv.remark ? `<span class="muted-hint">${String(inv.remark).replace(/</g, "").slice(0, 48)}${inv.remark.length > 48 ? "…" : ""}</span>` : ""}
    <a class="btn sm" href="/purchase-orders/${po.id}/invoices/${inv.id}/file" target="_blank" rel="noopener noreferrer">下载</a>
    <button type="button" class="btn sm pi-inv-del" data-inv="${inv.id}">删除</button>
  </li>`
    )
    .join("");
}

function openPiModal(po, focusAdd) {
  currentPoId = po.id;
  document.getElementById("pi_modal_title").textContent = `进项发票 — ${po.order_no}`;
  document.getElementById("pi_modal_meta").textContent = `${po.supplier_company || ""} · 订单含税合计 ${fmt2(po.total_with_tax)} · 日期 ${isoDateOnly(po.order_date)}`;
  renderModalInvoices(po);
  clearUploadForm();
  document.getElementById("pi_modal").classList.remove("hidden");
  if (focusAdd) {
    requestAnimationFrame(() => {
      document.getElementById("pi_section_add")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      document.getElementById("pi_inv_no")?.focus();
    });
  }
}

function closePiModal() {
  document.getElementById("pi_modal").classList.add("hidden");
  currentPoId = null;
}

async function loadOrderTable() {
  const res = await fetch("/purchase-orders");
  if (!res.ok) return showMsg("加载订单列表失败", true);
  const rows = await res.json();
  const sorted = [...rows].sort((a, b) => b.id - a.id);
  const tb = document.getElementById("pi_order_tbody");
  tb.innerHTML = sorted
    .map(
      (r) => `<tr data-po-id="${r.id}">
    <td>${escAttr(r.order_no)}</td>
    <td>${isoDateOnly(r.order_date)}</td>
    <td>${escAttr(r.supplier_company || "")}</td>
    <td>${statusBadgeHtml(r.status)}</td>
    <td>${fmt2(r.total_with_tax)}</td>
    <td>${invoiceStatusCell(r)}</td>
    <td>
      <button type="button" class="btn sm" data-pi-view="${r.id}">查看发票记录</button>
      <button type="button" class="btn sm primary" data-pi-add="${r.id}">新增发票</button>
    </td>
  </tr>`
    )
    .join("");
  document.getElementById("pi_total").textContent = `共 ${sorted.length} 条`;
}

document.getElementById("pi_order_tbody").addEventListener("click", async (e) => {
  const viewBtn = e.target.closest("[data-pi-view]");
  const addBtn = e.target.closest("[data-pi-add]");
  const id = viewBtn?.getAttribute("data-pi-view") || addBtn?.getAttribute("data-pi-add");
  if (!id) return;
  const res = await fetch(`/purchase-orders/${id}`);
  if (!res.ok) return showMsg("加载订单失败", true);
  const po = await res.json();
  openPiModal(po, Boolean(addBtn));
  showMsg(addBtn ? "请填写发票信息并上传文件" : "可查看、下载或删除已有记录，或在下方新增");
});

document.getElementById("pi_upload").addEventListener("click", async () => {
  const id = currentPoId;
  if (!id) return showMsg("请先打开某个订单的发票窗口", true);
  const no = document.getElementById("pi_inv_no").value.trim();
  if (!no) return showMsg("请填写发票号码", true);
  const fileEl = document.getElementById("pi_inv_file");
  if (!fileEl.files || !fileEl.files.length) return showMsg("请选择发票电子文件", true);
  const fd = new FormData();
  fd.append("invoice_no", no);
  const amt = document.getElementById("pi_inv_amt").value.trim();
  if (amt) fd.append("amount_with_tax", amt);
  const rm = document.getElementById("pi_inv_remark").value.trim();
  if (rm) fd.append("remark", rm);
  fd.append("file", fileEl.files[0]);
  const res = await fetch(`/purchase-orders/${id}/invoices`, { method: "POST", body: fd });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    return showMsg(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail) || "上传失败", true);
  }
  showMsg("发票已保存");
  clearUploadForm();
  const r2 = await fetch(`/purchase-orders/${id}`);
  if (r2.ok) {
    const po = await r2.json();
    renderModalInvoices(po);
    await loadOrderTable();
  }
});

document.getElementById("pi_modal_list").addEventListener("click", async (e) => {
  const btn = e.target.closest(".pi-inv-del");
  if (!btn) return;
  const invId = btn.getAttribute("data-inv");
  const pid = currentPoId;
  if (!invId || !pid) return;
  if (!confirm("确定删除该发票记录及文件？")) return;
  const res = await fetch(`/purchase-orders/${pid}/invoices/${invId}`, { method: "DELETE" });
  if (!res.ok) return showMsg("删除失败", true);
  showMsg("已删除");
  const r2 = await fetch(`/purchase-orders/${pid}`);
  if (r2.ok) {
    renderModalInvoices(await r2.json());
    await loadOrderTable();
  }
});

document.getElementById("pi_close").addEventListener("click", closePiModal);

loadOrderTable();
