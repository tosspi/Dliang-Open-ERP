const fmt3 = (v) =>
  v === null || v === undefined || v === ""
    ? ""
    : Number.isFinite(Number(v))
      ? Number(v).toFixed(3)
      : String(v);

const msgEl = document.getElementById("msg");
const showMsg = (m, err = false) => {
  msgEl.textContent = m;
  msgEl.className = err ? "msg err" : "msg ok";
};

let allBoms = [];
let currentPlanId = null;
let currentPlanNo = "";

function todayISODate() {
  const d = new Date();
  const z = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
}

function statusLabel(st) {
  if (st === "confirmed") return '<span class="tag released">已确认</span>';
  if (st === "closed") return '<span class="tag obsolete">已关闭</span>';
  return '<span class="tag">草稿</span>';
}

function bomOptionsHtml() {
  return allBoms
    .map(
      (b) =>
        `<option value="${b.id}">${b.product_code} | ${b.product_name} | ${b.bom_version}${b.is_current ? " (current)" : ""}</option>`
    )
    .join("");
}

function lineRowHtml() {
  return `<tr>
    <td><select class="pp-line-bom" style="min-width:220px">${bomOptionsHtml()}</select></td>
    <td><input type="number" class="pp-line-qty" min="0" step="0.0001" value="1" style="width:100px"></td>
    <td><input class="pp-line-rmk" placeholder="选填" style="width:120px"></td>
    <td><button type="button" class="btn sm pp-del-line">删</button></td>
  </tr>`;
}

async function loadBoms() {
  const res = await fetch("/boms");
  if (!res.ok) return;
  allBoms = await res.json();
}

function collectLines() {
  const tbody = document.getElementById("pp_lines_tbody");
  const rows = [...tbody.querySelectorAll("tr")];
  const lines = [];
  rows.forEach((tr, i) => {
    const bomId = Number(tr.querySelector(".pp-line-bom")?.value);
    const q = Number(tr.querySelector(".pp-line-qty")?.value);
    const rmk = tr.querySelector(".pp-line-rmk")?.value?.trim() || null;
    if (!bomId || !Number.isFinite(q) || q <= 0) throw new Error(`第 ${i + 1} 行：请选择 BOM 且计划产量须大于 0`);
    lines.push({ bom_id: bomId, planned_qty: q, remark: rmk });
  });
  return lines;
}

function showProcurementPanel(planId, planNo) {
  currentPlanId = planId;
  currentPlanNo = planNo || "";
  const panel = document.getElementById("pp-procurement-panel");
  panel.classList.remove("hidden");
  document.getElementById("pp-proc-label").textContent = planNo ? `当前：${planNo}（#${planId}）` : "";
  document.getElementById("pp-s-tbody").innerHTML = "";
  document.getElementById("pp-supplier-groups").innerHTML = "";
  document.getElementById("pp-s-records").textContent = "共 0 条";
  document.getElementById("pp-s-groups").textContent = "共 0 组";
  document.getElementById("pp-s-total").textContent = "0.000";
}

function clearShortageDisplay() {
  document.getElementById("pp-s-tbody").innerHTML = "";
  document.getElementById("pp-supplier-groups").innerHTML = "";
  document.getElementById("pp-s-records").textContent = "共 0 条";
  document.getElementById("pp-s-groups").textContent = "共 0 组";
  document.getElementById("pp-s-total").textContent = "0.000";
}

