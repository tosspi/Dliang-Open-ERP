from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import PartType, ProductType, StatusType, TransactionType


class MaterialBase(BaseModel):
    code: str | None = None
    name: str
    spec: str | None = None
    unit: str | None = None
    category: str | None = None
    part_type: PartType = PartType.standard
    default_supplier: str | None = None
    tax_rate: str | None = None
    unit_price: Decimal = Decimal("0")
    safety_stock: Decimal = Decimal("0")
    current_stock: Decimal = Decimal("0")
    usage: str | None = None
    material_name_attr: str | None = None
    standard_attr: str | None = None
    grade_attr: str | None = None
    purchase_link: str | None = None
    remark: str | None = None
    current_revision: str | None = None
    status: StatusType = StatusType.draft
    drawing_no: str | None = None
    is_active: bool = True


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    name: str | None = None
    spec: str | None = None
    unit: str | None = None
    category: str | None = None
    part_type: PartType | None = None
    default_supplier: str | None = None
    tax_rate: str | None = None
    unit_price: Decimal | None = None
    safety_stock: Decimal | None = None
    current_stock: Decimal | None = None
    usage: str | None = None
    material_name_attr: str | None = None
    standard_attr: str | None = None
    grade_attr: str | None = None
    purchase_link: str | None = None
    remark: str | None = None
    current_revision: str | None = None
    status: StatusType | None = None
    drawing_no: str | None = None
    is_active: bool | None = None


class MaterialRead(MaterialBase):
    code: str
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaterialImportErrorItem(BaseModel):
    row: int
    message: str


class MaterialImportSummary(BaseModel):
    created: int
    failed: int
    errors: list[MaterialImportErrorItem]


class MaterialCategoryBase(BaseModel):
    name: str
    code_prefix: str
    sort_order: int = 0
    is_active: bool = True
    remark: str | None = None


class MaterialCategoryCreate(MaterialCategoryBase):
    pass


class MaterialCategoryUpdate(BaseModel):
    name: str | None = None
    code_prefix: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    remark: str | None = None


