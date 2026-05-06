from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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
    auth,
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
from app.auth import ensure_admin_user

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
    # Create admin user if not exists
    admin, created = ensure_admin_user(_db_boot, "Lutrade", "Lutrade@zhao1993.", "管理员账户")
    if created:
        print(f"[INIT] Admin user 'Lutrade' created successfully")
    else:
        print(f"[INIT] Admin user 'Lutrade' already exists")
finally:
    _db_boot.close()

app = FastAPI(
    title="大亮ERP / Dliang-ERP",
    version="0.2.0",
    description="机械产品物料、BOM、版本、库存、采购建议 ERP系统",
)

# Include routers
app.include_router(auth.router)
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


# Auth middleware - protect all /ui/* routes
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    
    # Allow public paths
    public_paths = ["/", "/auth/login", "/auth/logout", "/docs", "/openapi.json", "/static"]
    if any(path.startswith(p) for p in public_paths):
        return await call_next(request)
    
    # Check if path requires auth
    if path.startswith("/ui") or path.startswith("/api/"):
        from app.auth import get_current_user
        user = get_current_user(request)
        if not user:
            if request.headers.get("Accept") and "text/html" in request.headers.get("Accept", ""):
                return RedirectResponse(url="/auth/login", status_code=303)
            return HTMLResponse(content="Unauthorized - 请先登录", status_code=401)
    
    return await call_next(request)
