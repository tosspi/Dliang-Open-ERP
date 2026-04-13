const fmt3 = (v) => (v === null || v === undefined || v === "" ? "" : Number.isFinite(Number(v)) ? Number(v).toFixed(3) : String(v));

const pMsg = (m, err = false) => {
  const el = document.getElementById("msg");
  el.textContent = m;
  el.className = err ? "msg err" : "msg ok";
};

async function loadBoms() {
  const boms = await (await fetch("/boms")).json();
  const sel = document.getElementById("p_bom_id");
  sel.innerHTML = boms.map(b => `<option value="${b.id}">${b.product_code} | ${b.product_name} | ${b.bom_version}${b.is_current ? " (current)" : ""}</option>`).join("");
}

async function calcShortage() {
  const payload = { bom_id: Number(p_bom_id.value), production_qty: Number(p_qty.value) };
  const res = await fetch("/procurement/shortage-calc", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const e = await res.json();
    const pr = document.getElementById("p-record-total");
    const pg = document.getElementById("p-groups-total");
    if (pr) pr.textContent = "共 0 条记录";
    if (pg) pg.textContent = "共 0 组";
    document.getElementById("supplier-groups").innerHTML = "";
    return pMsg(e.detail || "缺料计算失败", true);
  }
  const data = await res.json();
  const tbody = document.getElementById("p-tbody");
  const pr = document.getElementById("p-record-total");
  const pg = document.getElementById("p-groups-total");
  if (!data.shortage_list.length) {
    tbody.innerHTML = `<tr><td colspan="13">无BOM明细或无需采购</td></tr>`;
    if (pr) pr.textContent = "共 0 条记录";
    if (pg) pg.textContent = "共 0 组";
  } else {
    tbody.innerHTML = data.shortage_list.map(i => `<tr>
      <td>${i.material_code}</td><td>${i.material_name}</td><td>${i.spec_drawing || ""}</td><td>${i.default_supplier || ""}</td><td>${fmt3(i.unit_usage)}</td>
      <td>${fmt3(i.total_required_qty)}</td><td>${fmt3(i.current_stock)}</td><td>${fmt3(i.safety_stock)}</td><td>${fmt3(i.safety_shortage_qty)}</td>
      <td>${fmt3(i.clear_shortage_qty)}</td>
      <td>${fmt3(i.suggested_purchase_qty)}</td><td>${fmt3(i.unit_price)}</td><td>${fmt3(i.estimated_amount)}</td>
    </tr>`).join("");
    if (pr) pr.textContent = `共 ${data.shortage_list.length} 条记录`;
  }
  if (pg && data.grouped_by_supplier) pg.textContent = `共 ${data.grouped_by_supplier.length} 组`;
  document.getElementById("p-total").textContent = fmt3(data.total_estimated_cost);
  const groupDiv = document.getElementById("supplier-groups");
  groupDiv.innerHTML = data.grouped_by_supplier.map(g => `
    <div class="card">
      <h4>${g.supplier} - 小计 ${fmt3(g.supplier_total_amount)}</h4>
      <p>${g.items.map(i => `${i.material_code}(${fmt3(i.suggested_purchase_qty)})`).join("，")}</p>
    </div>
  `).join("");
  pMsg("缺料计算完成");
}

loadBoms();
