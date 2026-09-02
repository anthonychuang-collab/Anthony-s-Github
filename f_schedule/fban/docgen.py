# -*- coding: utf-8 -*-
"""工作流下游文件產生：把 F 班資料轉成
  1) 約束評估記錄單（restraint）— 每樓層一份 Word
  2) 住民日常生活照護表（namecopy）— 每樓層一份 Word（需使用者提供範本）

作法：用系統已知的每日每樓層每班別核章姓名，餵給兩個 skill 的 docx 產生引擎。
姓名一律用 record_name（人頭牌照持有人＝實際核章姓名）。
"""
import os
import sys
import json

_HERE = os.path.dirname(os.path.abspath(__file__))
_DOCSKILLS = os.path.join(os.path.dirname(_HERE), "docskills")
sys.path.insert(0, os.path.join(_DOCSKILLS, "restraint"))
sys.path.insert(0, os.path.join(_DOCSKILLS, "namecopy"))

FLOORS = ["2F", "3F", "5F"]
RESTRAINT_TEMPLATE = os.path.join(_DOCSKILLS, "restraint", "blank_template.docx")


def _nurses(converted):
    return [p for p in converted if p["block"] == "護理"]


def _tw_aides(converted):
    """照護表的照服欄位由『台籍照服員』核章，不取外籍。"""
    return [p for p in converted if p["block"] == "台籍照服"]


def _pick(people, day, cat, floor=None, avoid_head=False):
    """挑當日符合(班別大類, 樓層)的人；回傳核章姓名。
    avoid_head=True 時，若同格有多位，優先跳過護理長(is_head)，除非只剩護理長。"""
    fallback = ""
    for p in people:
        info = p["days"].get(day, {})
        if not info.get("is_work"):
            continue
        if info.get("cat") != cat:
            continue
        if floor is not None and info.get("floor") != floor:
            continue
        nm = p.get("record_name") or p["name"]
        if avoid_head and p.get("is_head"):
            if not fallback:
                fallback = nm
            continue
        return nm
    return fallback


def institution_last_night(converted, n_days):
    """該月最後一天的大夜護理（跨月銜接用：本月最後一天大夜＝下月1日的大夜格）。"""
    return _pick(_nurses(converted), n_days, "N大夜")


# ---------------- 約束評估記錄單 ----------------
def restraint_floor_data(converted, n_days, prev_night=""):
    """{day:{'2F':{大夜,白班,小夜}, '3F':..., '5F':...}}（護理姓名）。

    大夜班跨午夜：約束表第 D 天凌晨 00:00~08:00 的大夜，是「班表第 (D-1) 天大夜」
    那位護理值到隔天早上。故大夜往前推一天；第 1 天用上月最後一天大夜（prev_night）。
    """
    nurses = _nurses(converted)
    data = {}
    for d in range(1, n_days + 1):
        night = prev_night if d == 1 else _pick(nurses, d - 1, "N大夜")
        eve = _pick(nurses, d, "E小夜")
        data[d] = {}
        for fl in FLOORS:
            data[d][fl] = {
                "白班": _pick(nurses, d, "D白", fl, avoid_head=True),
                "小夜": eve,
                "大夜": night,
            }
    return data


def build_restraint(converted, n_days, roc_year, month, outdir, prev_night=""):
    import gen_form
    os.makedirs(outdir, exist_ok=True)
    data = restraint_floor_data(converted, n_days, prev_night)
    paths = []
    for fl in FLOORS:
        assign = {d: data[d][fl] for d in data}
        out = os.path.join(outdir, f"{roc_year}{month:02d}約束評估記錄單-{fl}.docx")
        gen_form.build(RESTRAINT_TEMPLATE, roc_year, month, out, assignments=assign)
        paths.append(out)
    return paths


# ---------------- 住民日常生活照護表 ----------------
def namecopy_assignments(converted, n_days):
    """{floor:{day:{白班護理,白班照服,夜班照服}}}（皆用核章姓名；照服只取台籍）。"""
    nurses = _nurses(converted)
    aides = _tw_aides(converted)
    out = {fl: {} for fl in FLOORS}
    for d in range(1, n_days + 1):
        for fl in FLOORS:
            day_nurse = _pick(nurses, d, "D白", fl, avoid_head=True)
            day_aide = _pick(aides, d, "D白", fl)
            night_aide = _pick(aides, d, "E小夜", fl) or _pick(aides, d, "N大夜", fl)
            out[fl][str(d)] = {
                "白班護理": day_nurse,
                "白班照服": day_aide,
                "夜班照服": night_aide,
            }
    return out


def build_namecopy(converted, n_days, roc_year, month, templates, outdir):
    """templates: {floor: 範本docx路徑}。回傳產出的檔案路徑清單。"""
    import fill_care_record
    os.makedirs(outdir, exist_ok=True)
    assigns = namecopy_assignments(converted, n_days)
    aj = os.path.join(outdir, "_assignments.json")
    with open(aj, "w", encoding="utf-8") as f:
        json.dump(assigns, f, ensure_ascii=False)
    paths = []
    for fl in FLOORS:
        tpl = templates.get(fl)
        if not tpl or not os.path.exists(tpl):
            continue
        out = os.path.join(outdir, f"{roc_year}{month:02d}住民日常生活照護表-{fl}.docx")
        fill_care_record.fill(tpl, aj, fl, out)
        paths.append(out)
    return paths
