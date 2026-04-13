const msgBox = document.getElementById("msg");
const tbody = document.querySelector("#materials-table tbody");
let allMaterials = [];
let allSuppliers = [];
let allCategories = [];
let optionMap = { unit: [], tax_rate: [], material_attr: [], grade: [] };
const partTypeMap = { standard: "标准件", custom: "自制件", assembly: "装配件" };
const statusMap = { draft: "草稿", released: "已发布", obsolete: "已停用(历史)" };
const fmt3 = (v) => (v === null || v === undefined || v === "" ? "" : Number.isFinite(Number(v)) ? Number(v).toFixed(3) : String(v));
const escAttr = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
/** textarea 内容转义，避免 </textarea> 注入 */
const escTextarea = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

let materialTableEditMode = false;

function formatSpecDrawing(m) {
  const a = (m.spec || "").trim();
  const b = (m.drawing_no || "").trim();
  if (a && b) return `${a} / ${b}`;
  return a || b || "";
}

/** 与列表展示「规格 / 图号」互逆：含「 / 」则拆成规格+图号，否则整段为规格 */
function parseSpecDrawingInput(raw) {
  const t = (raw || "").trim();
  if (!t) return { spec: null, drawing_no: null };
  const idx = t.indexOf(" / ");
  if (idx >= 0) {
    const a = t.slice(0, idx).trim();
    const b = t.slice(idx + 3).trim();
    return { spec: a || null, drawing_no: b || null };
  }
  return { spec: t, drawing_no: null };
}

function normStr(v) {
  return (v ?? "").toString().trim();
}

function normDraw(v) {
  const t = normStr(v);
  return t || null;
}

function materialRowUnchanged(m, payload, spec, drawingNo) {
  const sameRev = normStr(payload.current_revision) === normStr(m.current_revision);
  const sameSpec = normDraw(spec) === normDraw(m.spec);
  const sameDraw = normDraw(drawingNo) === normDraw(m.drawing_no);
  return (
    normStr(payload.name) === normStr(m.name) &&
    sameRev &&
    sameSpec &&
    sameDraw &&
    normStr(payload.usage) === normStr(m.usage) &&
    Number(payload.current_stock) === Number(m.current_stock || 0) &&
    Number(payload.safety_stock) === Number(m.safety_stock || 0) &&
    Number(payload.unit_price) === Number(m.unit_price || 0) &&
    normStr(payload.remark) === normStr(m.remark)
  );
}

function setMaterialFiltersDisabled(disabled) {
  ["f_code", "f_name", "f_category", "f_status"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.disabled = disabled;
  });
  const pt = document.getElementById("f_part_type");
  if (!pt) return;
  if (disabled) pt.disabled = true;
  else applyViewModePreset();
}

function updateMaterialBatchBar() {
  const t = document.getElementById("material-batch-toggle");
  const s = document.getElementById("material-batch-save");
  const c = document.getElementById("material-batch-cancel");
  if (t) t.classList.toggle("hidden", materialTableEditMode);
  if (s) s.classList.toggle("hidden", !materialTableEditMode);
  if (c) c.classList.toggle("hidden", !materialTableEditMode);
  setMaterialFiltersDisabled(materialTableEditMode);
}

const showMsg = (m, err = false) => {
  msgBox.textContent = m;
  msgBox.className = err ? "msg err" : "msg ok";
};

function getFilters() {
  return {
    code: document.getElementById("f_code").value.trim().toLowerCase(),
    name: document.getElementById("f_name").value.trim().toLowerCase(),
    category: document.getElementById("f_category").value.trim().toLowerCase(),
    part_type: document.getElementById("f_part_type").value,
    status: document.getElementById("f_status").value,
  };
}

