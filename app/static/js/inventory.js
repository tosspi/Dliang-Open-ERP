const invMsg = (m, err = false) => {
  const el = document.getElementById("msg");
  el.textContent = m;
  el.className = err ? "msg err" : "msg ok";
};
const typeMap = { in: "入库", out: "出库", adjust: "调整" };
const fmt3 = (v) => (v === null || v === undefined || v === "" ? "" : Number.isFinite(Number(v)) ? Number(v).toFixed(3) : String(v));

let materialMap = new Map();

async function loadMaterialsOptions() {
  const mats = await (await fetch("/materials")).json();
  materialMap = new Map(mats.map(m => [m.id, m]));
  const sel = document.getElementById("t_material_id");
  sel.innerHTML = mats.map(m => `<option value="${m.id}">${m.code} | ${m.name} | 库存:${fmt3(m.current_stock)}</option>`).join("");
}

async function loadTransactions() {
  const materialId = document.getElementById("i_material_id").value.trim();
  const type = document.getElementById("i_type").value;
  const url = materialId ? `/inventory/materials/${materialId}/transactions` : "/inventory/transactions";
  const res = await fetch(url);
  if (!res.ok) {
    const tot = document.getElementById("tx-record-total");
    if (tot) tot.textContent = "共 0 条记录";
    return invMsg("加载流水失败", true);
  }
  let rows = await res.json();
  if (type) rows = rows.filter(r => r.transaction_type === type);
  const tbody = document.getElementById("tx-tbody");
  tbody.innerHTML = rows.map(r => {
    const m = materialMap.get(r.material_id);
    return `<tr>
      <td>${r.id}</td><td>${r.material_id} ${m ? "(" + m.code + " " + m.name + ")" : ""}</td><td>${typeMap[r.transaction_type] || r.transaction_type}</td>
      <td>${fmt3(r.qty)}</td><td>${fmt3(r.unit_price)}</td><td>${r.reference_type || ""}</td><td>${r.reference_no || ""}</td><td>${r.remark || ""}</td>
      <td>${(r.created_at || "").replace("T", " ").slice(0, 19)}</td>
    </tr>`;
  }).join("");
  const tot = document.getElementById("tx-record-total");
  if (tot) tot.textContent = `共 ${rows.length} 条记录`;
}

function openTxModal() { document.getElementById("tx-modal").classList.remove("hidden"); }
function closeTxModal() { document.getElementById("tx-modal").classList.add("hidden"); }

async function saveTx() {
  const payload = {
    material_id: Number(t_material_id.value),
    transaction_type: t_transaction_type.value,
    qty: Number(t_qty.value),
    unit_price: Number(t_unit_price.value || 0),
    reference_type: t_reference_type.value || null,
    reference_no: t_reference_no.value || null,
    remark: t_remark.value || null
  };
  const res = await fetch("/inventory/transactions", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const e = await res.json();
    return invMsg(e.detail || "保存失败", true);
  }
  invMsg("库存流水新增成功");
  closeTxModal();
  await loadMaterialsOptions();
  loadTransactions();
}

loadMaterialsOptions().then(loadTransactions);