function renderShortage(data) {
  const tbody = document.getElementById("pp-s-tbody");
  if (!data.shortage_list.length) {
    tbody.innerHTML = `<tr><td colspan="13">无需采购或无数据</td></tr>`;
    document.getElementById("pp-s-records").textContent = "共 0 条";
    document.getElementById("pp-s-groups").textContent = "共 0 组";
  } else {
    tbody.innerHTML = data.shortage_list
      .map(
        (i) => `<tr>
      <td>${i.material_code}</td><td>${i.material_name}</td><td>${i.spec_drawing || ""}</td><td>${i.default_supplier || ""}</td><td>${fmt3(i.unit_usage)}</td>
      <td>${fmt3(i.total_required_qty)}</td><td>${fmt3(i.current_stock)}</td><td>${fmt3(i.safety_stock)}</td><td>${fmt3(i.safety_shortage_qty)}</td>
      <td>${fmt3(i.clear_shortage_qty)}</td>
      <td>${fmt3(i.suggested_purchase_qty)}</td><td>${fmt3(i.unit_price)}</td><td>${fmt3(i.estimated_amount)}</td>
    </tr>`
      )
      .join("");
    document.getElementById("pp-s-records").textContent = `共 ${data.shortage_list.length} 条`;
    document.getElementById("pp-s-groups").textContent = `共 ${data.grouped_by_supplier.length} 组`;
  }
  document.getElementById("pp-s-total").textContent = fmt3(data.total_estimated_cost);
  document.getElementById("pp-supplier-groups").innerHTML = (data.grouped_by_supplier || [])
    .map(
      (g) => `
    <div class="card" style="margin-top:8px;">
      <h4 style="margin:0 0 6px;">${g.supplier} — 小计 ${fmt3(g.supplier_total_amount)}</h4>
      <p class="muted-hint" style="margin:0;font-size:13px;">${g.items.map((i) => `${i.material_code}(${fmt3(i.suggested_purchase_qty)})`).join("，")}</p>
    </div>
  `
    )
    .join("");
}

async function loadList() {
  const res = await fetch("/production-plans");
  if (!res.ok) return showMsg("加载生产计划失败", true);
  const rows = await res.json();
  const tb = document.getElementById("pp-tbody");
  tb.innerHTML = rows
    .map(
      (r) => `<tr>
    <td>${r.plan_no}</td>
    <td>${String(r.plan_date).slice(0, 10)}</td>
    <td>${statusLabel(r.status)}</td>
    <td>${(r.lines || []).length}</td>
    <td>
      <button type="button" class="btn sm" data-edit="${r.id}">编辑</button>
      <button type="button" class="btn sm" data-proc="${r.id}" data-no="${r.plan_no}">缺料/采购</button>
    </td>
  </tr>`
    )
    .join("");
  const tot = document.getElementById("pp-list-total");
  if (tot) tot.textContent = `共 ${rows.length} 条`;
}

function openModal() {
  document.getElementById("pp-modal").classList.remove("hidden");
}
function closeModal() {
  document.getElementById("pp-modal").classList.add("hidden");
}

function resetFormNew() {
  document.getElementById("pp_id").value = "";
  document.getElementById("pp-modal-title").textContent = "新建生产计划";
  document.getElementById("pp_plan_date").value = todayISODate();
  document.getElementById("pp_remark").value = "";
  const tbody = document.getElementById("pp_lines_tbody");
  tbody.innerHTML = lineRowHtml();
}

async function openEdit(id) {
  const res = await fetch(`/production-plans/${id}`);
  if (!res.ok) return showMsg("加载计划失败", true);
  const r = await res.json();
  document.getElementById("pp_id").value = String(r.id);
  document.getElementById("pp-modal-title").textContent = `编辑 ${r.plan_no}`;
  document.getElementById("pp_plan_date").value = String(r.plan_date).slice(0, 10);
  document.getElementById("pp_remark").value = r.remark || "";
  const tbody = document.getElementById("pp_lines_tbody");
  tbody.innerHTML = "";
  const lines = r.lines || [];
  if (!lines.length) {
    tbody.innerHTML = lineRowHtml();
  } else {
    lines.forEach((ln) => {
      tbody.insertAdjacentHTML("beforeend", lineRowHtml());
      const tr = tbody.querySelector("tr:last-child");
      tr.querySelector(".pp-line-bom").value = String(ln.bom_id);
      tr.querySelector(".pp-line-qty").value = ln.planned_qty;
      tr.querySelector(".pp-line-rmk").value = ln.remark || "";
    });
  }
  const isDraft = r.status === "draft";
  document.getElementById("pp_save").style.display = isDraft ? "" : "none";
  document.getElementById("pp_add_line").style.display = isDraft ? "" : "none";
  tbody.querySelectorAll(".pp-del-line").forEach((b) => (b.style.display = isDraft ? "" : "none"));
  tbody.querySelectorAll("input, select").forEach((el) => (el.disabled = !isDraft));
  document.getElementById("pp_plan_date").disabled = !isDraft;
  document.getElementById("pp_remark").disabled = !isDraft;
  document.getElementById("pp_confirm").style.display = r.status === "draft" ? "" : "none";
  openModal();
}

