# -*- coding: utf-8 -*-
"""讀取 T 班（xlsx 月分頁），自動偵測日期列與資料列。
日期列同時支援兩種寫法：純數字 1,2,3…；或 10/1(四)、10/1 這類「月/日(星期)」。"""
import re
import openpyxl
from openpyxl.utils import get_column_letter

_MD_RE = re.compile(r"^\s*\d{1,2}\s*/\s*(\d{1,2})")   # 10/1(四) → 取「日」=1


def _day_num(v):
    """把一格轉成日期號(1..31)；不是日期就回 None。
    支援：整數 1..31、字串 '1'…'31'、'10/1(四)'、'10/1'。"""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if 1 <= v <= 31 else None
    s = str(v).strip()
    m = _MD_RE.match(s)
    if m:
        d = int(m.group(1))
        return d if 1 <= d <= 31 else None
    if s.isdigit():
        d = int(s)
        return d if 1 <= d <= 31 else None
    return None


def _find_day_header(ws, max_scan=15):
    for r in range(1, max_scan + 1):
        for c in range(1, ws.max_column + 1):
            if _day_num(ws.cell(r, c).value) == 1:
                n = 1
                cc = c + 1
                while cc <= ws.max_column and _day_num(ws.cell(r, cc).value) == n + 1:
                    n += 1
                    cc += 1
                if n >= 20:
                    return r, c, n
    raise ValueError("找不到日期標題列（應有連續 1..N，或 10/1(四) 這類日期）")


def _autopick_sheet(wb):
    for name in wb.sheetnames:
        try:
            _find_day_header(wb[name])
            return name
        except ValueError:
            continue
    return wb.sheetnames[-1]


def _label_cols(ws, day_row, first_col, scan_rows=4):
    """在日期欄左側找「姓名」「帳號」標題所在的欄。找不到回 (None, None)。
    T 班版面不一定都是「姓名|帳號|日期…」，少一欄或多一欄都可能，
    所以優先認標題文字，認不出來才退回固定位置。"""
    name_col = acct_col = None
    r0 = max(1, day_row - scan_rows + 1)
    for r in range(r0, day_row + 1):
        for c in range(1, first_col):
            v = ws.cell(r, c).value
            if not isinstance(v, str):
                continue
            t = v.strip()
            if name_col is None and "姓名" in t:
                name_col = c
            elif acct_col is None and "帳號" in t:
                acct_col = c
    return name_col, acct_col


def read(path, sheet=None):
    """回傳 dict：{ 'day_row','first_col','n_days','rows':[{name,account,days:{d:code}}] }
    sheet 留空或找不到時自動挑第一個含日期列的分頁。"""
    wb = openpyxl.load_workbook(path, data_only=True)
    if not sheet or sheet not in wb.sheetnames:
        sheet = _autopick_sheet(wb)
    ws = wb[sheet]
    day_row, first_col, n_days = _find_day_header(ws)
    name_col, acct_col = _label_cols(ws, day_row, first_col)
    if name_col is None:                       # 認不出標題，退回常見版面：日期欄往左兩格
        name_col = max(1, first_col - 2)
    if acct_col is None or acct_col == name_col:
        acct_col = name_col + 1 if name_col + 1 < first_col else None

    people = []
    for r in range(day_row + 1, ws.max_row + 1):
        name = ws.cell(r, name_col).value
        if name is None:
            if all(ws.cell(r + k, name_col).value is None for k in range(0, 4)):
                break
            continue
        name = str(name).strip()
        if not name or name in ("姓名日期", "姓名"):
            continue
        acct = ws.cell(r, acct_col).value if acct_col else None
        days = {}
        for d in range(1, n_days + 1):
            v = ws.cell(r, first_col + d - 1).value
            days[d] = None if v is None else str(v).strip()
        people.append({"name": name, "account": acct, "days": days})

    return {"day_row": day_row, "first_col": first_col,
            "n_days": n_days, "rows": people}
