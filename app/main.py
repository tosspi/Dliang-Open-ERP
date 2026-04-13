from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import (
    BASE_DIR,
    Base,
    SessionLocal,
    engine,
    ensure_company_profile,
    ensure_company_profile_columns,
    ensure_default_system_options,
    ensure_purchase_order_extensions,
    ensure_sqlite_app_integration_woocommerce_columns,
    ensure_sqlite_material_columns,
    ensure_sqlite_sales_order_lines_product_id,
    ensure_sqlite_sales_orders_columns,
    ensure_sqlite_supplier_columns,
    migrate_inquiry_lines_material_ref_only,
)
from app import crud
from app.routes import (
    bom,
    company_settings,
    excel_exports,
    excel_imports,
    inquiries,
    integrations_taobao,
    integrations_woocommerce,
    inventory,
    material_categories,
    materials,
    procurement,
    production_plans,
    products,
    purchase_orders,
    revisions,
    sales,
    suppliers,
    system_options,
    ui,
)

Base.metadata.create_all(bind=engine)
ensure_sqlite_material_columns()
ensure_sqlite_supplier_columns()
ensure_default_system_options()
ensure_company_profile()
ensure_company_profile_columns()
migrate_inquiry_lines_material_ref_only()
ensure_purchase_order_extensions()
ensure_sqlite_sales_orders_columns()
ensure_sqlite_sales_order_lines_product_id()
(BASE_DIR / "uploads" / "purchase_invoices").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "uploads" / "revision_drawings").mkdir(parents=True, exist_ok=True)
_db_boot = SessionLocal()
try:
    crud.get_or_create_integration_settings(_db_boot)
finally:
    _db_boot.close()

app = FastAPI(
    title="大亮ERP / Inventory API",
    version="0.1.0",
    description="机械产品物料、BOM、版本、库存、采购建议 MVP",
)

app.include_router(materials.router)
app.include_router(material_categories.router)
app.include_router(system_options.router)
app.include_router(revisions.router)
app.include_router(bom.router)
app.include_router(inventory.router)
app.include_router(procurement.router)
app.include_router(production_plans.router)
app.include_router(products.router)
app.include_router(inquiries.router)
app.include_router(company_settings.router)
app.include_router(integrations_taobao.router)
app.include_router(integrations_woocommerce.router)
app.include_router(sales.router)
app.include_router(purchase_orders.router)
app.include_router(suppliers.router)
app.include_router(ui.router)
app.include_router(excel_exports.router)
app.include_router(excel_imports.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def root():
    return RedirectResponse(url="/ui")
