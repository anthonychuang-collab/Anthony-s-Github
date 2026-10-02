#!/usr/bin/env python3
"""Fill a floor's 住民日常生活照護表 (.docx) with 白班護理/白班照服/夜班照服 names."""
import sys
import json
import argparse
import re
import calendar
import docx
from docx.oxml.ns import qn
from docx.shared import Pt

CATEGORY_BY_ROLE = {
    "aide_day": "白班照服",
    "aide_night": "夜班照服",
    "nurse_day": "白班護理",
}

NAME_FONT = "KaiTi"
NAME_FONT_SIZE_PT = 8
NAME_BOLD = True


def set_run_font(run, name=NAME_FONT, size_pt=NAME_FONT_SIZE_PT, bold=NAME_BOLD):
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.name = name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = rPr.makeelement(qn("w:rFonts"), {})
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:eastAsia"), name)
    rFonts.set(qn("w:ascii"), name)
    rFonts.set(qn("w:hAnsi"), name)


def lock_table_layout(table):
    table.autofit = False


TITLE_LINE_PATTERN = re.compile(r"\d{2,3}\s*年\s*\d{1,2}\s*月.*姓名")
MAX_RUN_OF_SPACES = 25


def normalize_title_spacing(doc):
    for p in doc.paragraphs:
        if TITLE_LINE_PATTERN.search(p.text):
            for run in p.runs:
                run.text = re.sub(r" {%d,}" % (MAX_RUN_OF_SPACES + 1),
                                  " " * MAX_RUN_OF_SPACES, run.text)


def set_document_font(doc, name="KaiTi"):
    def set_paragraph_font(p):
        for run in p.runs:
            run.font.name = name
            rPr = run._element.get_or_add_rPr()
            rFonts = rPr.find(qn("w:rFonts"))
            if rFonts is None:
                rFonts = rPr.makeelement(qn("w:rFonts"), {})
                rPr.insert(0, rFonts)
            rFonts.set(qn("w:eastAsia"), name)
            rFonts.set(qn("w:ascii"), name)
            rFonts.set(qn("w:hAnsi"), name)
    for p in doc.paragraphs:
        set_paragraph_font(p)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    set_paragraph_font(p)
    for sec in doc.sections:
        for p in sec.header.paragraphs:
            set_paragraph_font(p)
        for p in sec.footer.paragraphs:
            set_paragraph_font(p)


def detect_days_in_month(doc):
    pattern = re.compile(r"(\d{2,3})\s*年\s*(\d{1,2})\s*月")
    for p in doc.paragraphs:
        m = pattern.search(p.text)
        if m:
            western_year = int(m.group(1)) + 1911
            try:
                return calendar.monthrange(western_year, int(m.group(2)))[1]
            except ValueError:
                return None
    return None


_YM_RE = re.compile(r"(\d{2,3})(\s*)年(\s*)(\d{1,2})(\s*)月")


def _replace_span(paragraph, start, end, new_text):
    """把段落文字的 [start, end) 換成 new_text；跨越多個 run 也正確。"""
    pos = 0
    pending = new_text
    for run in paragraph.runs:
        r0, r1 = pos, pos + len(run.text)
        pos = r1
        if r1 <= start or r0 >= end:
            continue
        head = run.text[:start - r0] if start > r0 else ""
        tail = run.text[end - r0:] if end < r1 else ""
        run.text = head + pending + tail
        pending = ""


def set_title_year_month(doc, roc_year, month):
    """把標題的「<民國年> 年 <月> 月」改成指定年月。回傳改到幾處。
    月份位數變多時吃掉前面的空白，讓標題寬度不變、不擠壓後面的欄位。"""
    hits = 0
    for p in doc.paragraphs:
        m = _YM_RE.search(p.text)
        if not m:
            continue
        sp_y, sp_m, sp_after = m.group(2), m.group(3), m.group(5)
        diff = len(str(month)) - len(m.group(4))
        if diff > 0:
            sp_m = sp_m[diff:] if len(sp_m) >= diff else ""
        elif diff < 0:
            sp_m = sp_m + " " * (-diff)
        _replace_span(p, m.start(), m.end(),
                      f"{roc_year}{sp_y}年{sp_m}{month}{sp_after}月")
        hits += 1
    return hits


