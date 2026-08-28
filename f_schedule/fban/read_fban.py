# -*- coding: utf-8 -*-
"""讀回「本系統產生的 F 班 xlsx」（可能經人工微調），還原成 converted 資料，
供下游文件工作流使用。讓使用者可『上傳自己的 F 班』而非一定要現場重算。

僅支援本系統 writer.py 產出的版面（四區塊：核章在第3欄、姓名第4欄、
班種第5欄、日期自第6欄起；儲存格底色代表樓層）。
"""
import openpyxl

BLOCK_TITLES = {"護理人員": "護理", "台籍照服員": "台籍照服",
                "外籍照服員": "外籍照服", "社工/行政": "社工", "行政": "行政"}
REST = {"例", "休", "國", "特"}


def _cat_of(code):
    if not code:
        return "空"
    c = str(code)
    if c in REST:
        return c
    if c.startswith("D"):
        return "D白"
    if c.startswith("E"):
        return "E小夜"
    if c.startswith("N"):
        return "N大夜"
    return "其他"


def _fill_argb(cell):
    f = cell.fill
    if f is None or f.patternType is None:
        return None
    c = f.fgColor
    if c is not None and c.type == "rgb":
        return c.rgb
    return None


def load(xlsx_path, cfg):
    """回傳 (converted, n_days)。"""
    # 建 color->floor 反查（只取有指定樓層者）
    color_floor = {}
    for r in cfg.color_rules:
        fl = r.get("樓層")
        if fl and fl != "*":
            color_floor[str(r.get("RGB(ARGB)")).upper()] = fl

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    maxr, maxc = ws.max_row, ws.max_column

    # 找日期欄範圍：從第6欄起連續 1..N
    first_day_col = 6
    n_days = 0
    # 掃描找任一列 F..為 1,2,3…
    for r in range(1, min(maxr, 12) + 1):
        c = first_day_col
        if ws.cell(r, c).value == 1:
            k = 1
            while ws.cell(r, first_day_col + k).value == k + 1:
                k += 1
            if k >= 20:
                n_days = k
                break
    if not n_days:
        n_days = 31

    converted = []
    cur_block = None
    r = 1
    while r <= maxr:
        title = ws.cell(r, 5).value
        if title in BLOCK_TITLES:
            cur_block = BLOCK_TITLES[title]
            r += 2  # 跳過標題列與表頭列
            continue
        if title == "每日每班人力統計":
            break
        if cur_block:
            name = ws.cell(r, 4).value
            if name:
                stamp = ws.cell(r, 3).value
                kind = ws.cell(r, 5).value
                days = {}
                for d in range(1, n_days + 1):
                    cell = ws.cell(r, first_day_col + d - 1)
                    code = cell.value
                    cat = _cat_of(code)
                    argb = _fill_argb(cell)
                    floor = color_floor.get(str(argb).upper()) if argb else None
                    days[d] = {"code": code, "cat": cat, "floor": floor,
                               "color": argb,
                               "is_work": cat in ("D白", "E小夜", "N大夜")}
                converted.append({
                    "name": str(name).strip(),
                    "record_name": (str(stamp).strip() if stamp else str(name).strip()),
                    "account": str(ws.cell(r, 2).value or ""),
                    "block": cur_block,
                    "shift_kind": str(kind or ""),
                    "n_days": n_days,
                    "days": days,
                })
        r += 1
    return converted, n_days
