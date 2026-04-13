import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PartType(str, enum.Enum):
    standard = "standard"
    custom = "custom"
    assembly = "assembly"


class StatusType(str, enum.Enum):
    draft = "draft"
    released = "released"
    obsolete = "obsolete"


class TransactionType(str, enum.Enum):
    in_ = "in"
    out = "out"
    adjust = "adjust"


class ProductType(str, enum.Enum):
    self_made = "self_made"
    purchased = "purchased"


class MaterialCategory(Base):
    __tablename__ = "material_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    code_prefix: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SystemOption(Base):
    __tablename__ = "system_options"
    __table_args__ = (UniqueConstraint("option_type", "name", name="uq_option_type_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    option_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # unit/tax_rate/material_attr/grade
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    spec: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    part_type: Mapped[PartType] = mapped_column(Enum(PartType), nullable=False, default=PartType.standard)
    default_supplier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tax_rate: Mapped[str | None] = mapped_column(String(32), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    safety_stock: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    current_stock: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    usage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    material_name_attr: Mapped[str | None] = mapped_column(String(128), nullable=True)
    standard_attr: Mapped[str | None] = mapped_column(String(128), nullable=True)
    grade_attr: Mapped[str | None] = mapped_column(String(64), nullable=True)
    purchase_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_revision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[StatusType] = mapped_column(Enum(StatusType), nullable=False, default=StatusType.draft)
    drawing_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    revisions = relationship("PartRevision", back_populates="material")
    stock_transactions = relationship("StockTransaction", back_populates="material")


class PartRevision(Base):
    __tablename__ = "part_revisions"
    __table_args__ = (UniqueConstraint("material_id", "revision", name="uq_material_revision"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False, index=True)
    revision: Mapped[str] = mapped_column(String(32), nullable=False)
    drawing_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_path_pdf: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[StatusType] = mapped_column(Enum(StatusType), nullable=False, default=StatusType.draft)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    material_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    standard: Mapped[str | None] = mapped_column(String(128), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(64), nullable=True)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    material = relationship("Material", back_populates="revisions")


class BOMHeader(Base):
    __tablename__ = "bom_headers"
    __table_args__ = (UniqueConstraint("product_code", "bom_version", name="uq_product_bom_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bom_version: Mapped[str] = mapped_column(String(32), nullable=False)
    revision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[StatusType] = mapped_column(Enum(StatusType), nullable=False, default=StatusType.draft)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    items = relationship("BOMItem", back_populates="bom_header")


class BOMItem(Base):
    __tablename__ = "bom_items"
    __table_args__ = (UniqueConstraint("bom_header_id", "line_no", name="uq_bom_line_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bom_header_id: Mapped[int] = mapped_column(ForeignKey("bom_headers.id"), nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False, index=True)
    material_code: Mapped[str] = mapped_column(String(64), nullable=False)
    material_name: Mapped[str] = mapped_column(String(255), nullable=False)
    revision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    usage: Mapped[str] = mapped_column(String(255), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    material_name_attr: Mapped[str | None] = mapped_column(String(128), nullable=True)
    standard_attr: Mapped[str | None] = mapped_column(String(128), nullable=True)
    grade_attr: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    bom_header = relationship("BOMHeader", back_populates="items")
    material = relationship("Material")


class ProductionPlan(Base):
    """生产计划单：多行 BOM × 计划产量，用于汇总缺料与生成草稿采购订单。"""

    __tablename__ = "production_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    plan_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lines = relationship(
        "ProductionPlanLine",
        back_populates="plan",
        order_by="ProductionPlanLine.line_no",
        cascade="all, delete-orphan",
    )


class ProductionPlanLine(Base):
    __tablename__ = "production_plan_lines"
    __table_args__ = (UniqueConstraint("plan_id", "line_no", name="uq_production_plan_line_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("production_plans.id"), nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    bom_id: Mapped[int] = mapped_column(ForeignKey("bom_headers.id"), nullable=False, index=True)
    planned_qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)

    plan = relationship("ProductionPlan", back_populates="lines")
    bom_header = relationship("BOMHeader", foreign_keys=[bom_id])


class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False, index=True)
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    reference_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    material = relationship("Material", back_populates="stock_transactions")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_code: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    supplier_categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    credit_code: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bank_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 付款账期：自订单日起多少天内应付（用于采购列表推算付款截止日）
    payment_term_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SupplierMaterial(Base):
    __tablename__ = "supplier_materials"
    __table_args__ = (UniqueConstraint("supplier_id", "material_id", name="uq_supplier_material"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CompanyProfile(Base):
    """买方公司基础信息（单条 id=1），采购/销售单据引用。"""

    __tablename__ = "company_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    tax_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    # 与单据状态分离：付款进度（手工维护，后续可接付款流水）
    payment_status: Mapped[str] = mapped_column(String(16), nullable=False, default="unpaid")
    order_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    supplier_company: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    supplier_tax_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_bank: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_account: Mapped[str | None] = mapped_column(String(128), nullable=True)
    supplier_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_contact: Mapped[str | None] = mapped_column(String(64), nullable=True)

    delivery_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    header_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_with_tax: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lines = relationship("PurchaseOrderLine", back_populates="order", order_by="PurchaseOrderLine.line_no")
    invoices = relationship("PurchaseInvoice", back_populates="order", order_by="PurchaseInvoice.id")


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    material_id: Mapped[int | None] = mapped_column(ForeignKey("materials.id"), nullable=True, index=True)
    material_code: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    material_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    spec_drawing: Mapped[str | None] = mapped_column(String(512), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    received_qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    line_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    tax_rate_note: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)

    order = relationship("PurchaseOrder", back_populates="lines")
    material = relationship("Material", foreign_keys=[material_id])


class PurchaseInvoice(Base):
    """采购发票（电子档必传），挂采购订单。"""

    __tablename__ = "purchase_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), nullable=False, index=True)
    invoice_no: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_with_tax: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    order = relationship("PurchaseOrder", back_populates="invoices")


class AppIntegrationSettings(Base):
    """全局集成配置（单条 id=1）：淘宝开放平台 App 与回调等。"""

    __tablename__ = "app_integration_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    taobao_app_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    taobao_app_secret: Mapped[str | None] = mapped_column(String(128), nullable=True)
    taobao_redirect_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    taobao_default_logistics_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    taobao_last_increment_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    woocommerce_site_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    woocommerce_consumer_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    woocommerce_consumer_secret: Mapped[str | None] = mapped_column(String(128), nullable=True)
    woocommerce_last_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class IntegrationOAuthState(Base):
    __tablename__ = "integration_oauth_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class TaobaoShopSession(Base):
    """淘宝 C 店授权会话（当前仅保留最近一次授权店铺）。"""

    __tablename__ = "taobao_shop_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_nick: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    taobao_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expire_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    internal_order_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    # taobao / woocommerce / manual；手工单用 platform_tid = m-{internal_order_no} 保证唯一且不改库非空约束
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="taobao", index=True)
    platform_tid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    platform_order_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform_status: Mapped[str] = mapped_column(String(48), nullable=False, default="")
    buyer_nick: Mapped[str | None] = mapped_column(String(128), nullable=True)
    receiver_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    receiver_mobile: Mapped[str | None] = mapped_column(String(32), nullable=True)
    receiver_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    header_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    post_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    pay_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    platform_modified: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    local_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_ship")
    # 发票：none 未开票 / pending 待开票 / issued 已开票 / not_required 不开票
    invoice_status: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    invoice_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    invoiced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    taobao_consign_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    taobao_consigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    taobao_out_sid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    taobao_logistics_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lines = relationship("SalesOrderLine", back_populates="order", cascade="all, delete-orphan", order_by="SalesOrderLine.id")


class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"), nullable=False, index=True)
    platform_oid: Mapped[str] = mapped_column(String(64), nullable=False)
    num_iid: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sku_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    outer_iid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    pic_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    material_id: Mapped[int | None] = mapped_column(ForeignKey("materials.id"), nullable=True, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)

    order = relationship("SalesOrder", back_populates="lines")
    material = relationship("Material", foreign_keys=[material_id])
    product = relationship("Product", foreign_keys=[product_id])


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_type: Mapped[ProductType] = mapped_column(Enum(ProductType), nullable=False, default=ProductType.self_made)
    product_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    spec_drawing: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sale_price_with_tax: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    current_stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    safety_stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_material_id: Mapped[int | None] = mapped_column(ForeignKey("materials.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    linked_material = relationship("Material")


class Inquiry(Base):
    __tablename__ = "inquiries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inquiry_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    inquiry_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    supplier_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_contact: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    delivery_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    header_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_estimated: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lines = relationship("InquiryLine", back_populates="inquiry", order_by="InquiryLine.line_no")


class InquiryLine(Base):
    """仅关联物料主数据，不存名称/规格等快照；展示时 JOIN materials。"""

    __tablename__ = "inquiry_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inquiry_id: Mapped[int] = mapped_column(ForeignKey("inquiries.id"), nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=1)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)

    inquiry = relationship("Inquiry", back_populates="lines")
    material = relationship("Material", foreign_keys=[material_id])