def clear_cell(cell):
    p = cell.paragraphs[0]
    for run in list(p.runs):
        run.text = ""
    for extra_p in cell.paragraphs[1:]:
        extra_p._element.getparent().remove(extra_p._element)


def _is_label_row(row):
    """白/晚 之類的欄位標籤列（不是資料列，不可清空）。"""
    txt = "".join(c.text for c in row.cells)
    return ("白" in txt and "晚" in txt) and not any(ch.isdigit() for ch in txt)


def blank_out_of_range_days(table, day_map, days_in_month):
    """清掉超出當月天數的欄位內容，但**保留表頭**：
    第 0 列（日期數字）與白/晚標籤列不動，否則表格會被永久破壞，
    該份輸出若被存回去當範本，之後就再也認不出那是第幾天。"""
    if days_in_month is None:
        return
    out_of_range_cols = {col for day, col in day_map.items() if day > days_in_month}
    if not out_of_range_cols:
        return
    for ri, row in enumerate(table.rows):
        if ri == 0 or _is_label_row(row):
            continue
        for col_idx in out_of_range_cols:
            if col_idx < len(row.cells):
                clear_cell(row.cells[col_idx])


def _row_height_val(row):
    trPr = row._tr.find(qn("w:trPr"))
    if trPr is None:
        return 0
    h = trPr.find(qn("w:trHeight"))
    if h is None:
        return 0
    v = h.get(qn("w:val"))
    return int(v) if v and v.isdigit() else 0


def set_row_height(row, val):
    """把列高設為至少 val（twips），避免責任護士列比照服員列小。"""
    tr = row._tr
    trPr = tr.find(qn("w:trPr"))
    if trPr is None:
        trPr = tr.makeelement(qn("w:trPr"), {})
        tr.insert(0, trPr)
    h = trPr.find(qn("w:trHeight"))
    if h is None:
        h = trPr.makeelement(qn("w:trHeight"), {})
        trPr.append(h)
    h.set(qn("w:val"), str(val))
    h.set(qn("w:hRule"), "atLeast")


def equalize_name_rows(table, roles):
    """責任護士列高度＝各姓名列的最大值，讓它不比照服員列小。"""
    rows = [table.rows[ri] for ri in roles.values()]
    if not rows:
        return
    target = max([_row_height_val(r) for r in rows] + [260])
    nd = roles.get("nurse_day")
    if nd is not None:
        set_row_height(table.rows[nd], target)


def find_special_rows(table):
    roles = {}
    for ri, row in enumerate(table.rows):
        c0 = row.cells[0].text.strip()
        if "照服員" in c0:
            c2 = row.cells[2].text.strip() if len(row.cells) > 2 else ""
            if c2 == "白":
                roles["aide_day"] = ri
            elif c2 in ("晚", "夜"):
                roles["aide_night"] = ri
        elif "責任護士" in c0:
            roles["nurse_day"] = ri
    return roles


def build_day_column_map(table):
    header = table.rows[0]
    day_map = {}
    for ci, cell in enumerate(header.cells):
        text = cell.text.strip()
        if text.isdigit():
            day = int(text)
            if day not in day_map:
                day_map[day] = ci
    return day_map


def _cell_groups(row):
    """把一列依『同一個合併儲存格』分組，回傳 [(cell, [欄索引...]), ...]。"""
    groups, last_tc = [], None
    for ci, cell in enumerate(row.cells):
        if last_tc is not None and cell._tc is last_tc:
            groups[-1][1].append(ci)
        else:
            groups.append((cell, [ci]))
            last_tc = cell._tc
    return groups


