const msgEl = document.getElementById("msg");
const tbody = document.getElementById("supplier-tbody");
let allSuppliers = [];
let allCategories = [];
let allMaterials = [];

const showMsg = (m, err = false) => {
  msgEl.textContent = m;
  msgEl.className = err ? "msg err" : "msg ok";
};

function getCategoryValues() {
  return Array.from(document.querySelectorAll("#sp_supplier_categories input[type='checkbox']:checked")).map(x => x.value);
}

function renderCategoryCheckboxes() {
  const container = document.getElementById("sp_supplier_categories");
  container.innerHTML = allCategories.map(c => `<label><input type="checkbox" value="${c.name}">${c.name}</label>`).join("");
}

function setCategoryValues(values = []) {
  const selected = new Set(values || []);
  document.querySelectorAll("#sp_supplier_categories input[type='checkbox']").forEach(x => {
    x.checked = selected.has(x.value);
  });
}

function getManagedMaterialIds() {
  return Array.from(document.querySelectorAll("#sp_managed_materials input[type='checkbox']:checked"))
    .map(x => Number(x.value))
    .filter(x => Number.isFinite(x));
}

function renderMaterialCheckboxes() {
  const kw = (document.getElementById("sp_material_kw")?.value || "").trim().toLowerCase();
  const container = document.getElementById("sp_managed_materials");
  const rows = allMaterials.filter(m =>
    !kw || (m.code || "").toLowerCase().includes(kw) || (m.name || "").toLowerCase().includes(kw)
  );
  container.innerHTML = rows.map(m => `<label><input type="checkbox" value="${m.id}"><span>${m.code} | ${m.name}</span></label>`).join("");
}

function setManagedMaterialIds(values = []) {
  const selected = new Set((values || []).map(Number));
  document.querySelectorAll("#sp_managed_materials input[type='checkbox']").forEach(x => {
    x.checked = selected.has(Number(x.value));
  });
}

function getFilters() {
  return {
    code: document.getElementById("s_code").value.trim().toLowerCase(),
    name: document.getElementById("s_name").value.trim().toLowerCase(),
    creditCode: document.getElementById("s_credit_code").value.trim().toLowerCase(),
  };
}

function renderTable() {
  const f = getFilters();
  const rows = allSuppliers.filter(s =>
    (!f.code || (s.supplier_code || "").toLowerCase().includes(f.code)) &&
    (!f.name || (s.company_name || "").toLowerCase().includes(f.name)) &&
    (!f.creditCode || (s.credit_code || "").toLowerCase().includes(f.creditCode))
  );

  tbody.innerHTML = rows.map(s => `<tr>
    <td>${s.supplier_code || ""}</td>
    <td>${s.company_name || ""}</td>
    <td>${(s.supplier_categories || []).join("、")}</td>
    <td>${s.payment_term_days != null && s.payment_term_days !== "" ? s.payment_term_days : "—"}</td>
    <td>${s.credit_code || ""}</td>
    <td>${s.bank_name || ""}</td>
    <td>${s.bank_account || ""}</td>
    <td>${s.bank_no || ""}</td>
    <td>${s.contact_person || ""}</td>
    <td>${s.phone || ""}</td>
    <td>${s.address || ""}</td>
    <td>${s.is_active ? '<span class="tag released">启用</span>' : '<span class="tag obsolete">停用</span>'}</td>
    <td>
      <button class="btn sm" onclick="editSupplier(${s.id})">编辑</button>
      <button class="btn sm" onclick="disableSupplier(${s.id})">停用</button>
    </td>
  </tr>`).join("");
  const tot = document.getElementById("supplier-record-total");
  if (tot) tot.textContent = `共 ${rows.length} 条记录`;
}

async function loadSuppliers() {
  const res = await fetch("/suppliers");
  allSuppliers = await res.json();
  renderTable();
}

