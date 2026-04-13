const bomMsgEl = document.getElementById("msg");
const $ = (id) => document.getElementById(id);
const bomMsg = (m, err = false) => { if (bomMsgEl) { bomMsgEl.textContent = m; bomMsgEl.className = err ? "msg err" : "msg ok"; } };
const statusMap = { draft: "draft（草稿）", released: "released（已发布）", obsolete: "obsolete（作废）" };
const fmt3 = (v) => (v === null || v === undefined || v === "" ? "" : Number.isFinite(Number(v)) ? Number(v).toFixed(3) : String(v));

async function api(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let err = "请求失败";
    try { const e = await res.json(); err = e.detail || err; } catch (_) {}
    throw new Error(err);
  }
  return res.json();
}

if (document.getElementById("bom-tbody")) {
  let bomRows = [];
  let productRows = [];
  const bomTbody = $("bom-tbody");
  const qp = new URLSearchParams(window.location.search);
  const qpCode = qp.get("product_code") || "";
  if (qpCode && $("b_product_code")) $("b_product_code").value = qpCode;
  function renderBomProductOptions() {
    const sel = $("bo_product_code");
    if (!sel) return;
    sel.innerHTML = `<option value="">请选择产品编码</option>` + productRows.map(
      (p) => `<option value="${p.product_code}">${p.product_code}</option>`
    ).join("");
  }

  async function loadBomProducts() {
    productRows = await api("/products?product_type=self_made");
    renderBomProductOptions();
  }

  window.onSelectBomProduct = () => {
    const code = $("bo_product_code").value;
    const p = productRows.find(x => x.product_code === code);
    $("bo_product_name").value = p?.product_name || "";
  };

  async function loadBoms() {
    bomRows = await api("/boms");
    const code = ($("b_product_code").value || "").toLowerCase();
    const name = ($("b_product_name").value || "").toLowerCase();
    const filtered = bomRows.filter(b => (!code || (b.product_code || "").toLowerCase().includes(code)) && (!name || (b.product_name || "").toLowerCase().includes(name)));
    bomTbody.innerHTML = filtered.map(b => `<tr>
      <td>${b.product_code}</td><td>${b.product_name}</td><td>${b.bom_version}</td><td>${b.revision_note || ""}</td>
      <td><span class="tag ${b.status}">${statusMap[b.status] || b.status}</span></td><td>${b.is_current ? '<span class="tag current">当前</span>' : ''}</td>
      <td>${(b.created_at || "").replace("T"," ").slice(0,19)}</td><td>${(b.updated_at || "").replace("T"," ").slice(0,19)}</td>
      <td>
        <a class="btn sm" href="/ui/boms/${b.id}">明细</a>
        <button class="btn sm" onclick='editBom(${JSON.stringify(b)})'>编辑</button>
        <button class="btn sm primary" onclick='setCurrentBom(${b.id})'>设为当前版本</button>
        <button class="btn sm" onclick='deleteBom(${b.id})'>删除</button>
      </td>
    </tr>`).join("");
    const tot = document.getElementById("bom-record-total");
    if (tot) tot.textContent = `共 ${filtered.length} 条记录`;
  }
  window.openBomModal = () => {
    $("bom-modal").classList.remove("hidden");
    if (!$("bo_product_code").value) onSelectBomProduct();
  };
  window.closeBomModal = () => { $("bom-modal").classList.add("hidden"); $("bom-form").reset(); $("bo_id").value = ""; };
  window.editBom = (b) => {
    openBomModal(); $("bom-title").textContent = "编辑 BOM";
    ["id","bom_version","revision_note","status"].forEach(k => { const el = $("bo_"+k); if (el) el.value = b[k] ?? ""; });
    if (!$("bo_product_code").querySelector(`option[value="${b.product_code}"]`)) {
      const op = document.createElement("option");
      op.value = b.product_code;
      op.textContent = b.product_code;
      $("bo_product_code").appendChild(op);
    }
    $("bo_product_code").value = b.product_code ?? "";
    onSelectBomProduct();
    if (!$("bo_product_name").value) $("bo_product_name").value = b.product_name ?? "";
    $("bo_is_current").value = String(b.is_current);
  };
  window.saveBom = async () => {
    try {
      const id = $("bo_id").value;
      const payload = {
        product_code: $("bo_product_code").value,
        product_name: $("bo_product_name").value,
        bom_version: $("bo_bom_version").value,
        revision_note: $("bo_revision_note").value,
        status: $("bo_status").value,
        is_current: $("bo_is_current").value === "true",
      };
      if (!payload.product_code) throw new Error("请选择产品编码");
      await api(id ? `/boms/${id}` : "/boms", { method: id ? "PUT" : "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload) });
      closeBomModal(); bomMsg("保存成功"); loadBoms();
    } catch (e) { bomMsg(e.message, true); }
  };
  window.setCurrentBom = async (id) => { try { await api(`/boms/${id}/set-current`, {method:"POST"}); bomMsg("已设为当前BOM"); loadBoms(); } catch (e) { bomMsg(e.message, true); } };
  window.deleteBom = async (id) => {
    const pwd = prompt("请输入删除密码：");
    if (pwd === null) return;
    if (!pwd.trim()) return bomMsg("未输入密码", true);
    if (!confirm("确认永久删除该BOM及其明细？此操作不可恢复。")) return;
    try {
      await api(`/boms/${id}`, {
        method: "DELETE",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ password: pwd.trim() }),
      });
      bomMsg("删除成功");
      loadBoms();
    } catch (e) { bomMsg(e.message, true); }
  };
  ["b_product_code","b_product_name"].forEach(i => $(i).addEventListener("input", loadBoms));
  loadBomProducts().then(loadBoms);
}

