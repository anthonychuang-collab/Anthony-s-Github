# -*- coding: utf-8 -*-
"""設立標準 + 勞基法 檢核。回傳問題清單與每日每班人力統計。"""

SHIFTS = ["D白", "E小夜", "N大夜"]
SHIFT_ORDER = {"D白": 0, "E小夜": 1, "N大夜": 2}


def daily_shift_counts(converted, n_days):
    counts = {}
    for d in range(1, n_days + 1):
        counts[d] = {s: {"total": 0} for s in SHIFTS}
    for p in converted:
        for d, info in p["days"].items():
            if not info.get("is_work"):
                continue
            cat = info["cat"]
            if cat not in SHIFTS:
                continue
            slot = counts[d][cat]
            slot["total"] += 1
            slot[p["block"]] = slot.get(p["block"], 0) + 1
    return counts


def check_coverage(converted, n_days, cfg):
    issues = []
    counts = daily_shift_counts(converted, n_days)
    min_staff = int(cfg.setting("每班最低人力", 7) or 7)

    for d in range(1, n_days + 1):
        for s in SHIFTS:
            nn = counts[d][s].get("護理", 0)
            if nn < 1:
                issues.append(f"[護理24hr] 第{d}日 {s} 無護理人員（需≥1）")
        night_tw = counts[d]["E小夜"].get("台籍照服", 0) + counts[d]["N大夜"].get("台籍照服", 0)
        if night_tw < 1:
            issues.append(f"[夜間台籍照服] 第{d}日 夜間無台籍照服員（需≥1）")
        for s in SHIFTS:
            tot = counts[d][s]["total"]
            if tot < min_staff:
                issues.append(f"[人力比1:15] 第{d}日 {s} 僅{tot}人（需≥{min_staff}）")
    return issues, counts


def check_labor(converted, cfg):
    """勞基法：例假(每14天≥2) + 三班順排(不可逆排)。"""
    issues = []
    min_li = int(cfg.setting("每14天最少例假", 2) or 2)
    pt_threshold = int(cfg.setting("兼職判定上班天數", 8) or 8)
    for p in converted:
        days = p["days"]
        nd = p["n_days"]
        workdays = sum(1 for d in range(1, nd + 1)
                       if days.get(d, {}).get("cat") in SHIFTS)
        if workdays < pt_threshold:
            continue
        li = [d for d in range(1, nd + 1) if days.get(d, {}).get("cat") == "例"]
        for start in range(1, nd - 12):
            w = [d for d in li if start <= d < start + 14]
            if len(w) < min_li:
                worked = any(days.get(d, {}).get("is_work") for d in range(start, start + 14))
                if worked:
                    issues.append(f"[例假] {p['name']} 第{start}~{start+13}日 僅{len(w)}例假（需≥{min_li}）")
                    break
        prev = None
        prev_day = None
        for d in range(1, nd + 1):
            info = days.get(d, {})
            if not info.get("is_work") or info["cat"] not in SHIFT_ORDER:
                if info.get("cat") in ("例", "休", "特", "國"):
                    prev = None
                continue
            cur = SHIFT_ORDER[info["cat"]]
            if prev is not None and prev_day == d - 1 and cur < prev:
                issues.append(
                    f"[順排] {p['name']} 第{prev_day}日{_name(prev)}→第{d}日{_name(cur)} 逆排")
            prev = cur
            prev_day = d
    return issues


def _name(o):
    return {0: "白", 1: "小夜", 2: "大夜"}[o]
