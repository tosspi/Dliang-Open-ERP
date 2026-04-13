const msgBox = document.getElementById("msg");
const tbody = document.querySelector("#products-table tbody");
let allProducts = [];
let productCategories = [];
let allMaterials = [];

const typeMap = { self_made: "自产品", purchased: "外购品" };
const fmt3 = (v) => (v === null || v === undefined || v === "" ? "" : Number.isFinite(Number(v)) ? Number(v).toFixed(3) : String(v));
const fmt2 = (v) => (v === null || v === undefined || v === "" ? "" : Number.isFinite(Number(v)) ? Number(v).toFixed(2) : String(v));
const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

const showMsg = (m, err = false) => {
  msgBox.textContent = m;
  msgBox.className = err ? "msg err" : "msg ok";
};

function getViewMode() {
  return (document.getElementById("product_view_mode")?.value || "self_made").toLowerCase();
}

function renderCategoryFilter() {
  const f = document.getElementById("p_category");
  const m = document.getElementById("pd_product_category");
  const opts = productCategories.map(c => `<option value="${c.name}">${c.name}</option>`).join("");
  f.innerHTML = `<option value="">全部类别</option>${opts}`;
  m.innerHTML = `<option value="">请选择类别</option>${opts}`;
}

function renderMaterialOptions(selected = "") {
  const sel = document.getElementById("pd_linked_material_id");
  const opts = allMaterials.map(m => `<option value="${m.id}">${m.code} | ${m.name}</option>`).join("");
  sel.innerHTML = `<option value="">请选择关联物料</option>${opts}`;
  if (selected) sel.value = String(selected);
}

function onProductTypeChange() {
  const t = document.getElementById("pd_product_type").value;
  const linkLabel = document.getElementById("pd_linked_material_label");
  linkLabel.style.display = t === "purchased" ? "" : "none";
}
window.onProductTypeChange = onProductTypeChange;

function renderTable() {
  const mode = getViewMode();
  const keyword = (document.getElementById("p_name").value || "").trim().toLowerCase();
  const model = (document.getElementById("p_model").value || "").trim().toLowerCase();
  const category = (document.getElementById("p_category").value || "").trim().toLowerCase();
  const rows = allProducts.filter(p =>
    p.product_type === mode &&
    (!keyword || (p.product_name || "").toLowerCase().includes(keyword)) &&
    (!model || (p.model_no || "").toLowerCase().includes(model)) &&
    (!category || (p.product_category || "").toLowerCase().includes(category))
  );
  tbody.innerHTML = rows.map(p => `<tr>
    <td>${p.product_code || ""}</td>
    <td>${p.product_name || ""}</td>
    <td>${typeMap[p.product_type] || p.product_type}</td>
    <td>${p.product_category || ""}</td>
    <td>${p.model_no || ""}</td>
    <td title="${esc(p.spec_drawing)}">${p.spec_drawing || ""}</td>
    <td>${fmt2(p.cost)}</td>
    <td>${fmt2(p.sale_price_with_tax)}</td>
    <td>${fmt3(p.current_stock)}</td>
    <td>${fmt3(p.safety_stock)}</td>
    <td>${p.remark || ""}</td>
    <td>
      <button class="btn sm" onclick="editProduct(${p.id})">编辑</button>
      ${p.product_type === "self_made" ? `<a class="btn sm" href="${p.current_bom_id ? `/ui/boms/${p.current_bom_id}` : `/ui/boms?product_code=${encodeURIComponent(p.product_code)}`}">查看BOM明细</a>` : ""}
      <button class="btn sm" onclick="deleteProduct(${p.id})">删除</button>
    </td>
  </tr>`).join("");
  const tot = document.getElementById("product-record-total");
  if (tot) tot.textContent = `共 ${rows.length} 条记录`;
}

async function loadProducts() {
  const mode = getViewMode();
  const res = await fetch(`/products?product_type=${encodeURIComponent(mode)}`);
  allProducts = await res.json();
  renderTable();
}

async function loadProductCategories() {
  const res = await fetch("/system-options?option_type=product_category");
  const rows = await res.json();
  productCategories = rows.filter(x => x.is_active);
  renderCategoryFilter();
}