async function loadCategories() {
  const res = await fetch("/material-categories");
  const rows = await res.json();
  allCategories = rows.filter(x => x.is_active);
  renderCategoryCheckboxes();
}

async function loadMaterials() {
  const res = await fetch("/materials");
  const rows = await res.json();
  allMaterials = rows.filter(x => x.is_active);
  renderMaterialCheckboxes();
}

function openSupplierModal() {
  document.getElementById("supplier-modal").classList.remove("hidden");
  document.getElementById("supplier-modal-title").textContent = "新增供应商";
  document.getElementById("sp_supplier_code").value = "";
}

function closeSupplierModal() {
  document.getElementById("supplier-modal").classList.add("hidden");
  document.getElementById("supplier-form").reset();
  document.getElementById("sp_id").value = "";
  setCategoryValues([]);
  document.getElementById("sp_material_kw").value = "";
  renderMaterialCheckboxes();
  setManagedMaterialIds([]);
}

function editSupplier(id) {
  const s = allSuppliers.find(x => x.id === id);
  if (!s) return;
  openSupplierModal();
  document.getElementById("supplier-modal-title").textContent = "编辑供应商";
  ["id", "supplier_code", "company_name", "payment_term_days", "credit_code", "bank_name", "bank_account", "bank_no", "contact_person", "phone", "address"].forEach(k => {
    const el = document.getElementById("sp_" + k);
    if (el) el.value = s[k] ?? "";
  });
  setCategoryValues(s.supplier_categories || []);
  const ptd = document.getElementById("sp_payment_term_days");
  if (ptd) ptd.value = s.payment_term_days != null && s.payment_term_days !== "" ? String(s.payment_term_days) : "";
  document.getElementById("sp_material_kw").value = "";
  renderMaterialCheckboxes();
  setManagedMaterialIds(s.managed_material_ids || []);
}

async function saveSupplier() {
  const id = document.getElementById("sp_id").value;
  const ptdRaw = (document.getElementById("sp_payment_term_days")?.value || "").trim();
  let payment_term_days = null;
  if (ptdRaw !== "") {
    const n = parseInt(ptdRaw, 10);
    if (!Number.isFinite(n) || n < 0) return showMsg("账期须为非负整数或留空", true);
    payment_term_days = n;
  }
  const payload = {
    company_name: sp_company_name.value,
    supplier_categories: getCategoryValues(),
    managed_material_ids: getManagedMaterialIds(),
    payment_term_days,
    credit_code: sp_credit_code.value || null,
    bank_name: sp_bank_name.value || null,
    bank_account: sp_bank_account.value || null,
    bank_no: sp_bank_no.value || null,
    contact_person: sp_contact_person.value || null,
    phone: sp_phone.value || null,
    address: sp_address.value || null,
    is_active: true,
  };
  if (!payload.company_name) return showMsg("公司名称必填", true);
  const url = id ? `/suppliers/${id}` : "/suppliers";
  const method = id ? "PUT" : "POST";
  const res = await fetch(url, { method, headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload) });
  if (!res.ok) {
    const e = await res.json();
    return showMsg(e.detail || "保存失败", true);
  }
  showMsg("保存成功");
  closeSupplierModal();
  loadSuppliers();
}

async function disableSupplier(id) {
  if (!confirm("确认停用该供应商？")) return;
  const res = await fetch(`/suppliers/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const e = await res.json();
    return showMsg(e.detail || "停用失败", true);
  }
  showMsg("已停用");
  loadSuppliers();
}

["s_code", "s_name", "s_credit_code"].forEach(id => {
  document.getElementById(id).addEventListener("input", renderTable);
});
document.getElementById("sp_material_kw").addEventListener("input", () => {
  const selected = getManagedMaterialIds();
  renderMaterialCheckboxes();
  setManagedMaterialIds(selected);
});

Promise.all([loadCategories(), loadMaterials()]).then(loadSuppliers);