function renderCategoryOptions() {
  const f = document.getElementById("f_category");
  const m = document.getElementById("m_category");
  const opts = allCategories.map(c => `<option value="${c.name}">${c.name}</option>`).join("");
  if (f) f.innerHTML = `<option value="">全部物料分类</option>${opts}`;
  if (m) m.innerHTML = `<option value="">请选择物料分类</option>${opts}`;
}

function renderOptionSelect(selectId, options, placeholder) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const opts = (options || []).map(o => `<option value="${o.name}">${o.name}</option>`).join("");
  sel.innerHTML = `<option value="">${placeholder}</option>${opts}`;
}

function applyViewModePreset() {
  const mode = (document.getElementById("view_mode")?.value || "all").toLowerCase();
  const partTypeSelect = document.getElementById("f_part_type");
  if (!partTypeSelect) return;
  if (mode === "standard") {
    partTypeSelect.value = "standard";
    partTypeSelect.disabled = true;
  } else {
    partTypeSelect.disabled = false;
    if (mode === "nonstandard") {
      partTypeSelect.value = "";
    }
  }
}

function renderTable() {
  const f = getFilters();
  const mode = (document.getElementById("view_mode")?.value || "all").toLowerCase();
  const rows = allMaterials.filter(m =>
    (mode !== "standard" || m.part_type === "standard") &&
    (mode !== "nonstandard" || (m.part_type === "custom" || m.part_type === "assembly")) &&
    (!f.code || (m.code || "").toLowerCase().includes(f.code)) &&
    (!f.name || (m.name || "").toLowerCase().includes(f.name)) &&
    (!f.category || (m.category || "").toLowerCase().includes(f.category)) &&
    (!f.part_type || m.part_type === f.part_type) &&
    (!f.status || m.status === f.status)
  );
  const edit = materialTableEditMode;
  tbody.innerHTML = rows.map((m) => {
    const actionsDisabled = edit ? "disabled" : "";
    const actions = `
      <div class="material-actions">
        <button type="button" class="btn sm" onclick="editMaterial(${m.id})" ${actionsDisabled}>编辑</button>
        <button type="button" class="btn sm" onclick="disableMaterial(${m.id})" ${actionsDisabled}>停用</button>
        <button type="button" class="btn sm" onclick="removeMaterial(${m.id})" ${actionsDisabled}>删除</button>
        <a class="btn sm" href="/ui/materials/${m.id}/revisions">版本</a>
      </div>`;
    if (!edit) {
      return `<tr data-mid="${m.id}">
    <td>${m.code || ""}</td><td title="${escAttr(m.name)}">${m.name || ""}</td><td>${m.current_revision || ""}</td><td title="${escAttr(formatSpecDrawing(m))}">${formatSpecDrawing(m)}</td><td>${m.unit || ""}</td><td>${m.category || ""}</td><td>${partTypeMap[m.part_type] || m.part_type || ""}</td>
    <td>${m.usage || ""}</td><td>${m.material_name_attr || ""}</td><td>${m.grade_attr || ""}</td>
    <td>${m.default_supplier || ""}</td><td>${m.purchase_link ? `<a href="${String(m.purchase_link).replace(/"/g, "&quot;")}" target="_blank" rel="noopener noreferrer">查看</a>` : ""}</td><td><span class="tag ${m.status}">${statusMap[m.status] || m.status}</span></td><td>${m.is_active ? '<span class="tag released">启用</span>' : '<span class="tag obsolete">停用</span>'}</td><td>${fmt3(m.current_stock)}</td><td>${fmt3(m.safety_stock)}</td><td>${fmt3(m.unit_price)}</td><td>${m.tax_rate || ""}</td><td>${m.remark || ""}</td>
    <td>${actions}</td>
  </tr>`;
    }
    return `<tr data-mid="${m.id}">
    <td>${m.code || ""}</td>
    <td><input type="text" class="me-input me-name" value="${escAttr(m.name)}"></td>
    <td><input type="text" class="me-input me-rev" value="${escAttr(m.current_revision || "")}"></td>
    <td><textarea class="me-input me-specdraw" rows="2" spellcheck="false">${escTextarea(formatSpecDrawing(m))}</textarea></td>
    <td>${m.unit || ""}</td><td>${m.category || ""}</td><td>${partTypeMap[m.part_type] || m.part_type || ""}</td>
    <td><input type="text" class="me-input me-usage" value="${escAttr(m.usage || "")}"></td>
    <td>${m.material_name_attr || ""}</td><td>${m.grade_attr || ""}</td>
    <td>${m.default_supplier || ""}</td><td>${m.purchase_link ? `<a href="${String(m.purchase_link).replace(/"/g, "&quot;")}" target="_blank" rel="noopener noreferrer">查看</a>` : ""}</td><td><span class="tag ${m.status}">${statusMap[m.status] || m.status}</span></td><td>${m.is_active ? '<span class="tag released">启用</span>' : '<span class="tag obsolete">停用</span>'}</td>
    <td><input type="number" class="me-input me-cstock" step="0.001" value="${Number(m.current_stock ?? 0)}"></td>
    <td><input type="number" class="me-input me-sstock" step="0.001" value="${Number(m.safety_stock ?? 0)}"></td>
    <td><input type="number" class="me-input me-price" step="0.01" min="0" value="${Number(m.unit_price ?? 0)}"></td>
    <td>${m.tax_rate || ""}</td>
    <td><textarea class="me-input me-remark" rows="2" spellcheck="false">${escTextarea(m.remark || "")}</textarea></td>
    <td>${actions}</td>
  </tr>`;
  }).join("");
  const tot = document.getElementById("materials-record-total");
  if (tot) tot.textContent = `共 ${rows.length} 条记录`;
}

async function saveMaterialBatchEdits() {
  const trs = [...tbody.querySelectorAll("tr[data-mid]")];
  if (!trs.length) {
    materialTableEditMode = false;
    updateMaterialBatchBar();
    renderTable();
    return;
  }
  const errors = [];
  let saved = 0;
  let skipped = 0;
  for (const tr of trs) {
    const id = Number(tr.dataset.mid);
    const m = allMaterials.find((x) => x.id === id);
    if (!m) continue;
    const name = tr.querySelector(".me-name")?.value?.trim() || "";
    if (!name) {
      errors.push(`${m.code || id}：名称不能为空`);
      continue;
    }
    const { spec, drawing_no } = parseSpecDrawingInput(tr.querySelector(".me-specdraw")?.value || "");
    const revRaw = tr.querySelector(".me-rev")?.value?.trim() || "";
    const payload = {
      name,
      current_revision: revRaw || null,
      spec: spec ?? null,
      drawing_no: drawing_no ?? null,
      usage: normStr(tr.querySelector(".me-usage")?.value || "") || null,
      current_stock: Number(tr.querySelector(".me-cstock")?.value || 0),
      safety_stock: Number(tr.querySelector(".me-sstock")?.value || 0),
      unit_price: Number(tr.querySelector(".me-price")?.value || 0),
      remark: normStr(tr.querySelector(".me-remark")?.value || "") || null,
    };
    if (materialRowUnchanged(m, payload, spec, drawing_no)) {
      skipped += 1;
      continue;
    }
    const res = await fetch(`/materials/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      let detail = "保存失败";
      try {
        const e = await res.json();
        detail = e.detail || detail;
        if (Array.isArray(detail)) detail = JSON.stringify(detail);
      } catch (_) {}
      errors.push(`${m.code || id}：${detail}`);
      continue;
    }
    saved += 1;
  }
  materialTableEditMode = false;
  updateMaterialBatchBar();
  await loadMaterials();
  if (errors.length) {
    showMsg(`已保存 ${saved} 条，跳过未改 ${skipped} 条；失败 ${errors.length} 条：${errors.slice(0, 3).join("；")}${errors.length > 3 ? "…" : ""}`, true);
  } else {
    showMsg(saved ? `已保存 ${saved} 条${skipped ? `，未改动 ${skipped} 条` : ""}` : skipped ? `无修改（${skipped} 条）` : "无数据");
  }
}

