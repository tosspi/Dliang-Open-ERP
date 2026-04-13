const revMsg = (m, err = false) => {
  const el = document.getElementById("msg");
  el.textContent = m;
  el.className = err ? "msg err" : "msg ok";
};

const partTypeMap = { standard: "标准件", custom: "自制件", assembly: "装配件" };
const statusMap = { draft: "草稿", released: "已发布", obsolete: "已停用" };

let flatRows = [];
let nonstandardMaterials = [];
let filterDebounceTimer = null;

function escAttr(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;");
}

function fileLink(revisionId, slot, hasFile) {
  if (!hasFile) return "—";
  const u = `/revisions/${revisionId}/drawing-file?slot=${slot}`;
  return `<a href="${u}" target="_blank" rel="noopener">下载</a>`;
}

function buildQuery() {
  const p = new URLSearchParams();
  const c = document.getElementById("rev_f_code")?.value?.trim();
  const n = document.getElementById("rev_f_name")?.value?.trim();
  const cat = document.getElementById("rev_f_category")?.value?.trim();
  const rev = document.getElementById("rev_f_revision")?.value?.trim();
  const st = document.getElementById("rev_f_status")?.value?.trim();
  const cur = document.getElementById("rev_f_current_only")?.checked;
  const focus = document.getElementById("focus_material_id")?.value?.trim();
  if (c) p.set("material_code", c);
  if (n) p.set("material_name", n);
  if (cat) p.set("category", cat);
  if (rev) p.set("revision", rev);
  if (st) p.set("status", st);
  if (cur) p.set("current_only", "true");
  if (focus && !Number.isNaN(Number(focus))) p.set("material_id", focus);
  return p.toString();
}

