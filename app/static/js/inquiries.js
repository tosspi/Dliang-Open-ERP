const msgEl = document.getElementById("msg");
const showMsg = (m, err = false) => { msgEl.textContent = m; msgEl.className = err ? "msg err" : "msg ok"; };

let allSuppliers = [];
let allMaterials = [];
let allCategories = [];

function todayISODate() {
  const d = new Date();
  const z = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth()+1)}-${z(d.getDate())}`;
}
function isoDateOnly(s) { return s ? String(s).slice(0, 10) : ""; }

function escAttr(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;");
}

function renderSupplierOptions(selected = "") {
  const sel = document.getElementById("iq_supplier_company");
  sel.innerHTML = `<option value="">请选择供应商</option>` + allSuppliers.filter(s => s.is_active !== false).map(s => `<option value="${escAttr(s.company_name)}">${escAttr(s.company_name || "")}</option>`).join("");
  if (selected) sel.value = selected;
}
function fillSupplierInfo(name) {
  const s = allSuppliers.find(x => (x.company_name || "") === (name || ""));
  if (!s) return;
  document.getElementById("iq_supplier_contact").value = s.contact_person || "";
  document.getElementById("iq_supplier_phone").value = s.phone || "";
}

function materialSpec(m) {
  const a = (m.spec || "").trim();
  const b = (m.drawing_no || "").trim();
  return [a, b].filter(Boolean).join(" / ");
}

function renderCategoryFilter() {
  const sel = document.getElementById("iq_f_category");
  sel.innerHTML = `<option value="">全部物料分类</option>` + allCategories.map(c => `<option value="${escAttr(c.name)}">${escAttr(c.name || "")}</option>`).join("");
}

function renderMaterialTable() {
  const code = (document.getElementById("iq_f_code").value || "").toLowerCase();
  const name = (document.getElementById("iq_f_name").value || "").toLowerCase();
  const cat = (document.getElementById("iq_f_category").value || "").toLowerCase();
  const rows = allMaterials.filter(m =>
    (!code || (m.code || "").toLowerCase().includes(code)) &&
    (!name || (m.name || "").toLowerCase().includes(name)) &&
    (!cat || (m.category || "").toLowerCase().includes(cat))
  );
  document.getElementById("iq_material_tbody").innerHTML = rows.map(m => `<tr>
    <td><input type="checkbox" class="iq-m-check" data-id="${m.id}"></td>
    <td>${escAttr(m.code || "")}</td><td>${escAttr(m.name || "")}</td><td>${escAttr(m.category || "")}</td><td>${escAttr(materialSpec(m))}</td><td>${escAttr(m.unit || "")}</td>
  </tr>`).join("");
}

function materialSelectOptions(selectedId) {
  const sel = selectedId === "" || selectedId == null ? NaN : Number(selectedId);
  return `<option value="">请选择物料</option>` + allMaterials.map(m =>
    `<option value="${m.id}" ${Number(m.id) === sel ? "selected" : ""}>${escAttr(m.code || "")} — ${escAttr(m.name || "")}</option>`
  ).join("");
}

function applyInquiryMaterialRow(tr) {
  const sel = tr.querySelector(".iq-material-id");
  const id = Number(sel && sel.value ? sel.value : 0);
  const m = allMaterials.find(x => x.id === id);
  const setText = (cls, v) => {
    const el = tr.querySelector(cls);
    if (el) el.textContent = v ?? "";
  };
  if (!m) {
    setText(".iq-show-code", "");
    setText(".iq-show-name", "");
    setText(".iq-show-spec", "");
    setText(".iq-show-mat", "");
    setText(".iq-show-grade", "");
    setText(".iq-show-unit", "");
    return;
  }
  setText(".iq-show-code", m.code || "");
  setText(".iq-show-name", m.name || "");
  setText(".iq-show-spec", materialSpec(m));
  setText(".iq-show-mat", m.material_name_attr || "");
  setText(".iq-show-grade", m.grade_attr || "");
  setText(".iq-show-unit", m.unit || "");
}

function lineHtml(i, r = {}) {
  const mid = r.material_id != null && r.material_id !== "" ? r.material_id : "";
  return `<tr data-i="${i}">
    <td><input class="iq-ln" type="number" value="${r.line_no ?? (i+1)}" min="1" style="width:52px"></td>
    <td><select class="iq-material-id">${materialSelectOptions(mid)}</select></td>
    <td class="iq-show-code"></td>
    <td class="iq-show-name"></td>
    <td class="iq-show-spec"></td>
    <td class="iq-show-mat"></td>
    <td class="iq-show-grade"></td>
    <td class="iq-show-unit"></td>
    <td><input class="iq-qty" type="number" value="${r.qty ?? 1}" min="0" step="0.0001" style="width:86px"></td>
    <td class="muted">—</td>
    <td class="muted">—</td>
    <td><input class="iq-remark" value="${escAttr(r.remark ?? "")}"></td>
    <td><button type="button" class="btn sm iq-del">删</button></td>
  </tr>`;
}

function collectLines() {
  const rows = [...document.querySelectorAll("#iq_lines_tbody tr")];
  return rows.map((tr, i) => ({
    line_no: Number(tr.querySelector(".iq-ln")?.value || i + 1),
    material_id: Number(tr.querySelector(".iq-material-id")?.value || 0),
    qty: Number(tr.querySelector(".iq-qty")?.value || 0),
    remark: tr.querySelector(".iq-remark")?.value?.trim() || null,
  })).filter((x) => x.material_id > 0 && x.qty > 0);
}

async function loadInquiries() {
  const res = await fetch("/inquiries");
  const rows = await res.json();
  document.getElementById("inq_tbody").innerHTML = rows.map(r => `<tr>
    <td>${escAttr(r.inquiry_no)}</td><td>${isoDateOnly(r.inquiry_date)}</td><td>${escAttr(r.supplier_company || "")}</td><td>${escAttr(r.status)}</td><td>—</td>
    <td><button class="btn sm" data-edit="${r.id}">编辑</button> <a class="btn sm" href="/export/inquiry/${r.id}" target="_blank">导出Excel</a></td>
  </tr>`).join("");
  document.getElementById("inq_total").textContent = `共 ${rows.length} 条`;
}

async function loadBasics() {
  const [spRes, mRes, cRes] = await Promise.all([fetch("/suppliers"), fetch("/materials"), fetch("/material-categories")]);
  allSuppliers = await spRes.json();
  allMaterials = await mRes.json();
  allCategories = (await cRes.json()).filter(x => x.is_active);
  renderSupplierOptions(document.getElementById("iq_supplier_company")?.value || "");
  renderCategoryFilter();
  renderMaterialTable();
}

function openModal() { document.getElementById("inq_modal").classList.remove("hidden"); }
function closeModal() { document.getElementById("inq_modal").classList.add("hidden"); }
async function resetForm(useCompanyDefaults = false) {
  document.getElementById("iq_id").value = "";
  document.getElementById("iq_no").value = "";
  document.getElementById("iq_date").value = todayISODate();
  document.getElementById("iq_valid_until").value = "";
  document.getElementById("iq_supplier_company").value = "";
  document.getElementById("iq_supplier_contact").value = "";
  document.getElementById("iq_supplier_phone").value = "";
  document.getElementById("iq_delivery_address").value = "";
  document.getElementById("iq_payment_terms").value = "";
  document.getElementById("iq_header_remark").value = "";
  document.getElementById("iq_lines_tbody").innerHTML = "";
  if (useCompanyDefaults) {
    try {
      const res = await fetch("/company-profile");
      if (res.ok) {
        const p = await res.json();
        document.getElementById("iq_delivery_address").value = (p.address || "").trim();
        document.getElementById("iq_supplier_contact").value = (p.contact_person || "").trim();
        document.getElementById("iq_supplier_phone").value = (p.phone || "").trim();
      }
    } catch (_) {}
  }
}

document.getElementById("inq_new").addEventListener("click", async () => {
  await resetForm(true);
  openModal();
});
document.getElementById("iq_close").addEventListener("click", closeModal);
document.getElementById("iq_supplier_company").addEventListener("change", (e) => fillSupplierInfo(e.target.value));
["iq_f_code", "iq_f_name"].forEach(id => document.getElementById(id).addEventListener("input", renderMaterialTable));
document.getElementById("iq_f_category").addEventListener("change", renderMaterialTable);
document.getElementById("iq_add_line").addEventListener("click", () => {
  const tb = document.getElementById("iq_lines_tbody");
  const n = tb.querySelectorAll("tr").length;
  tb.insertAdjacentHTML("beforeend", lineHtml(n, {}));
  applyInquiryMaterialRow(tb.querySelector("tr:last-child"));
});
document.getElementById("iq_add_checked").addEventListener("click", () => {
  const checked = [...document.querySelectorAll(".iq-m-check:checked")].map(x => Number(x.dataset.id));
  const tb = document.getElementById("iq_lines_tbody");
  const existingIds = new Set([...tb.querySelectorAll(".iq-material-id")].map((s) => Number(s.value || 0)).filter((id) => id > 0));
  checked.forEach((id) => {
    if (existingIds.has(id)) return;
    const m = allMaterials.find((x) => x.id === id);
    if (!m) return;
    tb.insertAdjacentHTML("beforeend", lineHtml(tb.querySelectorAll("tr").length, { material_id: m.id, qty: 1, remark: "" }));
    existingIds.add(id);
    applyInquiryMaterialRow(tb.querySelector("tr:last-child"));
  });
});
document.getElementById("iq_lines_tbody").addEventListener("change", (e) => {
  if (e.target.matches(".iq-material-id")) applyInquiryMaterialRow(e.target.closest("tr"));
});
document.getElementById("iq_lines_tbody").addEventListener("click", (e) => {
  const btn = e.target.closest(".iq-del");
  if (!btn) return;
  btn.closest("tr")?.remove();
});
document.getElementById("inq_tbody").addEventListener("click", async (e) => {
  const id = e.target.getAttribute("data-edit");
  if (!id) return;
  const res = await fetch(`/inquiries/${id}`);
  const r = await res.json();
  await resetForm(false);
  document.getElementById("iq_id").value = String(r.id);
  document.getElementById("iq_no").value = r.inquiry_no;
  document.getElementById("iq_date").value = isoDateOnly(r.inquiry_date);
  document.getElementById("iq_valid_until").value = isoDateOnly(r.valid_until);
  renderSupplierOptions(r.supplier_company || "");
  document.getElementById("iq_supplier_contact").value = r.supplier_contact || "";
  document.getElementById("iq_supplier_phone").value = r.supplier_phone || "";
  document.getElementById("iq_delivery_address").value = r.delivery_address || "";
  document.getElementById("iq_payment_terms").value = r.payment_terms || "";
  document.getElementById("iq_header_remark").value = r.header_remark || "";
  const tb = document.getElementById("iq_lines_tbody");
  (r.lines || []).forEach((ln, i) => {
    tb.insertAdjacentHTML("beforeend", lineHtml(i, ln));
    applyInquiryMaterialRow(tb.querySelector("tr:last-child"));
  });
  openModal();
});
document.getElementById("iq_save").addEventListener("click", async () => {
  const id = document.getElementById("iq_id").value;
  const lines = collectLines();
  if (!lines.length) return showMsg("请选择物料并填写有效数量（大于 0）", true);
  const payload = {
    inquiry_date: document.getElementById("iq_date").value ? new Date(document.getElementById("iq_date").value + "T12:00:00").toISOString() : undefined,
    valid_until: document.getElementById("iq_valid_until").value ? new Date(document.getElementById("iq_valid_until").value + "T12:00:00").toISOString() : null,
    supplier_company: document.getElementById("iq_supplier_company").value || null,
    supplier_contact: document.getElementById("iq_supplier_contact").value || null,
    supplier_phone: document.getElementById("iq_supplier_phone").value || null,
    delivery_address: document.getElementById("iq_delivery_address").value || null,
    payment_terms: document.getElementById("iq_payment_terms").value || null,
    header_remark: document.getElementById("iq_header_remark").value || null,
    lines,
  };
  const res = await fetch(id ? `/inquiries/${id}` : "/inquiries", {
    method: id ? "PUT" : "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(e.detail || "保存失败", true);
  }
  showMsg("保存成功");
  closeModal();
  loadInquiries();
});

loadBasics().then(loadInquiries);
