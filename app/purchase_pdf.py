"""采购订单 PDF（ReportLab + 内置中文字体）。"""
from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT = "STSong-Light"

_PO_STATUS_CN = {
    "draft": "草稿",
    "sent": "已发送",
    "confirmed": "已确认",
    "partial_received": "部分入库",
    "received": "已全部入库",
    "closed": "已关闭",
}
_PAYMENT_STATUS_CN = {"unpaid": "待付款", "partial": "部分付款", "paid": "已付款"}


def _register_cn_font() -> None:
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(FONT))
    except Exception as e:
        raise RuntimeError(
            "无法注册中文字体 STSong-Light，请确认已安装 reportlab 且环境支持 CID 字体。"
        ) from e


def _p(text: str, size: float = 9, bold: bool = False, align: str = "LEFT") -> Paragraph:
    ta = {"LEFT": TA_LEFT, "CENTER": TA_CENTER, "RIGHT": TA_RIGHT}.get(align, TA_LEFT)
    return Paragraph(
        f"<b>{escape(text)}</b>" if bold else escape(text or ""),
        ParagraphStyle(
            name="cn",
            fontName=FONT,
            fontSize=size,
            leading=size * 1.2,
            alignment=ta,
        ),
    )


def _fmt_money(v: Decimal | float | int | None) -> str:
    if v is None:
        return ""
    try:
        d = Decimal(str(v))
        return f"{d:,.2f}"
    except Exception:
        return str(v)


def _fmt_qty(v: Decimal | float | int | None) -> str:
    if v is None:
        return ""
    try:
        d = Decimal(str(v))
        if d == d.to_integral():
            return str(int(d))
        return format(d.normalize(), "f").rstrip("0").rstrip(".")
    except Exception:
        return str(v)


def build_purchase_order_pdf(po, company) -> bytes:
    _register_cn_font()
    buf = BytesIO()
    left_margin = 16 * mm
    right_margin = 16 * mm
    top_margin = 14 * mm
    bottom_margin = 18 * mm
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=left_margin,
        rightMargin=right_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
        title=getattr(po, "order_no", None) or "采购订单",
    )

    story: list = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="title",
        parent=styles["Heading1"],
        fontName=FONT,
        fontSize=18,
        leading=22,
        alignment=1,
    )
    story.append(Paragraph(escape("采购订单"), title_style))
    story.append(Spacer(1, 4 * mm))

    od = getattr(po, "order_date", None)
    od_s = od.strftime("%Y-%m-%d") if od else ""
    st = str(po.status or "")
    pay = str(getattr(po, "payment_status", None) or "")
    meta = [
        [_p("订单编号", 9, True), _p(str(po.order_no or ""), 9), _p("订单日期", 9, True), _p(od_s, 9)],
        [_p("订单状态", 9, True), _p(_PO_STATUS_CN.get(st, st), 9), _p("含税合计（元）", 9, True), _p(_fmt_money(po.total_with_tax), 9)],
        [_p("付款状态", 9, True), _p(_PAYMENT_STATUS_CN.get(pay, pay or "—"), 9), _p("", 9), _p("", 9)],
    ]
    mt = Table(meta, colWidths=[28 * mm, 68 * mm, 32 * mm, 52 * mm])
    mt.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ]
        )
    )
    story.append(mt)
    story.append(Spacer(1, 3 * mm))

    buyer_lines = [
        f"名称：{company.company_name or '—'}",
        f"税号：{company.tax_no or '—'}",
        f"开户行：{company.bank_name or '—'}",
        f"账号：{company.bank_account or '—'}",
        f"地址：{company.address or '—'}",
        f"联系人：{company.contact_person or '—'}",
        f"电话：{company.phone or '—'}",
    ]
    seller_lines = [
        f"名称：{po.supplier_company or '—'}",
        f"税号：{po.supplier_tax_no or '—'}",
        f"开户行：{po.supplier_bank or '—'}",
        f"账号：{po.supplier_account or '—'}",
        f"地址：{po.supplier_address or '—'}",
        f"电话：{po.supplier_phone or '—'}",
        f"联系人：{po.supplier_contact or '—'}",
    ]
    parties = Table(
        [
            [_p("买方（需方）", 10, True), _p("卖方（供方）", 10, True)],
            [
                Paragraph("<br/>".join(escape(x) for x in buyer_lines), ParagraphStyle("b", fontName=FONT, fontSize=8, leading=10)),
                Paragraph("<br/>".join(escape(x) for x in seller_lines), ParagraphStyle("s", fontName=FONT, fontSize=8, leading=10)),
            ],
        ],
        colWidths=[88 * mm, 88 * mm],
    )
    parties.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
            ]
        )
    )
    story.append(parties)
    story.append(Spacer(1, 3 * mm))

    terms = [
        [_p("交货地址", 9, True), _p(po.delivery_address or "—", 8)],
        [_p("付款条件", 9, True), _p(po.payment_terms or "—", 8)],
        [_p("交货条件", 9, True), _p(po.delivery_terms or "—", 8)],
        [_p("备注", 9, True), _p(po.header_remark or "—", 8)],
    ]
    tt = Table(terms, colWidths=[28 * mm, 148 * mm])
    tt.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ]
        )
    )
    story.append(tt)
    story.append(Spacer(1, 4 * mm))

    def _cell(s: str, size: int = 7) -> Paragraph:
        return Paragraph(
            escape(str(s)),
            ParagraphStyle("c", fontName=FONT, fontSize=size, leading=size * 1.15),
        )

    hdr = ["序号", "料号", "名称", "规格/图号", "单位", "数量", "含税单价", "金额", "税率说明", "行备注"]
    grid_data: list[list[Paragraph]] = [[_cell(h, 8) for h in hdr]]
    lines = sorted(po.lines, key=lambda x: x.line_no)
    for ln in lines:
        grid_data.append(
            [
                _cell(str(ln.line_no)),
                _cell(ln.material_code or ""),
                _cell(ln.material_name or ""),
                _cell(ln.spec_drawing or ""),
                _cell(ln.unit or ""),
                _cell(_fmt_qty(ln.qty)),
                _cell(_fmt_money(ln.unit_price)),
                _cell(_fmt_money(ln.line_amount)),
                _cell(ln.tax_rate_note or ""),
                _cell(ln.remark or ""),
            ]
        )
    grid_data.append(
        [
            _cell(""),
            _cell(""),
            _cell(""),
            _cell(""),
            _cell(""),
            _cell(""),
            _p("合计（元）", 9, True, "RIGHT"),
            _p(_fmt_money(po.total_with_tax), 9, False, "RIGHT"),
            _cell(""),
            _cell(""),
        ]
    )

    col_w = [10 * mm, 22 * mm, 28 * mm, 30 * mm, 12 * mm, 16 * mm, 22 * mm, 24 * mm, 18 * mm, 22 * mm]
    grid = Table(grid_data, colWidths=col_w, repeatRows=1)
    grid.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (5, 1), (7, -2), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
    )
    story.append(grid)
    story.append(Spacer(1, 6 * mm))
    story.append(
        _p("本订单经双方确认后生效；未尽事宜以双方约定或合同法相关规定为准。", 8)
    )

    doc.build(story)
    return buf.getvalue()