async function loadSuppliers() {
  const res = await fetch("/suppliers");
  allSuppliers = await res.json();
}

async function loadCategories() {
  const res = await fetch("/material-categories");
  const rows = await res.json();
  allCategories = rows.filter(x => x.is_active);
  renderCategoryOptions();
}

async function loadSystemOptions() {
  const res = await fetch("/system-options");
  const rows = await res.json();
  const active = rows.filter(x => x.is_active);
  optionMap = {
    unit: active.filter(x => x.option_type === "unit"),
    tax_rate: active.filter(x => x.option_type === "tax_rate"),
    material_attr: active.filter(x => x.option_type === "material_attr"),
    grade: active.filter(x => x.option_type === "grade"),
  };
  renderOptionSelect("m_unit", optionMap.unit, "请选择单位");
  renderOptionSelect("m_tax_rate", optionMap.tax_rate, "请选择税率");
  renderOptionSelect("m_material_name_attr", optionMap.material_attr, "请选择材质");
  renderOptionSelect("m_grade_attr", optionMap.grade, "请选择等级");
}

function refreshSupplierOptions(selected = "") {
  const category = (document.getElementById("m_category").value || "").trim();
  const supplierSelect = document.getElementById("m_default_supplier");
  const filtered = allSuppliers.filter(s => {
    const cats = s.supplier_categories || [];
    return !category || cats.includes(category);
  });
  supplierSelect.innerHTML = `<option value="">请选择供应商</option>` + filtered.map(s => `<option value="${s.company_name}">${s.company_name}${s.supplier_code ? "（" + s.supplier_code + "）" : ""}</option>`).join("");
  if (selected) supplierSelect.value = selected;
}