class MaterialCategoryRead(MaterialCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SystemOptionBase(BaseModel):
    option_type: str
    name: str
    sort_order: int = 0
    is_active: bool = True
    remark: str | None = None


class SystemOptionCreate(SystemOptionBase):
    pass


class SystemOptionUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    remark: str | None = None


class SystemOptionRead(SystemOptionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RevisionBase(BaseModel):
    revision: str
    drawing_no: str | None = None
    file_path_pdf: str | None = None
    file_path_model: str | None = None
    status: StatusType = StatusType.draft
    is_current: bool = False
    purpose: str | None = None
    material_name: str | None = None
    standard: str | None = None
    grade: str | None = None
    change_note: str | None = None


class RevisionCreate(RevisionBase):
    pass


class RevisionUpdate(BaseModel):
    revision: str | None = None
    drawing_no: str | None = None
    file_path_pdf: str | None = None
    file_path_model: str | None = None
    status: StatusType | None = None
    is_current: bool | None = None
    purpose: str | None = None
    material_name: str | None = None
    standard: str | None = None
    grade: str | None = None
    change_note: str | None = None


class RevisionRead(RevisionBase):
    id: int
    material_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RevisionListItem(RevisionRead):
    """非标物料（自制/装配）版本行：含物料主数据字段便于列表展示。

    注意：RevisionBase.material_name 表示版本记录上的「材质」属性；物料主数据名称使用 material_item_name，避免重名冲突。
    """

    material_code: str
    material_item_name: str
    material_category: str | None = None
    material_part_type: PartType


class BOMHeaderBase(BaseModel):
    product_code: str
    product_name: str
    bom_version: str
    revision_note: str | None = None
    status: StatusType = StatusType.draft
    is_current: bool = False


class BOMHeaderCreate(BOMHeaderBase):
    pass


class BOMHeaderUpdate(BaseModel):
    product_name: str | None = None
    bom_version: str | None = None
    revision_note: str | None = None
    status: StatusType | None = None
    is_current: bool | None = None


class BOMHeaderRead(BOMHeaderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BOMItemBase(BaseModel):
    line_no: int
    material_id: int
    material_code: str | None = None
    material_name: str | None = None
    revision: str | None = None
    usage: str = "—"
    qty: Decimal
    unit: str | None = None
    material_name_attr: str | None = None
    standard_attr: str | None = None
    grade_attr: str | None = None
    unit_price: Decimal = Decimal("0")
    total_price: Decimal | None = None
    remark: str | None = None


class BOMItemCreate(BOMItemBase):
    pass


class BOMItemUpdate(BaseModel):
    line_no: int | None = None
    material_id: int | None = None
    material_code: str | None = None
    material_name: str | None = None
    revision: str | None = None
    usage: str | None = None
    qty: Decimal | None = None
    unit: str | None = None
    material_name_attr: str | None = None
    standard_attr: str | None = None
    grade_attr: str | None = None
    unit_price: Decimal | None = None
    total_price: Decimal | None = None
    remark: str | None = None


class BOMItemRead(BOMItemBase):
    id: int
    bom_header_id: int
    spec_drawing: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BOMDetailRead(BaseModel):
    header: BOMHeaderRead
    items: list[BOMItemRead]
    total_cost: Decimal


class StockTransactionBase(BaseModel):
    material_id: int
    transaction_type: TransactionType
    qty: Decimal = Field(..., gt=0)
    unit_price: Decimal = Decimal("0")
    reference_type: str | None = None
    reference_no: str | None = None
    remark: str | None = None


class StockTransactionCreate(StockTransactionBase):
    pass


class StockTransactionRead(StockTransactionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierBase(BaseModel):
    supplier_code: str | None = None
    company_name: str
    supplier_categories: list[str] = Field(default_factory=list)
    credit_code: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    bank_no: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    address: str | None = None
    # 账期（天）：自采购订单日期起算付款截止；留空表示不推算截止日
    payment_term_days: int | None = Field(None, ge=0)
    managed_material_ids: list[int] = Field(default_factory=list)
    is_active: bool = True


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    supplier_code: str | None = None
    company_name: str | None = None
    supplier_categories: list[str] | None = None
    credit_code: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    bank_no: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    address: str | None = None
    payment_term_days: int | None = Field(None, ge=0)
    managed_material_ids: list[int] | None = None
    is_active: bool | None = None


class SupplierManagedMaterial(BaseModel):
    id: int
    code: str
    name: str
    spec_drawing: str | None = None
    unit: str | None = None
    unit_price: Decimal = Decimal("0")
    tax_rate: str | None = None
    remark: str | None = None


class SupplierRead(SupplierBase):
    id: int
    managed_materials: list[SupplierManagedMaterial] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShortageCalcRequest(BaseModel):
    bom_id: int
    production_qty: Decimal = Field(..., gt=0)


class ShortageItem(BaseModel):
    material_id: int
    material_code: str
    material_name: str
    spec_drawing: str | None = None
    revision: str | None = None
    usage: str
    unit: str | None = None
    unit_usage: Decimal
    total_required_qty: Decimal
    current_stock: Decimal
    safety_stock: Decimal
    safety_shortage_qty: Decimal  # 总需求 + 安全库存 − 当前库存（≥0），用于建议采购
    clear_shortage_qty: Decimal  # 总需求 − 当前库存（≥0），不含安全库存，即「刚好够用」缺口
    suggested_purchase_qty: Decimal
    default_supplier: str | None = None
    unit_price: Decimal
    estimated_amount: Decimal


class SupplierGroup(BaseModel):
    supplier: str
    items: list[ShortageItem]
    supplier_total_amount: Decimal


class ShortageCalcResponse(BaseModel):
    bom_id: int
    production_qty: Decimal
    shortage_list: list[ShortageItem]
    grouped_by_supplier: list[SupplierGroup]
    total_estimated_cost: Decimal


class PlanShortageResponse(BaseModel):
    """多 BOM 行合并后的缺料结果（与 shortage-calc 明细结构一致）。"""

    production_plan_id: int
    plan_no: str
    shortage_list: list[ShortageItem]
    grouped_by_supplier: list[SupplierGroup]
    total_estimated_cost: Decimal


class ProductionPlanLineIn(BaseModel):
    line_no: int | None = None
    bom_id: int
    planned_qty: Decimal = Field(..., gt=0)
    remark: str | None = None


class ProductionPlanCreate(BaseModel):
    plan_date: datetime | None = None
    remark: str | None = None
    lines: list[ProductionPlanLineIn] = Field(default_factory=list)


class ProductionPlanUpdate(BaseModel):
    plan_date: datetime | None = None
    status: str | None = None
    remark: str | None = None
    lines: list[ProductionPlanLineIn] | None = None


class ProductionPlanLineRead(BaseModel):
    id: int
    line_no: int
    bom_id: int
    product_code: str
    product_name: str
    bom_version: str
    planned_qty: Decimal
    remark: str | None = None


class ProductionPlanRead(BaseModel):
    id: int
    plan_no: str
    plan_date: datetime
    status: str
    remark: str | None = None
    lines: list[ProductionPlanLineRead]
    created_at: datetime
    updated_at: datetime


# --- Company profile (买方) ---


class CompanyProfileRead(BaseModel):
    id: int
    company_name: str
    tax_no: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    address: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyProfileUpdate(BaseModel):
    company_name: str | None = None
    tax_no: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    address: str | None = None
    contact_person: str | None = None
    phone: str | None = None


# --- 手工采购订单 ---


class PurchaseOrderLineIn(BaseModel):
    """保存明细；更新时携带 id 以保留已入库数量。"""

    id: int | None = None
    line_no: int
    material_id: int | None = None
    material_code: str = ""
    material_name: str = ""
    spec_drawing: str | None = None
    unit: str | None = None
    qty: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    tax_rate_note: str | None = None
    remark: str | None = None


class PurchaseOrderLineRead(BaseModel):
    id: int
    purchase_order_id: int
    line_no: int
    material_id: int | None = None
    material_code: str
    material_name: str
    spec_drawing: str | None
    unit: str | None
    qty: Decimal
    received_qty: Decimal
    qty_open: Decimal
    unit_price: Decimal
    line_amount: Decimal
    tax_rate_note: str | None
    remark: str | None

    model_config = ConfigDict(from_attributes=True)


class PurchaseInvoiceRead(BaseModel):
    id: int
    purchase_order_id: int
    invoice_no: str
    amount_with_tax: Decimal | None = None
    original_filename: str
    remark: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderReceiveLineIn(BaseModel):
    line_id: int | None = None
    line_no: int | None = None
    qty: Decimal = Field(..., gt=0)

    @model_validator(mode="after")
    def need_line_ref(self):
        if self.line_id is None and self.line_no is None:
            raise ValueError("每行须指定 line_id 或 line_no")
        return self


class PurchaseOrderReceiveIn(BaseModel):
    lines: list[PurchaseOrderReceiveLineIn]


class PurchaseOrderCreate(BaseModel):
    order_date: datetime | None = None
    supplier_company: str
    supplier_tax_no: str | None = None
    supplier_bank: str | None = None
    supplier_account: str | None = None
    supplier_address: str | None = None
    supplier_phone: str | None = None
    supplier_contact: str | None = None
    delivery_address: str | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    header_remark: str | None = None
    lines: list[PurchaseOrderLineIn]


class PurchaseOrderUpdate(BaseModel):
    order_date: datetime | None = None
    status: str | None = None
    payment_status: str | None = None
    supplier_company: str | None = None
    supplier_tax_no: str | None = None
    supplier_bank: str | None = None
    supplier_account: str | None = None
    supplier_address: str | None = None
    supplier_phone: str | None = None
    supplier_contact: str | None = None
    delivery_address: str | None = None
    payment_terms: str | None = None
    delivery_terms: str | None = None
    header_remark: str | None = None
    lines: list[PurchaseOrderLineIn] | None = None


class PurchaseOrderRead(BaseModel):
    id: int
    order_no: str
    status: str
    payment_status: str
    receipt_progress: str
    order_date: datetime
    supplier_company: str
    supplier_tax_no: str | None
    supplier_bank: str | None
    supplier_account: str | None
    supplier_address: str | None
    supplier_phone: str | None
    supplier_contact: str | None
    delivery_address: str | None
    payment_terms: str | None
    delivery_terms: str | None
    header_remark: str | None
    total_with_tax: Decimal
    created_at: datetime
    updated_at: datetime
    lines: list[PurchaseOrderLineRead]
    invoices: list[PurchaseInvoiceRead]
    # 按供应商档案中的账期推算（订单日 + 账期天）；无账期或未匹配供应商时为 null
    payment_due_date: date | None = None
    payment_due_days_remaining: int | None = None

    model_config = ConfigDict(from_attributes=True)


class DraftPOsFromPlanResponse(BaseModel):
    created_orders: list[PurchaseOrderRead]
    skipped_unassigned: bool
    message: str | None = None


# --- 销售 / 淘宝集成 ---


class TaobaoIntegrationConfigRead(BaseModel):
    taobao_app_key: str | None = None
    taobao_app_secret_configured: bool = False
    taobao_redirect_uri: str | None = None
    taobao_default_logistics_code: str | None = None
    taobao_authorized: bool = False
    taobao_seller_nick: str | None = None
    taobao_token_expire_time: datetime | None = None
    taobao_last_increment_sync: datetime | None = None


class TaobaoIntegrationConfigUpdate(BaseModel):
    taobao_app_key: str | None = None
    taobao_app_secret: str | None = None
    taobao_redirect_uri: str | None = None
    taobao_default_logistics_code: str | None = None


class TaobaoOAuthUrlResponse(BaseModel):
    authorization_url: str


class SalesOrderLineRead(BaseModel):
    id: int
    platform_oid: str
    num_iid: str | None = None
    sku_id: str | None = None
    outer_iid: str | None = None
    title: str
    qty: Decimal
    price: Decimal
    line_total: Decimal
    pic_url: str | None = None
    material_id: int | None = None
    product_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class SalesOrderRead(BaseModel):
    id: int
    internal_order_no: str
    channel: str
    platform_tid: str
    platform_order_no: str | None = None
    platform_status: str
    buyer_nick: str | None = None
    receiver_name: str | None = None
    receiver_mobile: str | None = None
    receiver_address: str | None = None
    header_remark: str | None = None
    total_amount: Decimal
    post_fee: Decimal
    pay_time: datetime | None = None
    platform_modified: datetime | None = None
    local_status: str
    invoice_status: str = "none"
    invoice_no: str | None = None
    invoiced_at: datetime | None = None
    taobao_consign_error: str | None = None
    taobao_consigned_at: datetime | None = None
    taobao_out_sid: str | None = None
    taobao_logistics_code: str | None = None
    created_at: datetime
    updated_at: datetime
    lines: list[SalesOrderLineRead]

    model_config = ConfigDict(from_attributes=True)


class ManualSalesOrderLineIn(BaseModel):
    """手工单明细：可从产品主数据选择（带默认含税售价与关联物料），或手填品名/物料。"""

    title: str = ""
    qty: Decimal
    price: Decimal | None = None
    line_total: Decimal | None = None
    outer_iid: str | None = None
    product_id: int | None = None
    material_id: int | None = None
    material_code: str | None = None
    platform_oid: str | None = None

    @model_validator(mode="after")
    def need_source_and_price(self):
        t = (self.title or "").strip()
        has_src = bool(t) or self.material_id is not None or bool((self.material_code or "").strip()) or self.product_id is not None
        if not has_src:
            raise ValueError("每行请选择产品，或填写品名，或填写物料编码 / 物料 ID")
        if self.product_id is None and self.price is None:
            raise ValueError("未选择产品时须填写单价")
        return self


class ManualSalesOrderCreate(BaseModel):
    buyer_nick: str | None = None
    receiver_name: str | None = None
    receiver_mobile: str | None = None
    receiver_address: str | None = None
    header_remark: str | None = None
    customer_ref: str | None = Field(None, description="客户侧单号/合同号，写入平台单号列")
    post_fee: Decimal = Decimal("0")
    pay_time: datetime | None = None
    confirm_immediately: bool = Field(False, description="为 true 时跳过草稿，直接进入待发货")
    lines: list[ManualSalesOrderLineIn]

    @model_validator(mode="after")
    def need_lines(self):
        if not self.lines:
            raise ValueError("至少一行明细")
        return self


class ManualSalesOrderUpdate(BaseModel):
    buyer_nick: str | None = None
    receiver_name: str | None = None
    receiver_mobile: str | None = None
    receiver_address: str | None = None
    header_remark: str | None = None
    customer_ref: str | None = None
    post_fee: Decimal | None = None
    pay_time: datetime | None = None
    lines: list[ManualSalesOrderLineIn] | None = None


class SalesOrderInvoicePatch(BaseModel):
    invoice_status: str | None = None
    invoice_no: str | None = None
    invoiced_at: datetime | None = None


class ManualShipRequest(BaseModel):
    tracking_number: str = Field(..., min_length=1, description="运单号，记入本地发货信息")
    carrier_name: str | None = Field(None, description="承运商，可选")


class TaobaoShipRequest(BaseModel):
    company_code: str = Field(..., min_length=1, description="淘宝物流公司编码，如 STO、YTO、ZTO 等")
    out_sid: str = Field(..., min_length=1, description="运单号")


class TaobaoSyncResult(BaseModel):
    synced_count: int
    message: str | None = None


class WooCommerceIntegrationConfigRead(BaseModel):
    woocommerce_site_url: str | None = None
    woocommerce_consumer_key_configured: bool = False
    woocommerce_consumer_secret_configured: bool = False
    woocommerce_last_sync: datetime | None = None


class WooCommerceIntegrationConfigUpdate(BaseModel):
    woocommerce_site_url: str | None = None
    woocommerce_consumer_key: str | None = None
    woocommerce_consumer_secret: str | None = None


class WooCommerceSyncResult(BaseModel):
    synced_count: int
    message: str | None = None


class WooCommerceShipRequest(BaseModel):
    tracking_number: str = Field(..., min_length=1)
    carrier_name: str | None = Field(None, description="承运商名称，写入订单 meta 便于后台查看")
    set_status_completed: bool = Field(True, description="是否将订单标为 completed（已付款待发场景）")


class ProductBase(BaseModel):
    product_name: str
    product_type: ProductType
    product_category: str | None = None
    model_no: str | None = None
    spec_drawing: str | None = None
    sale_price_with_tax: Decimal = Decimal("0")
    current_stock: Decimal = Decimal("0")
    safety_stock: Decimal = Decimal("0")
    remark: str | None = None
    linked_material_id: int | None = None
    is_active: bool = True


class ProductCreate(ProductBase):
    product_code: str


class ProductUpdate(BaseModel):
    product_code: str | None = None
    product_name: str | None = None
    product_type: ProductType | None = None
    product_category: str | None = None
    model_no: str | None = None
    spec_drawing: str | None = None
    sale_price_with_tax: Decimal | None = None
    current_stock: Decimal | None = None
    safety_stock: Decimal | None = None
    remark: str | None = None
    linked_material_id: int | None = None
    is_active: bool | None = None


class ProductRead(ProductBase):
    id: int
    product_code: str
    cost: Decimal = Decimal("0")
    current_bom_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InquiryLineIn(BaseModel):
    line_no: int
    material_id: int = Field(..., gt=0)
    qty: Decimal = Field(..., gt=0)
    remark: str | None = None


class InquiryLineRead(BaseModel):
    id: int
    inquiry_id: int
    line_no: int
    material_id: int
    qty: Decimal
    remark: str | None
    # 自物料主表实时带出（非快照）
    material_code: str
    material_name: str
    spec_drawing: str | None = None
    material_name_attr: str | None = None
    grade_attr: str | None = None
    unit: str | None = None
    unit_price: Decimal | None = None  # 询价单留空，不存库
    line_total: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class InquiryCreate(BaseModel):
    inquiry_date: datetime | None = None
    valid_until: datetime | None = None
    supplier_company: str | None = None
    supplier_contact: str | None = None
    supplier_phone: str | None = None
    delivery_address: str | None = None
    payment_terms: str | None = None
    header_remark: str | None = None
    lines: list[InquiryLineIn]


class InquiryUpdate(BaseModel):
    status: str | None = None
    inquiry_date: datetime | None = None
    valid_until: datetime | None = None
    supplier_company: str | None = None
    supplier_contact: str | None = None
    supplier_phone: str | None = None
    delivery_address: str | None = None
    payment_terms: str | None = None
    header_remark: str | None = None
    lines: list[InquiryLineIn] | None = None


class InquiryRead(BaseModel):
    id: int
    inquiry_no: str
    status: str
    inquiry_date: datetime
    valid_until: datetime | None = None
    supplier_company: str | None = None
    supplier_contact: str | None = None
    supplier_phone: str | None = None
    delivery_address: str | None = None
    payment_terms: str | None = None
    header_remark: str | None = None
    total_estimated: Decimal
    created_at: datetime
    updated_at: datetime
    lines: list[InquiryLineRead]

    model_config = ConfigDict(from_attributes=True)