def restore_missing_day_headers(table, days_in_month):
    """範本日期列最後幾格沒寫號碼時，依前面的規律補上（只補當月有效日）。

    機構的空白表單常把第 31 格留白（手寫或排版使然），
    導致程式認不出那是第 31 天、該欄永遠空著。
    僅在「該格確實是日期欄」（寬度與其他日期欄相同、且白/晚標籤列對應位置
    有班別標籤）時才補，避免誤寫到裝飾欄位。"""
    if days_in_month is None or not table.rows:
        return 0
    groups = _cell_groups(table.rows[0])
    numbered = [(i, int(c.text.strip())) for i, (c, _) in enumerate(groups)
                if c.text.strip().isdigit()]
    if not numbered:
        return 0
    last_i, last_day = numbered[-1]
    width = len(groups[last_i][1])
    label_row = next((r for r in table.rows if _is_label_row(r)), None)

    added = 0
    day = last_day
    for gi in range(last_i + 1, len(groups)):
        cell, cols = groups[gi]
        if cell.text.strip():
            break
        if len(cols) != width:
            break
        if label_row is not None:
            lab = "".join(label_row.cells[ci].text for ci in cols
                          if ci < len(label_row.cells))
            if "白" not in lab and "晚" not in lab:
                break
        day += 1
        if day > days_in_month:
            break
        run = cell.paragraphs[0].add_run(str(day))
        src = groups[last_i][0].paragraphs[0]
        if src.runs:                      # 沿用既有日期的字型大小
            run.font.size = src.runs[0].font.size
            run.bold = src.runs[0].bold
        cell.paragraphs[0].alignment = groups[last_i][0].paragraphs[0].alignment
        added += 1
    return added


def set_cell_name(cell, name):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    p = cell.paragraphs[0]
    for run in list(p.runs):
        run.text = ""
    if p.runs:
        p.runs[0].text = name
        set_run_font(p.runs[0])
    else:
        set_run_font(p.add_run(name))
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for extra_p in cell.paragraphs[1:]:
        extra_p._element.getparent().remove(extra_p._element)


def fill(template_path, assignments_path, floor, output_path,
         roc_year=None, month=None):
    """roc_year/month 有給時，以它為準改寫標題並決定當月天數；
    未給時沿用範本標題自行偵測（CLI 直接套舊範本時的行為）。"""
    with open(assignments_path, "r", encoding="utf-8") as f:
        assignments = json.load(f)
    if floor not in assignments:
        raise SystemExit(f"Floor '{floor}' not found (available: {list(assignments.keys())})")
    floor_data = assignments[floor]

    d = docx.Document(template_path)
    if not d.tables:
        raise SystemExit("No tables found in the template docx.")

    set_document_font(d, "KaiTi")
    normalize_title_spacing(d)

    if roc_year is not None and month is not None:
        # 以呼叫端指定的年月為準：範本是哪個月都沒關係
        hits = set_title_year_month(d, roc_year, month)
        days_in_month = calendar.monthrange(roc_year + 1911, month)[1]
        print(f"Set title to {roc_year}/{month} ({hits} place(s)); "
              f"{days_in_month} day(s) in this month.")
        if hits == 0:
            print("WARNING: 範本中找不到「<年>年 <月>月」標題，年月未改寫",
                  file=sys.stderr)
    else:
        days_in_month = detect_days_in_month(d)
        if days_in_month is None:
            print("WARNING: could not detect '<年>年 <月>月'", file=sys.stderr)
        else:
            print(f"Detected {days_in_month} day(s) in this month.")

    filled_days = set()
    for table in d.tables:
        roles = find_special_rows(table)
        if not roles:
            continue
        if restore_missing_day_headers(table, days_in_month):
            pass          # 範本尾端未編號的日期欄，已依當月天數補上號碼
        day_map = build_day_column_map(table)
        if not day_map:
            continue
        blank_out_of_range_days(table, day_map, days_in_month)
        lock_table_layout(table)
        equalize_name_rows(table, roles)
        # 每個姓名列先整列清空（日期欄起），再只填當月有效日；
        # 如此超出當月天數的欄位（如 9 月的第 31 欄、或範本右側多出的空欄）一律留白。
        first_day_col = min(day_map.values())
        for role, row_idx in roles.items():
            category = CATEGORY_BY_ROLE[role]
            row = table.rows[row_idx]
            for ci in range(first_day_col, len(row.cells)):
                clear_cell(row.cells[ci])
            for day, col_idx in day_map.items():
                if days_in_month is not None and day > days_in_month:
                    continue
                name = floor_data.get(str(day), {}).get(category)
                if not name or col_idx >= len(row.cells):
                    continue
                set_cell_name(row.cells[col_idx], name)
                filled_days.add(day)

    d.save(output_path)
    print(f"Saved {output_path}. Filled data for {len(filled_days)} day(s).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template_docx")
    ap.add_argument("assignments_json")
    ap.add_argument("floor", choices=["2F", "3F", "5F"])
    ap.add_argument("output_docx")
    args = ap.parse_args()
    fill(args.template_docx, args.assignments_json, args.floor, args.output_docx)


if __name__ == "__main__":
    main()