async function loadMaterials() {
  const res = await fetch("/materials");
  allMaterials = await res.json();
  renderTable();
}

function openMaterialModal() {
  document.getElementById("material-modal").classList.remove("hidden");
  document.getElementById("material-modal-title").textContent = "新增物料";
  document.getElementById("m_code").value = "";
  const sd = document.getElementById("m_spec_draw");
  if (sd) sd.value = "";
  if (!document.getElementById("m_category").value && allCategories.length) {
    document.getElementById("m_category").value = allCategories[0].name;
  }
  refreshSupplierOptions();
}
function closeMaterialModal() {
  document.getElementById("material-modal").classList.add("hidden");
  document.getElementById("material-form").reset();
  document.getElementById("m_id").value = "";
}

function editMaterial(id) {
  const m = allMaterials.find(x => x.id === id);
  if (!m) return;
  openMaterialModal();
  document.getElementById("material-modal-title").textContent = "编辑物料";
  [
    "id","code","name","unit","category","part_type","default_supplier","tax_rate","unit_price","safety_stock",
    "current_stock","usage","material_name_attr","grade_attr","purchase_link","current_revision","status","remark"
  ].forEach(k => {
    const el = document.getElementById("m_" + k);
    if (el) el.value = m[k] ?? "";
  });
  const sd = document.getElementById("m_spec_draw");
  if (sd) {
    const a = (m.spec || "").trim();
    const b = (m.drawing_no || "").trim();
    sd.value = [a, b].filter(Boolean).join("\n");
  }
  if (m.status === "obsolete") {
    document.getElementById("m_status").value = "draft";
  }
  refreshSupplierOptions(m.default_supplier || "");
}

