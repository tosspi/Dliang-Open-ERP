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

const PO_STATUS_FORM_OPTIONS = [
  { value: "draft", label: "草稿（内部编制中）" },
  { value: "sent", label: "已发送供方（已下达）" },
  { value: "confirmed", label: "供方已确认" },
  { value: "partial_received", label: "部分入库" },
  { value: "received", label: "已全部入库" },
  { value: "closed", label: "已关闭" },
];

const PAYMENT_META = {
  unpaid: { text: "待付款", cls: "po-pay-unpaid" },
  partial: { text: "部分付款", cls: "po-pay-partial" },
  paid: { text: "已付款", cls: "po-pay-paid" },
};

function escAttr(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

function statusBadgeHtml(status) {
  const m = PO_STATUS_META[status] || { text: status || "—", cls: "po-st-unknown" };
  const t = String(m.text).replace(/</g, "");
  return `<span class="po-status-tag ${m.cls}">${t}</span>`;
}

function paymentBadgeHtml(paymentStatus) {
  const m = PAYMENT_META[paymentStatus] || { text: paymentStatus || "—", cls: "po-pay-unknown" };
  const t = String(m.text).replace(/</g, "");
  return `<span class="po-status-tag ${m.cls}">${t}</span>`;
}

/** 付款截止日、剩余天数两列（未维护供应商账期则无截止日） */
function paymentDueDateTds(r) {
  if (!r.payment_due_date) {
    return { d: "<td>—</td>", rem: "<td>—</td>" };
  }
  const d = String(r.payment_due_date).slice(0, 10);
  if (r.payment_status === "paid") {
    return {
      d: `<td>${escAttr(d)}</td>`,
      rem: `<td><span class="po-due-muted">已付款</span></td>`,
    };
  }
  const rem = Number(r.payment_due_days_remaining);
  if (!Number.isFinite(rem)) {
    return { d: `<td>${escAttr(d)}</td>`, rem: "<td>—</td>" };
  }
  if (rem < 0) {
    const overdue = Math.abs(rem);
    return {
      d: `<td class="po-due-overdue"><span class="po-due-pill">超期</span> ${escAttr(d)}</td>`,
      rem: `<td class="po-due-overdue"><strong>已超期 ${overdue} 天</strong></td>`,
    };
  }
  if (rem === 0) {
    return {
      d: `<td class="po-due-today"><span class="po-due-pill po-due-pill-today">今日到期</span> ${escAttr(d)}</td>`,
      rem: `<td class="po-due-today"><strong>今日到期</strong></td>`,
    };
  }
  if (rem <= 3) {
    return {
      d: `<td class="po-due-soon">${escAttr(d)}</td>`,
      rem: `<td class="po-due-soon">剩余 <strong>${rem}</strong> 天</td>`,
    };
  }
  return {
    d: `<td>${escAttr(d)}</td>`,
    rem: `<td>剩余 ${rem} 天</td>`,
  };
}

function fillStatusModalSelect(selected) {
  const sel = document.getElementById("po_status_modal_sel");
  sel.innerHTML = PO_STATUS_FORM_OPTIONS.map(
    (o) => `<option value="${o.value}" ${o.value === selected ? "selected" : ""}>${o.label}</option>`
  ).join("");
}

function openQuickStatusModal(id, orderNo, currentStatus, currentPayment) {
  document.getElementById("po_status_modal_id").value = String(id);
  document.getElementById("po_status_modal_hint").textContent = `订单号：${orderNo || "—"}`;
  fillStatusModalSelect(currentStatus || "draft");
  const paySel = document.getElementById("po_payment_modal_sel");
  const ps = currentPayment || "unpaid";
  if (paySel) paySel.value = PAYMENT_META[ps] ? ps : "unpaid";
  document.getElementById("po-status-modal").classList.remove("hidden");
}

function closeQuickStatusModal() {
  document.getElementById("po-status-modal").classList.add("hidden");
}

let allSuppliers = [];

function todayISODate() {
  const d = new Date();
  const z = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
}

function isoDateOnly(s) {
  if (!s) return todayISODate();
  return String(s).slice(0, 10);
}

function renderSupplierOptions(selected = "") {
  const sel = document.getElementById("po_supplier_company");
  if (!sel) return;
  const opts = allSuppliers
    .filter((s) => s.is_active !== false)
    .map((s) => `<option value="${String(s.company_name || "").replace(/"/g, "&quot;")}">${String(s.company_name || "")}</option>`)
    .join("");
  sel.innerHTML = `<option value="">请选择供应商</option>${opts}`;
  if (selected) {
    if (![...sel.options].some((o) => o.value === selected)) {
      const op = document.createElement("option");
      op.value = selected;
      op.textContent = `${selected}（历史）`;
      sel.appendChild(op);
    }
    sel.value = selected;
  }
}

function fillSupplierFieldsByCompany(companyName) {
  const s = allSuppliers.find((x) => (x.company_name || "") === (companyName || ""));
  if (!s) return;
  document.getElementById("po_supplier_tax_no").value = s.credit_code || "";
  document.getElementById("po_supplier_bank").value = s.bank_name || "";
  document.getElementById("po_supplier_account").value = s.bank_account || "";
  document.getElementById("po_supplier_address").value = s.address || "";
  document.getElementById("po_supplier_phone").value = s.phone || "";
  document.getElementById("po_supplier_contact").value = s.contact_person || "";
}

async function loadSuppliers() {
  const res = await fetch("/suppliers");
  if (!res.ok) return;
  allSuppliers = await res.json();
  renderSupplierOptions();
}

function currentSupplierMaterials() {
  const company = document.getElementById("po_supplier_company").value || "";
  const sp = allSuppliers.find((s) => (s.company_name || "") === company);
  return sp?.managed_materials || [];
}

function materialByCode(code) {
  const v = (code || "").trim();
  if (!v) return null;
  return currentSupplierMaterials().find((m) => (m.code || "") === v) || null;
}

function lineRowHtml(idx, r = {}) {
  const lid = r.id != null && r.id !== "" ? r.id : "";
  const mid = r.material_id != null && r.material_id !== "" ? r.material_id : "";
  const listId = `po-code-list-${idx}`;
  return `<tr data-idx="${idx}" data-material-id="${mid}">
    <td>
      <input type="hidden" class="po-line-id" value="${lid}">
      <input type="number" class="po-ln" value="${r.line_no ?? idx + 1}" min="1" style="width:52px">
    </td>
    <td>
      <input class="po-code" list="${listId}" placeholder="料号（可搜索）">
      <datalist id="${listId}"></datalist>
    </td>
    <td><input class="po-name" placeholder="名称"></td>
    <td><input class="po-spec" placeholder="规格/图号"></td>
    <td><input class="po-unit" placeholder="单位" style="width:56px"></td>
    <td><input type="number" class="po-qty" value="${r.qty ?? 1}" min="0" step="0.0001" style="width:88px"></td>
    <td><input type="number" class="po-price" value="0" min="0" step="0.0001" style="width:96px"></td>
    <td class="po-amt">${fmt2(0)}</td>
    <td><input class="po-taxnote" placeholder="如13%" style="width:64px"></td>
    <td><input class="po-lremark"></td>
    <td><button type="button" class="btn sm po-del-line">删</button></td>
  </tr>`;
}

function applyMaterialToRow(tr, mat, force = false) {
  if (!tr || !mat) return;
  tr.dataset.materialId = String(mat.id);
  const nameEl = tr.querySelector(".po-name");
  const specEl = tr.querySelector(".po-spec");
  const unitEl = tr.querySelector(".po-unit");
  const priceEl = tr.querySelector(".po-price");
  const taxEl = tr.querySelector(".po-taxnote");
  const remarkEl = tr.querySelector(".po-lremark");

  if (force || !nameEl.value) nameEl.value = mat.name || "";
  if (force || !specEl.value) specEl.value = mat.spec_drawing || "";
  if (force || !unitEl.value) unitEl.value = mat.unit || "";
  if (force || !priceEl.value || Number(priceEl.value) === 0) priceEl.value = Number(mat.unit_price || 0);
  if (force || !taxEl.value) taxEl.value = mat.tax_rate || "";
  if (force || !remarkEl.value) remarkEl.value = mat.remark || "";
  recalcPoLines();
}

function refreshLineMaterialLists() {
  const mats = currentSupplierMaterials();
  const tbody = document.getElementById("po_lines_tbody");
  tbody.querySelectorAll("tr").forEach((tr, i) => {
    const listId = `po-code-list-${i}`;
    tr.dataset.idx = String(i);
    const codeInput = tr.querySelector(".po-code");
    if (codeInput) codeInput.setAttribute("list", listId);
    let dl = tr.querySelector("datalist");
    if (!dl) {
      dl = document.createElement("datalist");
      tr.querySelector("td:nth-child(2)")?.appendChild(dl);
    }
    dl.id = listId;
    dl.innerHTML = mats.map((m) => `<option value="${String(m.code || "").replace(/"/g, "&quot;")}">${String(m.name || "").replace(/</g, "")}</option>`).join("");
    const m = materialByCode(codeInput?.value || "");
    if (m) applyMaterialToRow(tr, m);
  });
}

function recalcPoLines() {
  const tbody = document.getElementById("po_lines_tbody");
  let sum = 0;
  tbody.querySelectorAll("tr").forEach((tr) => {
    const q = Number(tr.querySelector(".po-qty")?.value || 0);
    const p = Number(tr.querySelector(".po-price")?.value || 0);
    const amt = q * p;
    sum += amt;
    const cell = tr.querySelector(".po-amt");
    if (cell) cell.textContent = fmt2(amt);
  });
  document.getElementById("po_line_total").textContent = fmt2(sum);
}

function bindLineEvents(tbody) {
  tbody.addEventListener("input", (e) => {
    if (e.target.matches(".po-qty, .po-price")) recalcPoLines();
    if (e.target.matches(".po-code")) {
      const tr = e.target.closest("tr");
      const m = materialByCode(e.target.value);
      if (m) applyMaterialToRow(tr, m, true);
      else tr.dataset.materialId = "";
    }
  });
  tbody.addEventListener("click", (e) => {
    const btn = e.target.closest(".po-del-line");
    if (!btn) return;
    const tr = btn.closest("tr");
    if (tr && tbody.querySelectorAll("tr").length > 1) tr.remove();
    refreshLineMaterialLists();
    recalcPoLines();
  });
}

function collectLines() {
  const tbody = document.getElementById("po_lines_tbody");
  const rows = [...tbody.querySelectorAll("tr")];
  return rows.map((tr, i) => {
    const lineIdRaw = tr.querySelector(".po-line-id")?.value;
    const line_no = Number(tr.querySelector(".po-ln")?.value || i + 1);
    const qty = Number(tr.querySelector(".po-qty")?.value || 0);
    const unit_price = Number(tr.querySelector(".po-price")?.value || 0);
    if (qty <= 0) throw new Error("每行数量须大于 0");
    const midRaw = tr.dataset.materialId;
    const material_id = midRaw ? Number(midRaw) : null;
    const o = {
      line_no,
      material_id: Number.isFinite(material_id) && material_id > 0 ? material_id : null,
      material_code: tr.querySelector(".po-code")?.value?.trim() || "",
      material_name: tr.querySelector(".po-name")?.value?.trim() || "",
      spec_drawing: tr.querySelector(".po-spec")?.value?.trim() || null,
      unit: tr.querySelector(".po-unit")?.value?.trim() || null,
      qty,
      unit_price,
      tax_rate_note: tr.querySelector(".po-taxnote")?.value?.trim() || null,
      remark: tr.querySelector(".po-lremark")?.value?.trim() || null,
    };
    if (lineIdRaw) o.id = Number(lineIdRaw);
    return o;
  });
}

function renderLinesFromOrder(lines) {
  const tbody = document.getElementById("po_lines_tbody");
  tbody.innerHTML = "";
  const sorted = [...lines].sort((a, b) => a.line_no - b.line_no);
  sorted.forEach((ln, i) => {
    tbody.insertAdjacentHTML("beforeend", lineRowHtml(i, ln));
    const tr = tbody.querySelector("tr:last-child");
    tr.querySelector(".po-ln").value = ln.line_no;
    tr.querySelector(".po-code").value = ln.material_code || "";
    tr.querySelector(".po-name").value = ln.material_name || "";
    tr.querySelector(".po-spec").value = ln.spec_drawing || "";
    tr.querySelector(".po-unit").value = ln.unit || "";
    tr.querySelector(".po-qty").value = ln.qty;
    tr.querySelector(".po-price").value = ln.unit_price;
    tr.querySelector(".po-taxnote").value = ln.tax_rate_note || "";
    tr.querySelector(".po-lremark").value = ln.remark || "";
    if (ln.material_id != null) tr.dataset.materialId = String(ln.material_id);
    tr.querySelector(".po-line-id").value = ln.id != null ? String(ln.id) : "";
  });
  if (!sorted.length) {
    tbody.innerHTML = lineRowHtml(0, {});
  }
  refreshLineMaterialLists();
  recalcPoLines();
}

function openModal() {
  document.getElementById("po-modal").classList.remove("hidden");
}
function closeModal() {
  document.getElementById("po-modal").classList.add("hidden");
}

async function resetFormNew() {
  document.getElementById("po_id").value = "";
  document.getElementById("po-modal-title").textContent = "新建采购订单";
  document.getElementById("po_order_no").value = "";
  document.getElementById("po_order_date").value = todayISODate();
  ["po_payment_terms", "po_delivery_terms", "po_header_remark"].forEach((id) => {
    document.getElementById(id).value = "";
  });
  let deliveryAddr = "";
  try {
    const res = await fetch("/company-profile");
    if (res.ok) {
      const p = await res.json();
      deliveryAddr = (p.address || "").trim();
    }
  } catch (_) {}
  document.getElementById("po_delivery_address").value = deliveryAddr;
  ["po_supplier_company", "po_supplier_tax_no", "po_supplier_bank", "po_supplier_account", "po_supplier_address", "po_supplier_phone", "po_supplier_contact"].forEach((id) => {
    document.getElementById(id).value = "";
  });
  renderSupplierOptions();
  const tbody = document.getElementById("po_lines_tbody");
  tbody.innerHTML = lineRowHtml(0, {});
  refreshLineMaterialLists();
  recalcPoLines();
}

async function loadList() {
  const res = await fetch("/purchase-orders");
  if (!res.ok) return showMsg("加载订单列表失败", true);
  const rows = await res.json();
  const tb = document.getElementById("po-tbody");
  tb.innerHTML = rows
    .map(
      (r) => {
        const due = paymentDueDateTds(r);
        return `<tr>
    <td>${escAttr(r.order_no)}</td>
    <td>${isoDateOnly(r.order_date)}</td>
    <td>${escAttr(r.supplier_company || "")}</td>
    <td>${statusBadgeHtml(r.status)}</td>
    <td>${paymentBadgeHtml(r.payment_status)}</td>
    ${due.d}
    ${due.rem}
    <td>${fmt2(r.total_with_tax)}</td>
    <td>
      <button type="button" class="btn sm" data-edit="${r.id}">编辑</button>
      <button type="button" class="btn sm" data-quick-status="${r.id}" data-order-no="${escAttr(r.order_no)}" data-current-status="${escAttr(r.status)}" data-current-payment="${escAttr(r.payment_status || "unpaid")}">修改状态</button>
      <a class="btn sm" href="/purchase-orders/${r.id}/pdf" target="_blank">导出PDF</a>
    </td>
  </tr>`;
      }
    )
    .join("");
  const tot = document.getElementById("po-total");
  if (tot) tot.textContent = `共 ${rows.length} 条`;
}

async function openEdit(id) {
  const res = await fetch(`/purchase-orders/${id}`);
  if (!res.ok) return showMsg("加载订单失败", true);
  const r = await res.json();
  document.getElementById("po_id").value = String(r.id);
  document.getElementById("po-modal-title").textContent = `编辑 ${r.order_no}`;
  document.getElementById("po_order_no").value = r.order_no;
  document.getElementById("po_order_date").value = isoDateOnly(r.order_date);
  document.getElementById("po_delivery_address").value = r.delivery_address || "";
  document.getElementById("po_payment_terms").value = r.payment_terms || "";
  document.getElementById("po_delivery_terms").value = r.delivery_terms || "";
  document.getElementById("po_header_remark").value = r.header_remark || "";
  renderSupplierOptions(r.supplier_company || "");
  document.getElementById("po_supplier_tax_no").value = r.supplier_tax_no || "";
  document.getElementById("po_supplier_bank").value = r.supplier_bank || "";
  document.getElementById("po_supplier_account").value = r.supplier_account || "";
  document.getElementById("po_supplier_address").value = r.supplier_address || "";
  document.getElementById("po_supplier_phone").value = r.supplier_phone || "";
  document.getElementById("po_supplier_contact").value = r.supplier_contact || "";
  renderLinesFromOrder(r.lines || []);
  openModal();
}

document.getElementById("po_new").addEventListener("click", async () => {
  await resetFormNew();
  openModal();
});
document.getElementById("po_close").addEventListener("click", closeModal);
document.getElementById("po_add_line").addEventListener("click", () => {
  const tbody = document.getElementById("po_lines_tbody");
  const n = tbody.querySelectorAll("tr").length;
  tbody.insertAdjacentHTML("beforeend", lineRowHtml(n, {}));
  refreshLineMaterialLists();
  recalcPoLines();
});

document.getElementById("po_supplier_company").addEventListener("change", (e) => {
  fillSupplierFieldsByCompany(e.target.value || "");
  refreshLineMaterialLists();
});

document.getElementById("po_save").addEventListener("click", async () => {
  let lines;
  try {
    lines = collectLines();
  } catch (e) {
    return showMsg(e.message || "明细有误", true);
  }
  if (!lines.length) return showMsg("至少一行明细", true);
  const supplier = document.getElementById("po_supplier_company").value.trim();
  if (!supplier) return showMsg("供方公司名称必填", true);
  const id = document.getElementById("po_id").value;
  const order_date = document.getElementById("po_order_date").value;
  const payload = {
    order_date: order_date ? new Date(order_date + "T12:00:00").toISOString() : undefined,
    supplier_company: supplier,
    supplier_tax_no: document.getElementById("po_supplier_tax_no").value.trim() || null,
    supplier_bank: document.getElementById("po_supplier_bank").value.trim() || null,
    supplier_account: document.getElementById("po_supplier_account").value.trim() || null,
    supplier_address: document.getElementById("po_supplier_address").value.trim() || null,
    supplier_phone: document.getElementById("po_supplier_phone").value.trim() || null,
    supplier_contact: document.getElementById("po_supplier_contact").value.trim() || null,
    delivery_address: document.getElementById("po_delivery_address").value.trim() || null,
    payment_terms: document.getElementById("po_payment_terms").value.trim() || null,
    delivery_terms: document.getElementById("po_delivery_terms").value.trim() || null,
    header_remark: document.getElementById("po_header_remark").value.trim() || null,
    lines,
  };
  let url = "/purchase-orders";
  let method = "POST";
  if (id) {
    url = `/purchase-orders/${id}`;
    method = "PUT";
  }
  const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail) || "保存失败", true);
  }
  showMsg("保存成功");
  closeModal();
  loadList();
});

document.getElementById("po-tbody").addEventListener("click", (e) => {
  const qs = e.target.closest("[data-quick-status]");
  if (qs) {
    openQuickStatusModal(
      Number(qs.getAttribute("data-quick-status")),
      qs.getAttribute("data-order-no") || "",
      qs.getAttribute("data-current-status") || "draft",
      qs.getAttribute("data-current-payment") || "unpaid"
    );
    return;
  }
  const editBtn = e.target.closest("[data-edit]");
  if (editBtn) openEdit(Number(editBtn.getAttribute("data-edit")));
});

document.getElementById("po_status_modal_save").addEventListener("click", async () => {
  const id = document.getElementById("po_status_modal_id").value;
  if (!id) return;
  const status = document.getElementById("po_status_modal_sel").value;
  const payment_status = document.getElementById("po_payment_modal_sel").value;
  const res = await fetch(`/purchase-orders/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, payment_status }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    return showMsg(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail) || "更新失败", true);
  }
  showMsg("订单状态与付款状态已更新");
  closeQuickStatusModal();
  loadList();
});

document.getElementById("po_status_modal_cancel").addEventListener("click", closeQuickStatusModal);

bindLineEvents(document.getElementById("po_lines_tbody"));
loadSuppliers().then(loadList);