if ($("item-tbody")) {
  const bomId = Number($("bom_id").value);
  const headerEl = $("bom-header-card");
  const tbody = $("item-tbody");
  /** 避免备注/名称等含 </td> 或引号时撑破表格列 */
  const escCell = (s) => {
    if (s == null || s === "") return "";
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  };
  let bomDetailItemsById = {};
  let materials = [];
  let categories = [];
  let existingMaterialIds = new Set();
  let nextLineStart = 1;
  let modalBaseLineNo = 1;
  const specDraw = (m) => [(m.spec || "").trim(), (m.drawing_no || "").trim()].filter(Boolean).join(" / ");
  const usageFromMat = (m) => {
    const u = m && m.usage != null ? String(m.usage).trim() : "";
    return u || "—";
  };

  function materialOptions(selectedId) {
    return materials.map(m => `<option value="${m.id}" ${Number(selectedId) === Number(m.id) ? "selected" : ""}>${m.code} | ${m.name}</option>`).join("");
  }
  function renderPickCategoryOptions() {
    const sel = $("bi_f_category");
    if (!sel) return;
    sel.innerHTML = `<option value="">全部物料分类</option>` + categories.map(c => `<option value="${c.name}">${c.name}</option>`).join("");
  }
  function renderPickMaterials() {
    const code = ($("bi_f_code")?.value || "").toLowerCase();
    const name = ($("bi_f_name")?.value || "").toLowerCase();
    const category = ($("bi_f_category")?.value || "").toLowerCase();
    const rows = materials.filter(m =>
      (!code || (m.code || "").toLowerCase().includes(code)) &&
      (!name || (m.name || "").toLowerCase().includes(name)) &&
      (!category || (m.category || "").toLowerCase().includes(category))
    );
    const picked = new Set([...$("bi_lines_tbody").querySelectorAll(".bi-material-id")].map(x => Number(x.value)));
    $("bi_material_pick_tbody").innerHTML = rows.map(m => `<tr>
      <td><input type="checkbox" class="bi-pick-chk" data-id="${m.id}" ${picked.has(m.id) || existingMaterialIds.has(m.id) ? "disabled" : ""}></td>
      <td>${m.code || ""}</td><td>${m.name || ""}</td><td>${m.category || ""}</td><td>${specDraw(m)}</td><td>${m.unit || ""}</td><td>${fmt3(m.unit_price)}</td>
    </tr>`).join("");
  }
  function itemLineHtml(idx, row = {}) {
    const mForRow = row.material_id != null ? materials.find(x => x.id === Number(row.material_id)) : null;
    const specFromApi = row.spec_drawing != null && String(row.spec_drawing).trim() !== "" ? String(row.spec_drawing) : "";
    const specInit = specFromApi || (mForRow ? specDraw(mForRow) : "");
    const usageInit =
      row.usage != null && String(row.usage).trim() !== ""
        ? String(row.usage)
        : mForRow
          ? usageFromMat(mForRow)
          : "—";
    return `<tr data-idx="${idx}">
      <td><input type="number" class="bi-line-no" value="${row.line_no ?? (modalBaseLineNo + idx)}" min="1" style="width:64px" readonly></td>
      <td><select class="bi-material-id">${materialOptions(row.material_id)}</select></td>
      <td><input class="bi-material-name" value="${row.material_name ?? ""}" readonly></td>
      <td><input class="bi-spec-drawing" value="${specInit}" readonly></td>
      <td><input class="bi-usage" value="${usageInit}" readonly></td>
      <td><input type="number" class="bi-qty" value="${row.qty ?? 1}" step="0.0001" min="0"></td>
      <td><input type="number" class="bi-price" value="${row.unit_price ?? 0}" step="0.01" min="0" readonly></td>
      <td><input type="number" class="bi-total" value="${row.total_price ?? 0}" step="0.01" readonly></td>
      <td><input class="bi-remark" value="${row.remark ?? ""}" readonly></td>
      <td><button type="button" class="btn sm bi-del">删</button></td>
    </tr>`;
  }
  function applyMaterialToLine(tr) {
    const mid = Number(tr.querySelector(".bi-material-id")?.value);
    const m = materials.find(x => x.id === mid);
    if (!m) return;
    tr.querySelector(".bi-material-name").value = m.name || "";
    const specEl = tr.querySelector(".bi-spec-drawing");
    if (specEl) specEl.value = specDraw(m);
    const usageEl = tr.querySelector(".bi-usage");
    if (usageEl) usageEl.value = usageFromMat(m);
    tr.querySelector(".bi-price").value = Number(m.unit_price || 0);
    tr.querySelector(".bi-remark").value = m.remark || "";
    recalcLine(tr);
  }
  function clearDupMarking() {
    $("bi_lines_tbody").querySelectorAll(".bi-material-id").forEach((el) => {
      el.style.borderColor = "";
      el.title = "";
    });
  }
  function markDup(tr, msg) {
    const sel = tr.querySelector(".bi-material-id");
    if (!sel) return;
    sel.style.borderColor = "#dc2626";
    sel.title = msg;
  }
  function reseqItemLines() {
    $("bi_lines_tbody").querySelectorAll("tr").forEach((tr, i) => {
      tr.querySelector(".bi-line-no").value = modalBaseLineNo + i;
    });
  }
  function recalcLine(tr) {
    const q = Number(tr.querySelector(".bi-qty")?.value || 0);
    const p = Number(tr.querySelector(".bi-price")?.value || 0);
    tr.querySelector(".bi-total").value = (q * p).toFixed(3);
  }
  function bindItemLineEvents() {
    const tb = $("bi_lines_tbody");
    tb.addEventListener("change", (e) => {
      if (e.target.matches(".bi-material-id")) applyMaterialToLine(e.target.closest("tr"));
    });
    tb.addEventListener("input", (e) => {
      if (e.target.matches(".bi-qty")) recalcLine(e.target.closest("tr"));
    });
    tb.addEventListener("click", (e) => {
      const btn = e.target.closest(".bi-del");
      if (!btn) return;
      const tr = btn.closest("tr");
      if (tr && tb.querySelectorAll("tr").length > 1) tr.remove();
      reseqItemLines();
    });
  }
  function addItemLine(row = {}) {
    const tb = $("bi_lines_tbody");
    const idx = tb.querySelectorAll("tr").length;
    tb.insertAdjacentHTML("beforeend", itemLineHtml(idx, row));
    applyMaterialToLine(tb.querySelector("tr:last-child"));
    renderPickMaterials();
  }
  function collectItemLines() {
    const rows = [...$("bi_lines_tbody").querySelectorAll("tr")];
    if (!rows.length) throw new Error("至少一行明细");
    clearDupMarking();
    const selectedInModal = new Map(); // material_id -> line_no
    return rows.map((tr, i) => {
      const material_id = Number(tr.querySelector(".bi-material-id")?.value || 0);
      const qty = Number(tr.querySelector(".bi-qty")?.value || 0);
      if (!material_id) throw new Error(`第 ${i + 1} 行请选择物料`);
      if (qty <= 0) throw new Error(`第 ${i + 1} 行数量须大于 0`);
      const line_no = Number(tr.querySelector(".bi-line-no")?.value || (i + 1));
      const editingId = Number($("bi_id").value || 0);
      const isEditingCurrent = editingId > 0 && i === 0;
      if (!isEditingCurrent && existingMaterialIds.has(material_id)) {
        markDup(tr, "该物料已存在于当前BOM中");
        throw new Error(`第 ${line_no} 行物料重复：已存在于当前BOM`);
      }
      if (selectedInModal.has(material_id)) {
        const firstLine = selectedInModal.get(material_id);
        markDup(tr, "该物料在本次新增中重复");
        throw new Error(`第 ${line_no} 行物料重复：与第 ${firstLine} 行相同`);
      }
      selectedInModal.set(material_id, line_no);
      return {
      line_no,
      material_id,
      qty,
      unit_price: Number(tr.querySelector(".bi-price")?.value || 0),
      total_price: null,
      remark: tr.querySelector(".bi-remark")?.value || "",
      };
    });
  }
  async function loadMaterialsForSelect() {
    materials = await api("/materials");
    categories = await api("/material-categories");
    categories = categories.filter(x => x.is_active);
    renderPickCategoryOptions();
    renderPickMaterials();
  }
  async function loadBomDetail() {
    const d = await api(`/boms/${bomId}`);
    const h = d.header;
    headerEl.innerHTML = `<h3>${h.product_code} - ${h.product_name} (${h.bom_version})</h3><p>状态：<span class="tag ${h.status}">${statusMap[h.status] || h.status}</span> ${h.is_current ? '<span class="tag current">当前</span>' : ''} | 说明：${h.revision_note || ''}</p>`;
    $("total-cost").textContent = fmt3(d.total_cost);
    bomDetailItemsById = Object.fromEntries((d.items || []).map((it) => [Number(it.id), it]));
    tbody.innerHTML = (d.items || []).map((i) => `<tr>
      <td>${escCell(i.line_no)}</td>
      <td>${escCell(i.material_code)}</td>
      <td>${escCell(i.material_name)}</td>
      <td>${escCell(i.spec_drawing)}</td>
      <td>${escCell(i.usage)}</td>
      <td>${escCell(i.material_name_attr)}</td>
      <td>${escCell(i.grade_attr)}</td>
      <td>${fmt3(i.qty)}</td>
      <td>${fmt3(i.unit_price)}</td>
      <td>${fmt3(i.total_price)}</td>
      <td>${escCell(i.remark)}</td>
      <td><button type="button" class="btn sm" data-bom-edit="${i.id}">编辑</button> <button type="button" class="btn sm" data-bom-del="${i.id}">删除</button></td>
    </tr>`).join("");
    const itot = document.getElementById("bom-items-total");
    if (itot) itot.textContent = `共 ${d.items.length} 条记录`;
    existingMaterialIds = new Set((d.items || []).map((x) => Number(x.material_id)).filter((x) => Number.isFinite(x)));
    const maxLine = d.items.reduce((m, i) => Math.max(m, Number(i.line_no || 0)), 0);
    nextLineStart = Math.max(1, maxLine + 1);
  }
  window.openBomItemModal = () => {
    $("item-modal").classList.remove("hidden");
    $("item-title").textContent = "新增 BOM 明细";
    $("bi_id").value = "";
    $("bi_lines_tbody").innerHTML = "";
    modalBaseLineNo = nextLineStart;
    addItemLine({});
    renderPickMaterials();
  };
  window.closeBomItemModal = () => {
    $("item-modal").classList.add("hidden");
    $("bi_id").value = "";
    $("bi_lines_tbody").innerHTML = "";
  };
  window.editBomItem = (i) => {
    $("item-modal").classList.remove("hidden");
    $("item-title").textContent = "编辑 BOM 明细";
    $("bi_id").value = i.id;
    $("bi_lines_tbody").innerHTML = "";
    modalBaseLineNo = Number(i.line_no || 1);
    addItemLine(i);
    renderPickMaterials();
  };
  window.saveBomItem = async () => {
    try {
      const id = $("bi_id").value;
      const rows = collectItemLines();
      if (id) {
        if (rows.length !== 1) throw new Error("编辑模式仅允许一行");
        const payload = rows[0];
        await api(`/bom-items/${id}`, { method: "PUT", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload) });
      } else {
        for (const payload of rows) {
          await api(`/boms/${bomId}/items`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(payload) });
        }
      }
      await loadBomDetail();
      bomMsg("保存成功");
      closeBomItemModal();
    } catch (e) { bomMsg(e.message, true); }
  };
  window.deleteBomItem = async (id) => { if (!confirm("确认删除?")) return; try { await api(`/bom-items/${id}`, {method:"DELETE"}); bomMsg("删除成功"); loadBomDetail(); } catch (e) { bomMsg(e.message, true); } };
  tbody.addEventListener("click", (e) => {
    const ed = e.target.closest("[data-bom-edit]");
    if (ed) {
      const row = bomDetailItemsById[Number(ed.dataset.bomEdit)];
      if (row) window.editBomItem(row);
      return;
    }
    const del = e.target.closest("[data-bom-del]");
    if (del) window.deleteBomItem(Number(del.dataset.bomDel));
  });
  $("bi_add_line").addEventListener("click", () => addItemLine({}));
  $("bi_add_checked").addEventListener("click", () => {
    const ids = [...document.querySelectorAll(".bi-pick-chk:checked")].map(x => Number(x.dataset.id));
    if (!ids.length) return bomMsg("请先勾选物料");
    const existing = new Set([...$("bi_lines_tbody").querySelectorAll(".bi-material-id")].map(x => Number(x.value)));
    ids.forEach((id) => {
      if (existing.has(id) || existingMaterialIds.has(id)) return;
      const m = materials.find(x => x.id === id);
      if (!m) return;
      addItemLine({
        material_id: m.id,
        material_code: m.code,
        material_name: m.name,
        qty: 1,
        unit_price: Number(m.unit_price || 0),
        remark: m.remark || "",
      });
      existing.add(id);
    });
    renderPickMaterials();
  });
  ["bi_f_code", "bi_f_name"].forEach((id) => $(id)?.addEventListener("input", renderPickMaterials));
  $("bi_f_category")?.addEventListener("change", renderPickMaterials);
  bindItemLineEvents();
  loadMaterialsForSelect();
  loadBomDetail();
}
