const msgEl = document.getElementById("msg");
const showMsg = (m, err = false) => {
  msgEl.textContent = m;
  msgEl.className = err ? "msg err" : "msg ok";
};

async function loadProfile() {
  const res = await fetch("/company-profile");
  if (!res.ok) return showMsg("公司信息加载失败", true);
  const p = await res.json();
  document.getElementById("cp_company_name").value = p.company_name || "";
  document.getElementById("cp_tax_no").value = p.tax_no || "";
  document.getElementById("cp_bank_name").value = p.bank_name || "";
  document.getElementById("cp_bank_account").value = p.bank_account || "";
  document.getElementById("cp_address").value = p.address || "";
  document.getElementById("cp_contact_person").value = p.contact_person || "";
  document.getElementById("cp_phone").value = p.phone || "";
}

document.getElementById("cp_save").addEventListener("click", async () => {
  const payload = {
    company_name: document.getElementById("cp_company_name").value.trim(),
    tax_no: document.getElementById("cp_tax_no").value.trim() || null,
    bank_name: document.getElementById("cp_bank_name").value.trim() || null,
    bank_account: document.getElementById("cp_bank_account").value.trim() || null,
    address: document.getElementById("cp_address").value.trim() || null,
    contact_person: document.getElementById("cp_contact_person").value.trim() || null,
    phone: document.getElementById("cp_phone").value.trim() || null,
  };
  if (!payload.company_name) return showMsg("公司名称必填", true);
  const res = await fetch("/company-profile", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    return showMsg(e.detail || "保存失败", true);
  }
  showMsg("已保存");
});

loadProfile();