async function saveMaterial() {
  const id = document.getElementById("m_id").value;
  const rawLines = (document.getElementById("m_spec_draw")?.value || "").split("\n").map((s) => s.trim());
  const specVal = rawLines[0] || "";
  const drawingVal = rawLines.slice(1).filter(Boolean).join("\n") || "";
  const payload = {
    name: m_name.value, spec: specVal, drawing_no: drawingVal || null, unit: m_unit.value, category: m_category.value,
    part_type: m_part_type.value, default_supplier: m_default_supplier.value, tax_rate: m_tax_rate.value, unit_price: Number(m_unit_price.value || 0),
    safety_stock: Number(m_safety_stock.value || 0), current_stock: Number(m_current_stock.value || 0),
    usage: m_usage.value, material_name_attr: m_material_name_attr.value, grade_attr: m_grade_attr.value,
    purchase_link: m_purchase_link.value,
    current_revision: m_current_revision.value, status: m_status.value,
    remark: m_remark.value
  };
  if (!payload.name) return showMsg("名称必填", true);
  if (!payload.category) return showMsg("分类必填", true);
  const url = id ? `/materials/${id}` : "/materials";
  const method = id ? "PUT" : "POST";
  const res = await fetch(url, { method, headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload) });
  if (!res.ok) {
    const e = await res.json();
    return showMsg(e.detail || "保存失败", true);
  }
  showMsg("保存成功");
  closeMaterialModal();
  loadMaterials();
}

async function disableMaterial(id) {
  if (!confirm("确认停用该物料？")) return;
  const res = await fetch(`/materials/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const e = await res.json();
    return showMsg(e.detail || "停用失败", true);
  }
  showMsg("已停用");
  loadMaterials();
}

async function removeMaterial(id) {
  if (!confirm("确认物理删除该物料？删除后不可恢复。")) return;
  const res = await fetch(`/materials/${id}/hard-delete`, { method: "DELETE" });
  if (!res.ok) {
    const e = await res.json();
    return showMsg(e.detail || "删除失败", true);
  }
  showMsg("已删除");
  loadMaterials();
}

async function importMaterialsFromFile(file) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch("/import/materials", { method: "POST", body: fd });
  let data = {};
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) {
    const d = data.detail;
    const msg = typeof d === "string" ? d : Array.isArray(d) ? JSON.stringify(d) : (res.statusText || "导入失败");
    return showMsg(msg, true);
  }
  let t = `导入完成：成功 ${data.created ?? 0} 条，失败 ${data.failed ?? 0} 条`;
  if (data.errors && data.errors.length) {
    const e0 = data.errors[0];
    t += `。示例：第 ${e0.row} 行 — ${e0.message}`;
    if (data.errors.length > 1) t += `（另 ${data.errors.length - 1} 条错误已省略）`;
  }
  showMsg(t, (data.failed || 0) > 0 && (data.created || 0) === 0);
  if (data.created > 0) loadMaterials();
}

document.getElementById("material-import-btn")?.addEventListener("click", () => {
  document.getElementById("material-import-file")?.click();
});
document.getElementById("material-import-file")?.addEventListener("change", async (ev) => {
  const input = ev.target;
  const f = input.files && input.files[0];
  input.value = "";
  if (!f) return;
  await importMaterialsFromFile(f);
});

["f_code","f_name","f_category","f_part_type","f_status"].forEach(id => {
  document.getElementById(id).addEventListener("input", renderTable);
  document.getElementById(id).addEventListener("change", renderTable);
});

document.getElementById("material-batch-toggle")?.addEventListener("click", () => {
  materialTableEditMode = true;
  updateMaterialBatchBar();
  renderTable();
});
document.getElementById("material-batch-cancel")?.addEventListener("click", () => {
  materialTableEditMode = false;
  updateMaterialBatchBar();
  renderTable();
});
document.getElementById("material-batch-save")?.addEventListener("click", () => {
  saveMaterialBatchEdits().catch((e) => showMsg(e.message || "保存失败", true));
});

loadCategories().then(() => loadSystemOptions().then(() => loadSuppliers().then(loadMaterials)));
applyViewModePreset();
updateMaterialBatchBar();