document.getElementById("pp_new").addEventListener("click", () => {
  resetFormNew();
  document.getElementById("pp_save").style.display = "";
  document.getElementById("pp_add_line").style.display = "";
  document.getElementById("pp_lines_tbody").querySelectorAll("input, select").forEach((el) => (el.disabled = false));
  document.getElementById("pp_plan_date").disabled = false;
  document.getElementById("pp_remark").disabled = false;
  document.getElementById("pp_confirm").style.display = "";
  openModal();
});

document.getElementById("pp_close").addEventListener("click", closeModal);

document.getElementById("pp_add_line").addEventListener("click", () => {
  document.getElementById("pp_lines_tbody").insertAdjacentHTML("beforeend", lineRowHtml());
});

document.getElementById("pp_lines_tbody").addEventListener("click", (e) => {
  const btn = e.target.closest(".pp-del-line");
  if (!btn) return;
  const tr = btn.closest("tr");
  const tbody = document.getElementById("pp_lines_tbody");
  if (tr && tbody.querySelectorAll("tr").length > 1) tr.remove();
});

document.getElementById("pp_save").addEventListener("click", async () => {
  let lines;
  try {
    lines = collectLines();
  } catch (err) {
    return showMsg(err.message || "明细有误", true);
  }
  if (!lines.length) return showMsg("至少一行计划明细", true);
  const pd = document.getElementById("pp_plan_date").value;
  const payload = {
    plan_date: pd ? new Date(pd + "T12:00:00").toISOString() : undefined,
    remark: document.getElementById("pp_remark").value.trim() || null,
    lines,
  };
  const id = document.getElementById("pp_id").value;
  const url = id ? `/production-plans/${id}` : "/production-plans";
  const method = id ? "PUT" : "POST";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail) || "保存失败", true);
  }
  const saved = await res.json();
  showMsg("保存成功");
  closeModal();
  loadList();
  showProcurementPanel(saved.id, saved.plan_no);
  clearShortageDisplay();
});

document.getElementById("pp_confirm").addEventListener("click", async () => {
  const id = document.getElementById("pp_id").value;
  if (!id) return showMsg("请先保存草稿", true);
  const res = await fetch(`/production-plans/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: "confirmed" }),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail) || "确认失败", true);
  }
  showMsg("计划已确认");
  closeModal();
  loadList();
});

document.getElementById("pp-tbody").addEventListener("click", (e) => {
  const ed = e.target.closest("[data-edit]");
  if (ed) {
    openEdit(Number(ed.getAttribute("data-edit")));
    return;
  }
  const pr = e.target.closest("[data-proc]");
  if (pr) {
    const id = Number(pr.getAttribute("data-proc"));
    const no = pr.getAttribute("data-no") || "";
    showProcurementPanel(id, no);
    document.getElementById("pp-procurement-panel").scrollIntoView({ behavior: "smooth" });
  }
});

document.getElementById("pp_calc_shortage").addEventListener("click", async () => {
  if (!currentPlanId) return showMsg("请先在列表中点「缺料/采购」选择计划", true);
  const res = await fetch(`/production-plans/${currentPlanId}/shortage`, { method: "POST" });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail) || "计算失败", true);
  }
  const data = await res.json();
  renderShortage(data);
  showMsg("汇总缺料计算完成");
});

document.getElementById("pp_draft_pos").addEventListener("click", async () => {
  if (!currentPlanId) return showMsg("请先在列表中点「缺料/采购」选择计划", true);
  if (!confirm("将按供应商拆分生成多张「草稿」采购订单，是否继续？")) return;
  const res = await fetch(`/production-plans/${currentPlanId}/draft-purchase-orders`, { method: "POST" });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail) || "生成失败", true);
  }
  const data = await res.json();
  const orders = data.created_orders || [];
  if (data.message) showMsg(data.message, orders.length === 0);
  else showMsg(`已生成 ${orders.length} 张草稿采购订单`);
  if (orders.length) {
    const nos = orders.map((o) => o.order_no).join("、");
    msgEl.textContent += ` 单号：${nos}。请到「采购订单」查看。`;
  }
  if (orders.length) loadList();
});

loadBoms().then(loadList);