async function loadMaterials() {
  const res = await fetch("/materials");
  allMaterials = await res.json();
  renderMaterialOptions();
}

function openProductModal() {
  document.getElementById("product-modal").classList.remove("hidden");
  document.getElementById("product-modal-title").textContent = "新增产品";
  document.getElementById("pd_id").value = "";
  document.getElementById("pd_product_code").value = "";
  document.getElementById("pd_product_code").readOnly = false;
  document.getElementById("pd_product_type").value = getViewMode();
  onProductTypeChange();
}
window.openProductModal = openProductModal;

function closeProductModal() {
  document.getElementById("product-modal").classList.add("hidden");
  document.getElementById("product-form").reset();
  document.getElementById("pd_id").value = "";
}
window.closeProductModal = closeProductModal;

window.editProduct = function editProduct(id) {
  const p = allProducts.find(x => x.id === id);
  if (!p) return;
  openProductModal();
  document.getElementById("product-modal-title").textContent = "编辑产品";
  document.getElementById("pd_id").value = p.id;
  document.getElementById("pd_product_code").value = p.product_code || "";
  document.getElementById("pd_product_code").readOnly = false;
  document.getElementById("pd_product_name").value = p.product_name || "";
  document.getElementById("pd_product_type").value = p.product_type || getViewMode();
  document.getElementById("pd_product_category").value = p.product_category || "";
  document.getElementById("pd_model_no").value = p.model_no || "";
  document.getElementById("pd_spec_drawing").value = p.spec_drawing || "";
  document.getElementById("pd_sale_price_with_tax").value = Number(p.sale_price_with_tax || 0);
  document.getElementById("pd_current_stock").value = Number(p.current_stock || 0);
  document.getElementById("pd_safety_stock").value = Number(p.safety_stock || 0);
  document.getElementById("pd_remark").value = p.remark || "";
  document.getElementById("pd_is_active").value = p.is_active ? "true" : "false";
  renderMaterialOptions(p.linked_material_id || "");
  onProductTypeChange();
};

window.saveProduct = async function saveProduct() {
  const id = document.getElementById("pd_id").value;
  const product_type = document.getElementById("pd_product_type").value;
  const payload = {
    product_name: document.getElementById("pd_product_name").value.trim(),
    product_type,
    product_category: document.getElementById("pd_product_category").value || null,
    model_no: document.getElementById("pd_model_no").value.trim() || null,
    spec_drawing: document.getElementById("pd_spec_drawing").value.trim() || null,
    sale_price_with_tax: Number(document.getElementById("pd_sale_price_with_tax").value || 0),
    current_stock: Number(document.getElementById("pd_current_stock").value || 0),
    safety_stock: Number(document.getElementById("pd_safety_stock").value || 0),
    remark: document.getElementById("pd_remark").value.trim() || null,
    linked_material_id: product_type === "purchased" ? (document.getElementById("pd_linked_material_id").value ? Number(document.getElementById("pd_linked_material_id").value) : null) : null,
    is_active: document.getElementById("pd_is_active").value === "true",
  };
  const productCode = document.getElementById("pd_product_code").value.trim();
  if (!productCode) return showMsg("产品编码必填", true);
  payload.product_code = productCode;
  if (!payload.product_name) return showMsg("产品名称必填", true);
  if (product_type === "purchased" && !payload.linked_material_id) return showMsg("外购品请关联物料", true);
  const url = id ? `/products/${id}` : "/products";
  const method = id ? "PUT" : "POST";
  const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(e.detail || "保存失败", true);
  }
  showMsg("保存成功");
  closeProductModal();
  loadProducts();
};

["p_name", "p_model"].forEach(id => document.getElementById(id).addEventListener("input", renderTable));
document.getElementById("p_category").addEventListener("change", renderTable);

Promise.all([loadProductCategories(), loadMaterials()]).then(loadProducts);

window.deleteProduct = async function deleteProduct(id) {
  if (!confirm("确认删除该产品？")) return;
  const res = await fetch(`/products/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(e.detail || "删除失败", true);
  }
  showMsg("删除成功");
  loadProducts();
};