async function loadFlatList() {
  const qs = buildQuery();
  const res = await fetch(`/revisions/flat${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    revMsg("加载版本列表失败", true);
    flatRows = [];
    renderTable([]);
    return;
  }
  flatRows = await res.json();
  renderTable(flatRows);
  revMsg("");
}

function renderTable(rows) {
  const tb = document.getElementById("rev-tbody");
  const tot = document.getElementById("rev-record-total");
  if (tot) tot.textContent = `共 ${rows.length} 条记录`;
  tb.innerHTML = rows
    .map(
      (r) => `<tr>
    <td>${escAttr(r.material_code)}</td>
    <td title="${escAttr(r.material_item_name)}">${escAttr(r.material_item_name)}</td>
    <td>${partTypeMap[r.material_part_type] || r.material_part_type}</td>
    <td>${escAttr(r.material_category || "")}</td>
    <td>${escAttr(r.revision)}</td>
    <td>${escAttr(r.drawing_no || "")}</td>
    <td>${fileLink(r.id, "pdf", !!r.file_path_pdf)}</td>
    <td>${fileLink(r.id, "model", !!r.file_path_model)}</td>
    <td><span class="tag ${r.status}">${statusMap[r.status] || r.status}</span></td>
    <td>${r.is_current ? '<span class="tag current">当前</span>' : "—"}</td>
    <td style="max-width:100px;word-break:break-all;font-size:12px;">${escAttr(r.purpose || "")}</td>
    <td style="max-width:120px;word-break:break-all;font-size:12px;">${escAttr(r.change_note || "")}</td>
    <td>${(r.created_at || "").replace("T", " ").slice(0, 19)}</td>
    <td style="white-space:normal;max-width:200px;">
      <button type="button" class="btn sm" data-act="edit" data-id="${r.id}">编辑</button>
      <button type="button" class="btn sm primary" data-act="current" data-id="${r.id}">设为当前</button>
      <button type="button" class="btn sm" data-act="upload" data-id="${r.id}">上传图纸</button>
      <a class="btn sm" href="/export/revisions/${r.material_id}">导出物料版本</a>
    </td>
  </tr>`
    )
    .join("");
}

function scheduleReload() {
  clearTimeout(filterDebounceTimer);
  filterDebounceTimer = setTimeout(() => loadFlatList(), 280);
}

async function loadCategories() {
  const sel = document.getElementById("rev_f_category");
  if (!sel) return;
  try {
    const res = await fetch("/material-categories");
    if (!res.ok) return;
    const rows = await res.json();
    const cur = sel.value;
    sel.innerHTML = '<option value="">全部分类</option>';
    for (const c of rows) {
      if (!c.is_active) continue;
      const o = document.createElement("option");
      o.value = c.name;
      o.textContent = c.name;
      sel.appendChild(o);
    }
    sel.value = cur || "";
  } catch (_) {}
}

async function loadNonstandardMaterials() {
  const res = await fetch("/materials");
  if (!res.ok) {
    nonstandardMaterials = [];
    return;
  }
  const all = await res.json();
  nonstandardMaterials = all.filter((m) => m.part_type === "custom" || m.part_type === "assembly");
  nonstandardMaterials.sort((a, b) => String(a.code || "").localeCompare(String(b.code || ""), "zh-CN"));
  populateMaterialSelect();
}

function populateMaterialSelect() {
  const sel = document.getElementById("r_material_id");
  if (!sel) return;
  const cur = sel.value;
  sel.innerHTML = "";
  const o0 = document.createElement("option");
  o0.value = "";
  o0.textContent = "— 请选择物料 —";
  sel.appendChild(o0);
  for (const m of nonstandardMaterials) {
    const o = document.createElement("option");
    o.value = String(m.id);
    o.textContent = `${m.code} · ${m.name}`;
    sel.appendChild(o);
  }
  const focus = document.getElementById("focus_material_id")?.value?.trim();
  if (focus && nonstandardMaterials.some((m) => String(m.id) === focus)) sel.value = focus;
  else if (cur && [...sel.options].some((o) => o.value === cur)) sel.value = cur;
}

function clearRevisionUploadInputs() {
  const p = document.getElementById("r_upload_pdf");
  const m = document.getElementById("r_upload_model");
  if (p) p.value = "";
  if (m) m.value = "";
}

function openRevisionModal(edit, row) {
  clearRevisionUploadInputs();
  document.getElementById("rev-modal").classList.remove("hidden");
  const matRow = document.getElementById("r_material_row");
  const midSel = document.getElementById("r_material_id");
  if (edit && row) {
    document.getElementById("rev-title").textContent = "编辑版本";
    document.getElementById("r_id").value = String(row.id);
    matRow.classList.add("hidden");
    midSel.removeAttribute("required");
    midSel.disabled = true;
    const keys = [
      "revision",
      "drawing_no",
      "file_path_pdf",
      "file_path_model",
      "status",
      "purpose",
      "material_name",
      "standard",
      "grade",
      "change_note",
    ];
    keys.forEach((k) => {
      const el = document.getElementById(`r_${k}`);
      if (el) el.value = row[k] ?? "";
    });
    document.getElementById("r_is_current").value = String(!!row.is_current);
  } else {
    document.getElementById("rev-title").textContent = "新增版本";
    document.getElementById("r_id").value = "";
    matRow.classList.remove("hidden");
    midSel.setAttribute("required", "required");
    midSel.disabled = false;
    document.getElementById("rev-form").reset();
    document.getElementById("r_id").value = "";
    populateMaterialSelect();
  }
}

function closeRevisionModal() {
  document.getElementById("rev-modal").classList.add("hidden");
  document.getElementById("r_material_id").disabled = false;
}

function openUploadModal(revisionId) {
  document.getElementById("ru_revision_id").value = String(revisionId);
  document.getElementById("ru_slot").value = "pdf";
  document.getElementById("ru_file").value = "";
  document.getElementById("rev-upload-modal").classList.remove("hidden");
}

function closeUploadModal() {
  document.getElementById("rev-upload-modal").classList.add("hidden");
}

async function uploadRevisionDrawing(revisionId, slot, file) {
  const fd = new FormData();
  fd.append("slot", slot);
  fd.append("file", file);
  const res = await fetch(`/revisions/${revisionId}/upload-drawing`, { method: "POST", body: fd });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    const d = e.detail;
    throw new Error(typeof d === "string" ? d : JSON.stringify(d) || "上传失败");
  }
}

async function saveRevision() {
  const rid = document.getElementById("r_id").value.trim();
  const midSel = document.getElementById("r_material_id");
  const mid = Number(midSel.value);
  const payload = {
    revision: document.getElementById("r_revision").value.trim(),
    drawing_no: document.getElementById("r_drawing_no").value.trim() || null,
    file_path_pdf: document.getElementById("r_file_path_pdf").value.trim() || null,
    file_path_model: document.getElementById("r_file_path_model").value.trim() || null,
    status: document.getElementById("r_status").value,
    is_current: document.getElementById("r_is_current").value === "true",
    purpose: document.getElementById("r_purpose").value.trim() || null,
    material_name: document.getElementById("r_material_name").value.trim() || null,
    standard: document.getElementById("r_standard").value.trim() || null,
    grade: document.getElementById("r_grade").value.trim() || null,
    change_note: document.getElementById("r_change_note").value.trim() || null,
  };
  if (!payload.revision) return revMsg("请填写版本号", true);
  let url;
  let method;
  if (rid) {
    url = `/revisions/${rid}`;
    method = "PUT";
  } else {
    if (!Number.isFinite(mid)) return revMsg("请选择所属物料", true);
    url = `/materials/${mid}/revisions`;
    method = "POST";
  }
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return revMsg(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail) || "保存失败", true);
  }
  const saved = await res.json();
  const revId = saved.id != null ? saved.id : Number(rid);
  const fPdf = document.getElementById("r_upload_pdf");
  const fModel = document.getElementById("r_upload_model");
  let uploadErr = null;
  try {
    if (fPdf && fPdf.files && fPdf.files[0]) await uploadRevisionDrawing(revId, "pdf", fPdf.files[0]);
    if (fModel && fModel.files && fModel.files[0]) await uploadRevisionDrawing(revId, "model", fModel.files[0]);
  } catch (err) {
    uploadErr = err.message || String(err);
  }
  closeRevisionModal();
  if (uploadErr) revMsg(`版本已保存，但文件上传失败：${uploadErr}`, true);
  else revMsg("保存成功");
  loadFlatList();
}

async function setCurrentRevision(id) {
  const res = await fetch(`/revisions/${id}/set-current`, { method: "POST" });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return revMsg(typeof e.detail === "string" ? e.detail : "设为当前失败", true);
  }
  revMsg("已设为当前版本");
  loadFlatList();
}

async function submitUpload() {
  const rid = document.getElementById("ru_revision_id").value.trim();
  const slot = document.getElementById("ru_slot").value;
  const fileEl = document.getElementById("ru_file");
  if (!fileEl.files || !fileEl.files[0]) return revMsg("请选择文件", true);
  try {
    await uploadRevisionDrawing(rid, slot, fileEl.files[0]);
  } catch (e) {
    return revMsg(e.message || String(e), true);
  }
  closeUploadModal();
  revMsg("上传成功");
  loadFlatList();
}

document.getElementById("rev-tbody").addEventListener("click", (e) => {
  const b = e.target.closest("[data-act]");
  if (!b) return;
  const id = Number(b.getAttribute("data-id"));
  const act = b.getAttribute("data-act");
  if (act === "edit") {
    const row = flatRows.find((x) => x.id === id);
    if (row) openRevisionModal(true, row);
  } else if (act === "current") setCurrentRevision(id);
  else if (act === "upload") openUploadModal(id);
});

document.getElementById("rev_btn_add").addEventListener("click", () => openRevisionModal(false, null));
document.getElementById("rev_btn_close_modal").addEventListener("click", closeRevisionModal);
document.getElementById("rev_btn_save").addEventListener("click", saveRevision);

document.getElementById("ru_cancel").addEventListener("click", closeUploadModal);
document.getElementById("ru_submit").addEventListener("click", submitUpload);

["rev_f_code", "rev_f_name", "rev_f_category", "rev_f_revision", "rev_f_status"].forEach((id) => {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener("change", scheduleReload);
  if (el.tagName !== "SELECT") el.addEventListener("input", scheduleReload);
});
const curOnly = document.getElementById("rev_f_current_only");
if (curOnly) curOnly.addEventListener("change", scheduleReload);

(async function init() {
  await loadCategories();
  await loadNonstandardMaterials();
  await loadFlatList();
})();
