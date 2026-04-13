import re
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_optional_tax_amount(raw) -> Decimal | None:
    """解析「含税金额」表单值：去空白/兼容全角、千分位逗号、欧式小数逗号；返回 None 表示留空。"""
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else None
        if raw is None:
            return None
    if isinstance(raw, Decimal):
        return money(raw)
    if isinstance(raw, bool):
        raise ValueError("含税金额格式无效")
    if isinstance(raw, (int, float)):
        if isinstance(raw, float) and (raw != raw or abs(raw) == float("inf")):
            raise ValueError("含税金额格式无效")
        return money(Decimal(str(raw)))
    if not isinstance(raw, str):
        raise ValueError("含税金额格式无效")
    s = unicodedata.normalize("NFKC", raw).strip()
    s = s.replace("\u00a0", "").replace(" ", "")
    if not s:
        return None
    s = s.replace("，", ",")
    if re.fullmatch(r"-?[\d,]+\.[\d]*", s) or re.fullmatch(r"-?[\d,]+\.", s):
        s = s.replace(",", "")
    elif re.fullmatch(r"-?[\d.]+,\d+", s) or re.fullmatch(r"-?[\d.]+,", s):
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    elif "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        d = Decimal(s)
    except InvalidOperation as e:
        raise ValueError("含税金额格式无效") from e
    return money(d)


def calc_total_price(qty: Decimal, unit_price: Decimal) -> Decimal:
    return money(Decimal(qty) * Decimal(unit_price))
