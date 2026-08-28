# -*- coding: utf-8 -*-
"""第二階段：自動補人頭（含少休機制）。"""
from .coverage import daily_shift_counts, SHIFTS, SHIFT_ORDER
from .convert import assign_rest

FCODE = {"D白": "D4x", "E小夜": "Ex", "N大夜": "Nx"}
FLOORS = ["2F", "3F", "5F"]


def _floor_counts(converted, n_days):
    fc = {d: {s: {f: 0 for f in FLOORS} for s in SHIFTS} for d in range(1, n_days + 1)}
    for p in converted:
        for d, info in p["days"].items():
            if info.get("is_work") and info.get("cat") in SHIFTS:
                fl = info.get("floor")
                if fl in fc[d][info["cat"]]:
                    fc[d][info["cat"]][fl] += 1
    return fc


def _roc_date(cfg):
    year = int(cfg.setting("西元年", 2026) or 2026)
    month = int(cfg.setting("月份", 7) or 7)
    return year - 1911, month


def _targets(cfg):
    return {
        "D白": int(cfg.setting("白班目標人數", 8) or 8),
        "E小夜": int(cfg.setting("小夜目標人數", 7) or 7),
        "N大夜": int(cfg.setting("大夜目標人數", 7) or 7),
    }


def _shift_reqs(cfg, shift):
    tw_min = 1 if shift in ("E小夜", "N大夜") else 0
    nurse_min = 1
    if shift == "N大夜":
        nurse_min = int(cfg.setting("大夜護理最少", 1) or 1)
        tw_min = int(cfg.setting("大夜台籍照服最少", 1) or 1)
    return nurse_min, tw_min


def auto_fill(converted, n_days, cfg):
    counts = daily_shift_counts(converted, n_days)
    floor_counts = _floor_counts(converted, n_days)
    roc_year, month = _roc_date(cfg)
    targets = _targets(cfg)
    max_consec = int(cfg.setting("人頭最多連續上班天數", 6) or 6)
    max_month = int(cfg.setting("人頭每月最多上班天數", 20) or 20)
    min_li = int(cfg.setting("每14天最少例假", 2) or 2)

    heads = {}
    for h in cfg.head_pool:
        heads[h.name] = {"meta": h, "cat": h.category,
                         "days": {}, "floor": {}, "shaoxiu": set()}
    log = []

    def consecutive_before(hname, d):
        c = 0
        dd = d - 1
        while dd >= 1 and heads[hname]["days"].get(dd):
            c += 1
            dd -= 1
        return c

    def _rest_floor_ok(hname, d):
        h = heads[hname]
        for start in range(max(1, d - 13), d + 1):
            worked = sum(1 for dd in range(start, start + 14)
                         if h["days"].get(dd)) + 1
            if worked > 14 - min_li:
                return False
        return True

    def can_assign(hname, d, shift, relaxed=False):
        h = heads[hname]
        if h["days"].get(d):
            return False
        if not h["meta"].available_on(roc_year, month, d):
            return False
        prev = h["days"].get(d - 1)
        if prev and SHIFT_ORDER[prev] > SHIFT_ORDER[shift]:
            return False
        nxt = h["days"].get(d + 1)
        if nxt and SHIFT_ORDER[shift] > SHIFT_ORDER[nxt]:
            return False
        if not _rest_floor_ok(hname, d):
            return False
        if not relaxed:
            if consecutive_before(hname, d) >= max_consec:
                return False
            if len(h["days"]) >= max_month:
                return False
        return True

    def pick(cat, d, shift, relaxed=False):
        cand = [n for n, h in heads.items()
                if (cat is None or h["cat"] == cat) and can_assign(n, d, shift, relaxed)]
        if not cand:
            return None
        cand.sort(key=lambda n: (bool(heads[n]["meta"].dedicated_to),
                                 len(heads[n]["days"]), n))
        return cand[0]

    def assign(hname, d, shift, shaoxiu=False):
        if shaoxiu:
            heads[hname]["shaoxiu"].add(d)
        fc = floor_counts[d][shift]
        floor = min(FLOORS, key=lambda f: (fc[f], FLOORS.index(f)))
        fc[floor] += 1
        heads[hname]["days"][d] = shift
        heads[hname]["floor"][d] = floor
        counts[d][shift]["total"] += 1
        blk = heads[hname]["cat"]
        counts[d][shift][blk] = counts[d][shift].get(blk, 0) + 1

    def fill_one(cats, d, shift):
        for c in cats:
            n = pick(c, d, shift)
            if n:
                assign(n, d, shift)
                return True
        for c in cats:
            n = pick(c, d, shift, relaxed=True)
            if n:
                assign(n, d, shift, shaoxiu=True)
                log.append(f"第{d}日 {shift} 人力不足→安排 {n} 少休出勤補班")
                return True
        return False

    # 全月第一階段：鎖住各班最低配置
    for d in range(1, n_days + 1):
        for shift in SHIFTS:
            nurse_min, tw_min = _shift_reqs(cfg, shift)
            slot = counts[d][shift]
            while slot.get("護理", 0) < nurse_min:
                if not fill_one(["護理"], d, shift):
                    log.append(f"第{d}日 {shift} 護理人頭不足，無法補足最低配置")
                    break
            while slot.get("台籍照服", 0) < tw_min:
                if not fill_one(["台籍照服"], d, shift):
                    log.append(f"第{d}日 {shift} 台籍照服人頭不足，無法補足最低配置")
                    break
    # 全月第二階段：補到總目標人數
    for d in range(1, n_days + 1):
        for shift in SHIFTS:
            slot = counts[d][shift]
            while slot["total"] < targets[shift]:
                if not fill_one(["護理", "台籍照服"], d, shift):
                    log.append(f"第{d}日 {shift} 人頭用盡，僅{slot['total']}人")
                    break

    # 轉成 converted 風格並分配例/休/國
    head_people = []
    for name, h in heads.items():
        if not h["days"]:
            continue
        block = h["cat"]
        days_out = {}
        worked = set(h["days"].keys())
        for d in range(1, n_days + 1):
            if d in worked:
                shift = h["days"][d]
                cat = shift
                fl = h["floor"].get(d, "5F")
                code = FCODE[shift]
                if shift == "D白":
                    code = "D5x" if block == "台籍照服" else "D4x"
                color = cfg.color_for(block, cat, fl)
                days_out[d] = {"code": code, "cat": cat,
                               "floor": fl, "color": color, "is_work": True}
            else:
                days_out[d] = {"code": None, "cat": "空", "floor": None,
                               "color": None, "is_work": False}
        rest_days = [d for d in range(1, n_days + 1) if d not in worked]
        quota = cfg.quota(roc_year, month) if hasattr(cfg, "quota") else None
        holiday_days = {dd for (y, m, dd) in getattr(cfg, "holiday_dates", {})
                        if y == roc_year and m == month}
        for d, lab in assign_rest(rest_days, min_li, None, quota, holiday_days).items():
            days_out[d]["code"] = lab
            days_out[d]["cat"] = lab
        n_shaoxiu = len(h["shaoxiu"])
        note = f"人頭補班；少休{n_shaoxiu}天" if n_shaoxiu else "人頭補班"
        head_people.append({
            "name": name, "record_name": name, "account": "(人頭)",
            "block": block, "shift_kind": note,
            "n_days": n_days, "days": days_out,
            "is_head": True, "shaoxiu": h["shaoxiu"],
        })
    return head_people, log
