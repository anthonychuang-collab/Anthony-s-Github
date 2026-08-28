# -*- coding: utf-8 -*-
"""T 班 -> F 班 轉換核心：碼轉換、例/休/國分配、樓層上色、人頭改名。"""
from .codes import CodeBook, classify, REST_TOKENS


DEFAULT_FLOOR = "5F"   # 護理無前綴 Di 視為 5F（可被人員主檔預設樓層覆蓋）


def _white_code(person, block, fcode, raw):
    """白班顯示碼：優先看該員『適用班別碼』，其次 T 碼提示，最後區塊預設。"""
    allowed = person.allowed if getattr(person, "allowed", None) else None
    r = str(raw)
    if ("D6" in r) and (allowed is None or "D6x" in allowed):
        return "D6x"
    if ("D4" in r) and (allowed is None or "D4x" in allowed):
        return "D4x"
    if allowed:
        for c in ("D6x", "D5x", "D4x", "Dx"):
            if c in allowed:
                return c
    if block == "外籍照服":
        return "Dx"
    if block == "台籍照服":
        return "D5x"
    return "D4x"


def _place_li(remaining, n_li, min_li_per_14=2):
    """在休息日 remaining(sorted) 中選出 n_li 個例假日：依日期平均分散。"""
    if not remaining or n_li <= 0:
        return set()
    lo, hi = remaining[0], remaining[-1]
    span = max(hi - lo, 1)
    li = set()
    pool = list(remaining)
    for k in range(min(n_li, len(remaining))):
        target = lo + span * (k + 0.5) / n_li
        c = min(pool, key=lambda d: abs(d - target))
        li.add(c)
        pool.remove(c)
    return li


def assign_rest(rest_days, min_li_per_14=2, forced=None, quota=None, holiday_days=None):
    """把休息日分配成 例/休/國。
    - 有 quota（年度行事曆每月配額 {例,休,國}）時：依配額分配 國→例→休，
      國優先落在國定假日確切日期(holiday_days)。
    - 無 quota 時：排序交替 休,例,休…，並確保每 14 天至少 min_li_per_14 例假。"""
    forced = forced or {}
    holiday_days = holiday_days or set()
    rest = sorted(rest_days)
    label = {}

    if quota:
        n_guo = int(quota.get("國", 0) or 0)
        n_li = int(quota.get("例", 0) or 0)
        guo = [d for d in rest if d in holiday_days][:n_guo]
        if len(guo) < n_guo:
            for d in rest:
                if len(guo) >= n_guo:
                    break
                if d not in guo:
                    guo.append(d)
        for d in guo:
            label[d] = "國"
        remaining = [d for d in rest if d not in label]
        li_days_set = _place_li(remaining, n_li, min_li_per_14)
        for d in remaining:
            label[d] = "例" if d in li_days_set else "休"
    else:
        for i, d in enumerate(rest):
            label[d] = "例" if i % 2 == 1 else "休"

    for d, lab in forced.items():
        if d in label:
            label[d] = lab

    # 每 14 天例假 >= min（僅無配額時；有配額不做，避免破壞月例假總數）
    if not quota:
        for start in range(1, 32):
            window = [d for d in rest if start <= d < start + 14]
            if not window:
                continue
            li = [d for d in window if label[d] == "例"]
            need = min_li_per_14 - len(li)
            if need > 0:
                xiu = [d for d in window if label[d] == "休"]
                for d in xiu[:need]:
                    label[d] = "例"
    return label


def convert_person(person, trow, codebook, cfg):
    """回傳 {name, record_name, account, block, days:{d:{code,cat,floor,color,is_work}}}"""
    block = person.block
    days_out = {}
    rest_days = []
    n = 0
    for d, raw in trow["days"].items():
        n = max(n, d)
        if raw is None or raw == "":
            days_out[d] = {"code": None, "cat": "空", "floor": None,
                           "color": None, "is_work": False}
            continue
        if raw in REST_TOKENS or raw == "R'":
            rest_days.append(d)
            days_out[d] = {"code": "REST", "cat": "例休", "floor": None,
                           "color": None, "is_work": False}
            continue
        fcode, cat, floor = codebook.lookup(raw)
        cat_n = classify(fcode, cat)
        if cat_n in ("特", "國", "空", "其他") or fcode in ("/", "特", "國", "公"):
            days_out[d] = {"code": fcode, "cat": cat_n, "floor": None,
                           "color": None,
                           "is_work": fcode not in ("/", "特", "國", "公")}
            continue
        if cat_n == "D白":
            fcode = _white_code(person, block, fcode, raw)
        fl = floor or person.floor or DEFAULT_FLOOR
        color = cfg.color_for(block, cat_n, fl)
        days_out[d] = {"code": fcode, "cat": cat_n, "floor": fl,
                       "color": color, "is_work": True}

    # 分配例/休/國（依年度行事曆每月配額 + 國定假日確切日期）
    min_li = int(cfg.setting("每14天最少例假", 2) or 2)
    roc_year = int(cfg.setting("西元年", 2026) or 2026) - 1911
    month = int(cfg.setting("月份", 7) or 7)
    quota = cfg.quota(roc_year, month) if hasattr(cfg, "quota") else None
    holiday_days = {d for (y, m, d) in getattr(cfg, "holiday_dates", {})
                    if y == roc_year and m == month}
    labels = assign_rest(rest_days, min_li, None, quota, holiday_days)
    for d, lab in labels.items():
        days_out[d]["code"] = lab
        days_out[d]["cat"] = lab

    return {
        "name": person.name,
        "record_name": person.record_name,
        "account": person.account or (trow.get("account") or ""),
        "block": block,
        "shift_kind": person.shift_kind,
        "n_days": n,
        "days": days_out,
    }


def convert_foreign_code(raw):
    """外籍照服碼(舊式helper)：刪樓層數字、確保結尾 x。 2Da->Dax, 3Nb->Nbx。"""
    import re
    s = str(raw).strip()
    s = re.sub(r"^[235]", "", s)
    if s and not s.endswith("x"):
        s = s + "x"
    return s
