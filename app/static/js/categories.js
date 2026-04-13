const catMsg = (m, err = false) => {
  const el = document.getElementById("msg");
  el.textContent = m;
  el.className = err ? "msg err" : "msg ok";
};
let allCategories = [];
const typeSelect = () => document.getElementById("c_type");
const isCategoryType = () => typeSelect().value === "category";

function renderCategories() {
  const keyword = (document.getElementById("c_name").value || "").toLowerCase();
  const rows = allCategories.filter(c => !keyword || (c.name || "").toLowerCase().includes(keyword));
  const showPrefix = isCategoryType();
  document.getElementById("cat-tbody").innerHTML = rows.map(c => `<tr>
    <td>${c.name}</td>${showPrefix ? `<td>${c.code_prefix || ""}</td>` : ""}<td>${c.sort_order}</td>
    <td>${c.is_active ? '<span class="tag released">启用</span>' : '<span class="tag obsolete">停用</span>'}</td>
    <td>${c.remark || ''}</td>
    <td>
      <button class="btn sm" onclick='editCategory(${JSON.stringify(c)})'>编辑</button>
      <button class="btn sm" onclick='deleteCategory(${c.id})'>删除</button>
    </td>
  </tr>`).join("");
  const tot = document.getElementById("cat-record-total");
  if (tot) tot.textContent = `共 ${rows.length} 条记录`;
}

async function loadCategories() {
  const t = typeSelect().value;
  const url = t === "category" ? "/material-categories" : `/system-options?option_type=${encodeURIComponent(t)}`;
  const res = await fetch(url);
  allCategories = await res.json();
  renderCategories();
}

function openCategoryModal() {
  document.getElementById("cat-modal").classList.remove("hidden");
  document.getElementById("cat-title").textContent = "新增类别";
}
function closeCategoryModal() {
  document.getElementById("cat-modal").classList.add("hidden");
  document.getElementById("cat-form").reset();
  document.getElementById("ct_id").value = "";
}
function editCategory(c) {
  openCategoryModal();
  document.getElementById("cat-title").textContent = "编辑类别";
  ["id", "name", "code_prefix", "sort_order", "remark"].forEach(k => {
    const el = document.getElementById("ct_" + k);
    if (el) el.value = c[k] ?? "";
  });
  document.getElementById("ct_is_active").value = c.is_active ? "true" : "false";
}
async function saveCategory() {
  const id = document.getElementById("ct_id").value;
  const base = {
    name: ct_name.value,
    sort_order: Number(ct_sort_order.value || 0),
    is_active: ct_is_active.value === "true",
    remark: ct_remark.value || null,
  };
  let payload = base;
  let url = "";
  if (isCategoryType()) {
    payload = {...base, code_prefix: ct_code_prefix.value};
    if (!payload.code_prefix) return catMsg("分类必须填写编码前缀", true);
    url = id ? `/material-categories/${id}` : "/material-categories";
  } else {
    payload = {...base, option_type: typeSelect().value};
    url = id ? `/system-options/${id}` : "/system-options";
  }
  const method = id ? "PUT" : "POST";
  const res = await fetch(url, { method, headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload) });
  if (!res.ok) {
    const e = await res.json();
    return catMsg(e.detail || "保存失败", true);
  }
  catMsg("保存成功");
  closeCategoryModal();
  loadCategories();
}

async function deleteCategory(id) {
  if (!confirm("确认删除该项？")) return;
  let url = "";
  if (isCategoryType()) {
    url = `/material-categories/${id}/hard-delete`;
  } else {
    url = `/system-options/${id}/hard-delete`;
  }
  const res = await fetch(url, { method: "DELETE" });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return catMsg(e.detail || "删除失败", true);
  }
  catMsg("删除成功");
  loadCategories();
}

function onTypeChanged() {
  const showPrefix = isCategoryType();
  document.getElementById("label-prefix").style.display = showPrefix ? "" : "none";
  document.getElementById("th-prefix").style.display = showPrefix ? "" : "none";
  const t = typeSelect().value;
  const hintMap = {
    category: "物料分类",
    unit: "单位",
    tax_rate: "税率",
    material_attr: "材质",
    grade: "等级",
    product_category: "产品类别",
  };
  const nm = document.getElementById("c_name");
  if (nm) nm.placeholder = `按${hintMap[t] || "名称"}搜索`;
  loadCategories();
}

// Explicit binding avoids relying on inline handlers only.
document.getElementById("c_type").addEventListener("change", onTypeChanged);
document.getElementById("c_name").addEventListener("input", renderCategories);

// Expose handlers for inline onclick/onchange attributes in template.
window.onTypeChanged = onTypeChanged;
window.openCategoryModal = openCategoryModal;
window.closeCategoryModal = closeCategoryModal;
window.saveCategory = saveCategory;
window.editCategory = editCategory;
window.deleteCategory = deleteCategory;

onTypeChanged();
