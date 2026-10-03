# -*- coding: utf-8 -*-
"""F 班系統測試套件（零依賴，python3 tests/test_fban.py）。"""
import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fban.config import Config, Person, HeadStaff
from fban.codes import CodeBook, leading_floor
from fban.convert import assign_rest, _place_li, convert_person, convert_foreign_code
from fban.coverage import check_coverage, check_labor
from fban.fillin import auto_fill
from fban import writer, read_fban
import tempfile, os as _os

_PASS = _FAIL = 0
def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1; print(f"  ✅ {name}")
    else:
        _FAIL += 1; print(f"  ❌ {name}  {detail}")
def eq(name, got, want):
    check(name, got == want, f"got={got!r} want={want!r}")

CODE_MAP = [
    {"T班原始碼": "Di", "F班顯示碼": "D4x", "班別大類": "D白"},
    {"T班原始碼": "2Di", "F班顯示碼": "D4x", "班別大類": "D白"},
    {"T班原始碼": "3Di", "F班顯示碼": "D4x", "班別大類": "D白"},
    {"T班原始碼": "D", "F班顯示碼": "D4x", "班別大類": "D白"},
    {"T班原始碼": "D6", "F班顯示碼": "D6x", "班別大類": "D白"},
    {"T班原始碼": "E", "F班顯示碼": "Ex", "班別大類": "E小夜"},
    {"T班原始碼": "N", "F班顯示碼": "Nx", "班別大類": "N大夜"},
]
COLOR_RULES = [
    {"區塊": "護理", "班別大類": "D白", "樓層": "2F", "RGB(ARGB)": "FF70AD47"},
    {"區塊": "護理", "班別大類": "D白", "樓層": "3F", "RGB(ARGB)": "FF5B9BD5"},
    {"區塊": "護理", "班別大類": "D白", "樓層": "5F", "RGB(ARGB)": "FFFF2F92"},
    {"區塊": "護理", "班別大類": "E小夜", "樓層": "*", "RGB(ARGB)": "FFED7D31"},
    {"區塊": "護理", "班別大類": "N大夜", "樓層": "*", "RGB(ARGB)": "FF44546A"},
    {"區塊": "台籍照服", "班別大類": "D白", "樓層": "5F", "RGB(ARGB)": "FFFF2F92"},
    {"區塊": "外籍照服", "班別大類": "D白", "樓層": "3F", "RGB(ARGB)": "FF5B9BD5"},
    {"區塊": "外籍照服", "班別大類": "N大夜", "樓層": "5F", "RGB(ARGB)": "FFD9D9D9"},
]
def make_cfg(**settings):
    cfg = Config(); cfg.code_map = CODE_MAP; cfg.color_rules = COLOR_RULES
    cfg.settings = {"每14天最少例假": 2, "西元年": 2026, "月份": 8, "每班最低人力": 7}
    cfg.settings.update(settings)
    return cfg
def days_from(codes):
    return {"name": "X", "account": "1", "days": {i+1: c for i, c in enumerate(codes)}}


def test_codebook_nursing():
    cb = CodeBook(CODE_MAP)
    eq("Di→D4x/D白", cb.lookup("Di")[:2], ("D4x", "D白"))
    eq("2Di 樓層=2F", cb.lookup("2Di")[2], "2F")
    eq("3Di 樓層=3F", cb.lookup("3Di")[2], "3F")
    eq("E→Ex", cb.lookup("E")[:2], ("Ex", "E小夜"))
    eq("N→Nx", cb.lookup("N")[:2], ("Nx", "N大夜"))

def test_codebook_foreign_both_orders():
    cb = CodeBook(CODE_MAP)
    eq("D3a→Dx", cb.lookup("D3a")[0], "Dx")
    eq("D3a 樓層=3F", cb.lookup("D3a")[2], "3F")
    eq("3Da→Dx", cb.lookup("3Da")[0], "Dx")
    eq("N5a→Nx", cb.lookup("N5a")[0], "Nx")
    eq("N5a 樓層=5F", cb.lookup("N5a")[2], "5F")
    eq("D5b→Dx", cb.lookup("D5b")[0], "Dx")

def test_codebook_pt_and_kitchen():
    cb = CodeBook(CODE_MAP)
    eq("Ep→其他", cb.lookup("Ep")[1], "其他")
    eq("Dp→其他", cb.lookup("Dp")[1], "其他")
    eq("C→其他", cb.lookup("C")[1], "其他")
    eq("K→其他", cb.lookup("K")[1], "其他")

def test_leading_floor():
    eq("2Di 前綴=2F", leading_floor("2Di"), "2F")
    eq("Di 無前綴", leading_floor("Di"), None)

def test_assign_rest_quota_counts():
    rest = [1, 4, 8, 12, 16, 20, 24, 28, 31]
    labels = assign_rest(rest, 2, None, {"例": 5, "休": 4, "國": 0}, set())
    eq("配額5例→恰5例", sum(1 for v in labels.values() if v == "例"), 5)
    eq("其餘為休", sum(1 for v in labels.values() if v == "休"), 4)

def test_assign_rest_quota_guo_on_holiday():
    labels = assign_rest([1, 5, 10, 15, 20, 25], 2, None, {"例": 4, "休": 0, "國": 2}, {5, 20})
    check("國定假日確切日→標國", labels.get(5) == "國" and labels.get(20) == "國", labels)
    eq("國恰2天", sum(1 for v in labels.values() if v == "國"), 2)

def test_assign_rest_no_quota_alternate():
    labels = assign_rest([2, 5, 9, 13], 2, None, None, None)
    check("無配額≥2例", sum(1 for v in labels.values() if v == "例") >= 2, labels)

def test_place_li_spread():
    li = _place_li([1, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30], 5, 2)
    eq("place_li 回傳5個", len(li), 5)
    check("例假有分散(跨月首尾)", min(li) <= 6 and max(li) >= 24, sorted(li))

def test_convert_nursing_codes_and_color():
    cfg = make_cfg()
    conv = convert_person(Person(name="甲", block="護理"),
                          days_from(["Di", "2Di", "3Di", "E", "N", "R", "R"]), CodeBook(CODE_MAP), cfg)
    d = conv["days"]
    eq("Di→D4x", d[1]["code"], "D4x")
    eq("Di 5F紅", d[1]["color"], "FFFF2F92")
    eq("2Di 2F綠", d[2]["color"], "FF70AD47")
    eq("3Di 3F藍", d[3]["color"], "FF5B9BD5")
    eq("E→Ex橘", (d[4]["code"], d[4]["color"]), ("Ex", "FFED7D31"))
    eq("N→Nx灰", (d[5]["code"], d[5]["color"]), ("Nx", "FF44546A"))
    check("R→例或休", d[6]["code"] in ("例", "休", "國"), d[6])

def test_white_code_by_block_and_allowed():
    cfg = make_cfg(); cb = CodeBook(CODE_MAP)
    eq("護理白→D4x", convert_person(Person(name="護", block="護理"), days_from(["D"]), cb, cfg)["days"][1]["code"], "D4x")
    eq("台籍白→D5x", convert_person(Person(name="台", block="台籍照服"), days_from(["D"]), cb, cfg)["days"][1]["code"], "D5x")
    eq("台籍勾D6x→D6x", convert_person(Person(name="台6", block="台籍照服", allowed={"D6x","Ex","Nx"}), days_from(["D"]), cb, cfg)["days"][1]["code"], "D6x")

def test_person_head_name():
    eq("人頭核章=牌照持有人", Person(name="借牌員", block="護理", stamp_name="持牌員").record_name, "持牌員")
    eq("本人核章=自己", Person(name="甲", block="護理").record_name, "甲")

def test_coverage_flags_shortfall():
    cfg = make_cfg()
    p = convert_person(Person(name="甲", block="護理"),
                       {"name":"甲","account":"1","days":{d:"Di" for d in range(1,4)}}, CodeBook(CODE_MAP), cfg)
    issues, _ = check_coverage([p], 3, cfg)
    check("偵測白班<7", any("僅" in s for s in issues), issues[:3])
    check("偵測缺護理", any("護理" in s for s in issues), issues[:3])

def test_labor_pt_filter():
    cfg = make_cfg(); cb = CodeBook(CODE_MAP)
    pt = convert_person(Person(name="PT員", block="護理"), days_from(["E","E","E"]+["/"]*28), cb, cfg)
    check("PT不報例假", not any("PT員" in s for s in check_labor([pt], cfg)), "")

def test_labor_detects_reverse_order():
    cfg = make_cfg(); cb = CodeBook(CODE_MAP)
    p = convert_person(Person(name="逆", block="護理"), days_from(["N","Di"]+["Di"]*10), cb, cfg)
    check("偵測逆排 大夜→白", any("順排" in s for s in check_labor([p], cfg)), "")

def test_fill_availability_gao():
    cfg = make_cfg()
    cfg.head_pool = [HeadStaff(name="高偲芸", category="護理", avail_from=(115,8,20))]
    heads, _ = auto_fill([], 31, cfg)
    gao = next((h for h in heads if h["name"] == "高偲芸"), None)
    if gao:
        eq("高偲芸8/20前不上班", [d for d in range(1,20) if gao["days"][d]["is_work"]], [])

def test_fill_meets_minimums():
    cfg = make_cfg(白班目標人數=1, 小夜目標人數=1, 大夜目標人數=1)
    cfg.head_pool = ([HeadStaff(name=f"護{i}", category="護理") for i in range(6)] +
                     [HeadStaff(name=f"台{i}", category="台籍照服") for i in range(6)])
    heads, _ = auto_fill([], 5, cfg)
    _, counts = check_coverage(heads, 5, cfg)
    ok = all(counts[d][s].get("護理",0) >= 1 for d in range(1,6) for s in ["D白","E小夜","N大夜"])
    check("補人頭後每班護理≥1", ok, "")

def test_fill_head_no_labor_violation():
    cfg = make_cfg(白班目標人數=1, 小夜目標人數=1, 大夜目標人數=1)
    cfg.head_pool = [HeadStaff(name=f"護{i}", category="護理") for i in range(8)] + \
                    [HeadStaff(name=f"台{i}", category="台籍照服") for i in range(8)]
    heads, _ = auto_fill([], 31, cfg)
    eq("人頭班0勞基法違規", check_labor(heads, cfg), [])

def test_convert_foreign_code_helper():
    eq("2Da→Dax(舊helper)", convert_foreign_code("2Da"), "Dax")
    eq("3Nb→Nbx(舊helper)", convert_foreign_code("3Nb"), "Nbx")

def _mk(name, block, record, per_day):
    days = {}
    for d in range(1, 4):
        cat, fl = per_day.get(d, (None, None))
        days[d] = {"code": cat, "cat": cat, "floor": fl, "is_work": cat in ("D白","E小夜","N大夜")}
    return {"name": name, "record_name": record, "block": block, "shift_kind": "", "n_days": 3, "days": days}

def test_docgen_restraint():
    from fban import docgen
    conv = [_mk("護A","護理","牌照A",{1:("D白","2F"),2:("D白","3F")}),
            _mk("護B","護理","護B",{1:("N大夜",None)}),
            _mk("護C","護理","護C",{1:("E小夜",None)})]
    data = docgen.restraint_floor_data(conv, 3, prev_night="前月大夜")
    eq("2F白=牌照A", data[1]["2F"]["白班"], "牌照A")
    eq("第1天大夜=上月最後一天", data[1]["2F"]["大夜"], "前月大夜")
    eq("第2天大夜=班表第1天大夜(往前推一天)", data[2]["2F"]["大夜"], "護B")
    eq("小夜共用護C(當日)", data[1]["3F"]["小夜"], "護C")

def test_docgen_namecopy():
    from fban import docgen
    conv = [_mk("護A","護理","護A",{1:("D白","2F")}),
            _mk("台A","台籍照服","台A",{1:("D白","2F")}),
            _mk("台N","台籍照服","台N",{1:("E小夜","2F")}),
            _mk("外A","外籍照服","外A",{1:("N大夜","2F")})]
    a = docgen.namecopy_assignments(conv, 3)
    eq("2F白班護理", a["2F"]["1"]["白班護理"], "護A")
    eq("2F白班照服=台籍", a["2F"]["1"]["白班照服"], "台A")
    eq("2F夜班照服=台籍(非外籍)", a["2F"]["1"]["夜班照服"], "台N")


def _mk_head(name, block, record, per_day, is_head=False):
    p = _mk(name, block, record, per_day)
    p["is_head"] = is_head
    return p

def test_docgen_avoid_head_nurse():
    """同日同樓層兩位白班：責任護士取實際護理，跳過護理長(is_head)。"""
    from fban import docgen
    # 護理長排在前面，仍應取後面的實際責任護士
    conv = [_mk_head("護理長", "護理", "護理長", {1: ("D白", "2F")}, is_head=True),
            _mk_head("曾素靖", "護理", "曾素靖", {1: ("D白", "2F")}, is_head=False)]
    data = docgen.restraint_floor_data(conv, 3)
    eq("2F白避開護理長→曾素靖", data[1]["2F"]["白班"], "曾素靖")
    # 只有護理長在該樓白班時，仍要顯示護理長（不留白）
    conv2 = [_mk_head("護理長", "護理", "護理長", {1: ("D白", "3F")}, is_head=True)]
    data2 = docgen.restraint_floor_data(conv2, 3)
    eq("3F只剩護理長→仍取護理長", data2[1]["3F"]["白班"], "護理長")

def test_readfban_real_format():
    """機構原生版面：多分頁依月份挑、欄位靠標題對位、theme/RGB 底色判樓層、護理長班種D0。"""
    import openpyxl
    from openpyxl.styles import PatternFill
    cfg = make_cfg()
    wb = openpyxl.Workbook()
    wb.active.title = "115.08"          # 舊月份（不應被選到）
    wb.active["A1"] = "舊月份不選"
    ws = wb.create_sheet("115.09")      # 目標月份
    # 日期列：從第 11 欄起 1..30
    for d in range(1, 31):
        ws.cell(4, 10 + d, d)
    # 區塊表頭列
    hdr = {4: "帳號", 5: "核章人員", 6: "護理人員", 7: "班種"}
    for c, v in hdr.items():
        ws.cell(5, c, v)
    green = PatternFill("solid", fgColor="FF70AD47")   # 2F
    # 護理長(班種 D0)與實際護理，第1日都 2F 白
    ws.cell(6, 4, "R001"); ws.cell(6, 5, "顏欣盈"); ws.cell(6, 6, "顏欣盈"); ws.cell(6, 7, "D0")
    ws.cell(6, 11, "D4x").fill = green
    ws.cell(7, 4, "R190"); ws.cell(7, 6, "曾素靖")   # 核章空→用姓名
    ws.cell(7, 11, "D4x").fill = green
    tmp = _os.path.join(tempfile.gettempdir(), "test_real_F.xlsx")
    wb.save(tmp)
    conv, nd = read_fban.load(tmp, cfg, "115.09")
    eq("依月份挑到 115.09(30天)", nd, 30)
    names = {p["name"] for p in conv if p["block"] == "護理"}
    check("讀到護理兩人", names == {"顏欣盈", "曾素靖"}, f"got={names}")
    byname = {p["name"]: p for p in conv}
    eq("底色判樓層=2F", byname["曾素靖"]["days"][1]["floor"], "2F")
    eq("班種D0→is_head", byname["顏欣盈"]["is_head"], True)
    eq("核章空→回姓名", byname["曾素靖"]["record_name"], "曾素靖")
    from fban import docgen
    data = docgen.restraint_floor_data(conv, nd)
    eq("責任護士避開護理長→曾素靖", data[1]["2F"]["白班"], "曾素靖")


def _mk_full(name, block, rec, per, cfg):
    """建立含 color 的 converted person（供 writer 寫出）。"""
    days = {}
    for d in range(1, 32):
        c = per.get(d)
        cat = (c if c in ("例", "休", "國") else
               "D白" if c and c[0] == "D" else
               "E小夜" if c == "Ex" else "N大夜" if c == "Nx" else "空")
        info = {"code": c, "cat": cat, "floor": per.get(("fl", d)),
                "color": None, "is_work": c in ("D4x", "D5x", "Dx", "Ex", "Nx")}
        if info["is_work"]:
            if not info["floor"]:
                info["floor"] = "5F"
            info["color"] = cfg.color_for(block, cat, info["floor"])
        days[d] = info
    return {"name": name, "record_name": rec, "account": "X", "block": block,
            "shift_kind": "", "n_days": 31, "days": days}

def test_readfban_roundtrip():
    """US-7：F班寫出→讀回，人數/區塊/樓層/班別/核章 還原正確。"""
    cfg = make_cfg(週起始星期=6)
    conv = [
        _mk_full("顏欣盈", "護理", "顏欣盈",
                 {**{d: "D4x" for d in range(1, 32)}, **{("fl", d): "2F" for d in range(1, 32)}}, cfg),
        _mk_full("何承祐", "護理", "何承祐", {d: "Nx" for d in range(1, 32)}, cfg),
        _mk_full("借牌員", "護理", "持牌員",  # 人頭：核章≠姓名（虛構例，非實際同仁）
                 {**{d: "D4x" for d in range(1, 32)}, **{("fl", d): "3F" for d in range(1, 32)}}, cfg),
    ]
    tmp = _os.path.join(tempfile.gettempdir(), "test_rt_F.xlsx")
    writer.write(conv, 31, cfg, tmp, "115.08")
    # 牌照持有人本人也要在人員主檔中，核章才會被採信（查無此人者一律忽略）
    cfg.people.append(Person(name="持牌員", block="護理"))
    conv2, nd = read_fban.load(tmp, cfg)
    eq("讀回天數=31", nd, 31)
    eq("讀回人數=3", len([p for p in conv2 if p["block"] == "護理"]), 3)
    byname = {p["name"]: p for p in conv2}
    eq("顏欣盈 第1日=D白", byname["顏欣盈"]["days"][1]["cat"], "D白")
    eq("顏欣盈 第1日樓層=2F(由底色)", byname["顏欣盈"]["days"][1]["floor"], "2F")
    eq("何承祐 第1日=N大夜", byname["何承祐"]["days"][1]["cat"], "N大夜")
    eq("人頭文件用名=持牌員(牌照持有人)", byname["借牌員"]["record_name"], "持牌員")
    eq("人頭名冊欄=借牌員(實際同仁)", byname["借牌員"]["name"], "借牌員")
    eq("人頭核章欄另存=持牌員", byname["借牌員"]["stamp"], "持牌員")

def test_readfban_feeds_docgen():
    """US-7→US-8：讀回的資料能正確產生約束表指派。"""
    from fban import docgen
    cfg = make_cfg(週起始星期=6)
    conv = [
        _mk_full("顏欣盈", "護理", "顏欣盈",
                 {**{d: "D4x" for d in range(1, 32)}, **{("fl", d): "2F" for d in range(1, 32)}}, cfg),
        _mk_full("何承祐", "護理", "何承祐", {d: "Nx" for d in range(1, 32)}, cfg),
        _mk_full("黃安宇", "護理", "黃安宇", {d: "Ex" for d in range(1, 32)}, cfg),
    ]
    tmp = _os.path.join(tempfile.gettempdir(), "test_rt_F2.xlsx")
    writer.write(conv, 31, cfg, tmp, "115.08")
    conv2, nd = read_fban.load(tmp, cfg)
    data = docgen.restraint_floor_data(conv2, nd, prev_night="上月大夜")
    eq("2F白=顏欣盈", data[1]["2F"]["白班"], "顏欣盈")
    eq("第1天大夜=上月最後一天", data[1]["2F"]["大夜"], "上月大夜")
    eq("第2天大夜=何承祐(往前推一天)", data[2]["2F"]["大夜"], "何承祐")
    eq("小夜=黃安宇", data[1]["2F"]["小夜"], "黃安宇")


def test_namecopy_blank_31_in_30day_month():
    """9 月（30天）：照護表第 31 欄（及右側多餘欄）不得有姓名。"""
    try:
        import docx
    except Exception:
        print("  ⏭ 略過（無 python-docx）"); return
    from docx import Document
    import sys as _sys
    _sys.path.insert(0, _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "docskills", "namecopy"))
    import importlib, json
    fcr = importlib.import_module("fill_care_record")
    # 造一個含 1..31 日欄 + 責任護士列的最小範本，並在第 31 欄預填殘留姓名
    d = Document()
    d.add_paragraph("115 年 9 月  姓名:")
    t = d.add_table(rows=2, cols=1 + 31)
    t.rows[0].cells[0].text = "日期"
    for day in range(1, 32):
        t.rows[0].cells[day].text = str(day)
    t.rows[1].cells[0].text = "責任護士 簽名"
    t.rows[1].cells[31].text = "殘留人"          # 第31欄殘留
    tmp = _os.path.join(tempfile.gettempdir(), "tpl_care.docx"); d.save(tmp)
    aj = _os.path.join(tempfile.gettempdir(), "asg.json")
    with open(aj, "w", encoding="utf-8") as f:
        json.dump({"2F": {str(x): {"白班護理": f"護{x}"} for x in range(1, 31)}}, f, ensure_ascii=False)
    out = _os.path.join(tempfile.gettempdir(), "care_out.docx")
    fcr.fill(tmp, aj, "2F", out)
    d2 = Document(out); row = d2.tables[0].rows[1]
    eq("第30欄有名", row.cells[30].text.strip(), "護30")
    eq("第31欄留白(9月無31)", row.cells[31].text.strip(), "")


def test_readfban_roundtrip_blocks():
    """迴歸：F班寫出→讀回，三個區塊要各自還原，不能全部落到護理。
    （writer 在表頭上一列寫的是「護理人員／台籍照服員／外籍照服員」全稱，
      read_fban 若只認短稱，會把每個人都當成護理，照護表的照服欄就會全空。）"""
    from fban import docgen
    cfg = make_cfg(週起始星期=6)
    conv = [
        _mk_full("護理甲", "護理", "護理甲",
                 {**{d: "D4x" for d in range(1, 32)}, **{("fl", d): "2F" for d in range(1, 32)}}, cfg),
        # 樓層須挑測試設定中有顏色規則者（台籍照服白=5F、外籍照服白=3F）
        _mk_full("台照乙", "台籍照服", "台照乙",
                 {**{d: "D5x" for d in range(1, 32)}, **{("fl", d): "5F" for d in range(1, 32)}}, cfg),
        _mk_full("外照丙", "外籍照服", "外照丙",
                 {**{d: "Dx" for d in range(1, 32)}, **{("fl", d): "3F" for d in range(1, 32)}}, cfg),
    ]
    tmp = _os.path.join(tempfile.gettempdir(), "test_rt_blocks.xlsx")
    writer.write(conv, 31, cfg, tmp, "115.08")
    conv2, nd = read_fban.load(tmp, cfg)
    got = {p["name"]: p["block"] for p in conv2}
    eq("護理甲 區塊=護理", got.get("護理甲"), "護理")
    eq("台照乙 區塊=台籍照服", got.get("台照乙"), "台籍照服")
    eq("外照丙 區塊=外籍照服", got.get("外照丙"), "外籍照服")
    # 區塊對了，照護表的「白班照服」才取得到台籍照服員
    assigns = docgen.namecopy_assignments(conv2, nd)
    eq("照護表2F白班護理=護理甲", assigns["2F"]["1"]["白班護理"], "護理甲")
    eq("照護表5F白班照服=台照乙(只取台籍)", assigns["5F"]["1"]["白班照服"], "台照乙")
    eq("照護表3F白班照服不取外籍", assigns["3F"]["1"]["白班照服"], "")


def test_head_name_same_on_both_paths():
    """迴歸：人頭在兩條路徑上，文件印的姓名必須一致（皆為牌照持有人）。
    路徑一＝T班轉出的 converted；路徑二＝寫出F班再讀回。
    read_fban 若改成取名冊欄姓名，這裡會抓到兩條路徑不一致。"""
    cfg = make_cfg(週起始星期=6)
    cb = CodeBook(CODE_MAP)
    # 路徑一：後台主檔有核章人員(牌照持有人)
    p1 = convert_person(Person(name="借牌員", block="護理", stamp_name="持牌員"),
                        days_from(["Di"] * 31), cb, cfg)
    eq("路徑一 文件用名=持牌員", p1["record_name"], "持牌員")
    # 路徑二：把同一個人寫進 F 班再讀回
    conv = [_mk_full("借牌員", "護理", "持牌員",
                     {**{d: "D4x" for d in range(1, 32)},
                      **{("fl", d): "2F" for d in range(1, 32)}}, cfg)]
    tmp = _os.path.join(tempfile.gettempdir(), "test_head_paths.xlsx")
    writer.write(conv, 31, cfg, tmp, "115.08")
    cfg.people.append(Person(name="持牌員", block="護理"))
    conv2, _ = read_fban.load(tmp, cfg)
    p2 = next(x for x in conv2 if x["name"] == "借牌員")
    eq("路徑二 文件用名=持牌員", p2["record_name"], "持牌員")
    eq("兩條路徑文件用名一致", p1["record_name"], p2["record_name"])


def test_tsheet_date_formats():
    """T 班日期列同時支援純數字與 10/1(四) 這種寫法。"""
    from fban import tsheet
    # 純數字
    eq("整數 1", tsheet._day_num(1), 1)
    eq("字串 '15'", tsheet._day_num("15"), 15)
    eq("超出範圍 2398→None", tsheet._day_num(2398), None)
    # 新版 月/日(星期)
    eq("'10/1(四)'→1", tsheet._day_num("10/1(四)"), 1)
    eq("'10/31(六)'→31", tsheet._day_num("10/31(六)"), 31)
    eq("'9/2'→2", tsheet._day_num("9/2"), 2)
    eq("代碼 '2Di'→None", tsheet._day_num("2Di"), None)
    eq("'/'空班→None", tsheet._day_num("/"), None)
    # 用新版版面(第1列標題含 10/1(四)…)實際讀一份
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active
    ws.cell(1, 1, "姓名"); ws.cell(1, 2, "人員班別代碼")
    for d in range(1, 31):
        ws.cell(1, 2 + d, f"10/{d}(一)")
    ws.cell(2, 1, "顏欣盈"); ws.cell(2, 2, 15)
    for d in range(1, 31):
        ws.cell(2, 2 + d, "2Di" if d % 2 else "R")
    tmp = _os.path.join(tempfile.gettempdir(), "t_newfmt.xlsx"); wb.save(tmp)
    got = tsheet.read(tmp)
    eq("新版讀到30天", got["n_days"], 30)
    eq("新版日期列在第1列", got["day_row"], 1)
    eq("新版第1欄=姓名", got["rows"][0]["name"], "顏欣盈")
    eq("新版第1天碼=2Di", got["rows"][0]["days"][1], "2Di")


def test_aide_split_by_master_list():
    """照服合併檔：由『人員主檔』名單自動分台籍/外籍。"""
    from fban import config as cfgmod
    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    cfgpath = _os.path.join(root, "後台設定.xlsx")
    if not _os.path.exists(cfgpath):
        print("  ⏭ 略過(無後台設定.xlsx)"); return
    cfg = cfgmod.load(cfgpath)
    tw = cfg.person_by_name("洪瑞輝")
    fn = cfg.person_by_name("阮氏秋賢")
    check("洪瑞輝→台籍照服", tw is not None and tw.block == "台籍照服", str(tw and tw.block))
    check("阮氏秋賢→外籍照服", fn is not None and fn.block == "外籍照服", str(fn and fn.block))
    check("未列主檔者查無(產生時歸台籍並標記)", cfg.person_by_name("查無此人甲乙") is None, "")


def test_renamed_person_prints_new_name():
    """迴歸：兩筆曾被誤記為「借牌照」的同仁，主檔不得留核章人員，文件一律印本人姓名。
      - 陳詡善：原名陳淑萍，是改名，不是借牌
      - 洪瑞輝：核章人員欄原誤填王淑環，是填錯，本人即核章
    若核章人員欄被填回去，文件會印成別人的名字，這裡會抓到。"""
    from fban import config as cfgmod
    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    cfgpath = _os.path.join(root, "後台設定.xlsx")
    if not _os.path.exists(cfgpath):
        print("  ⏭ 略過(無後台設定.xlsx)"); return
    cfg = cfgmod.load(cfgpath)
    p = cfg.person_by_name("陳詡善")
    check("陳詡善在人員主檔中", p is not None, "")
    if p is None:
        return
    eq("陳詡善文件用名=陳詡善(新名)", p.record_name, "陳詡善")
    check("陳詡善未掛核章人員(改名非借牌)", not p.stamp_name, f"stamp_name={p.stamp_name!r}")
    # 主檔任何欄位都不該再出現舊名
    import openpyxl
    ws = openpyxl.load_workbook(cfgpath)["人員主檔"]
    hits = [c.coordinate for r in ws.iter_rows() for c in r
            if isinstance(c.value, str) and "陳淑萍" in c.value and c.column != ws.max_column]
    check("人員主檔的姓名/核章欄不再有舊名陳淑萍", not hits, str(hits))
    # 洪瑞輝：核章人員欄原誤填王淑環
    h = cfg.person_by_name("洪瑞輝")
    check("洪瑞輝在人員主檔中", h is not None, "")
    if h is not None:
        eq("洪瑞輝文件用名=洪瑞輝(本人)", h.record_name, "洪瑞輝")
        check("洪瑞輝未掛核章人員(原誤填)", not h.stamp_name, f"stamp_name={h.stamp_name!r}")
    hits2 = [c.coordinate for r in ws.iter_rows() for c in r
             if isinstance(c.value, str) and "王淑環" in c.value and c.column != ws.max_column]
    check("人員主檔的姓名/核章欄不再有王淑環", not hits2, str(hits2))


def test_namecopy_month_comes_from_request_not_template():
    """迴歸：照護表的年月與天數要以『使用者選的月份』為準，不是範本標題。
    範本停在 9 月時，產 10 月必須改寫標題為 10 月，且第 31 欄要保留並填入。"""
    try:
        import docx
    except Exception:
        print("  ⏭ 略過（無 python-docx）"); return
    from docx import Document
    import sys as _sys, importlib, json, calendar
    _sys.path.insert(0, _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "docskills", "namecopy"))
    fcr = importlib.import_module("fill_care_record")

    # 造一個標題寫「115 年 9 月」、但日期欄有 1..31 的範本
    d = Document()
    d.add_paragraph("115年   9 月      姓名:")
    t = d.add_table(rows=2, cols=1 + 31)
    t.rows[0].cells[0].text = "日期"
    for day in range(1, 32):
        t.rows[0].cells[day].text = str(day)
    t.rows[1].cells[0].text = "責任護士 簽名"
    tpl = _os.path.join(tempfile.gettempdir(), "tpl_month.docx"); d.save(tpl)
    aj = _os.path.join(tempfile.gettempdir(), "asg_month.json")
    with open(aj, "w", encoding="utf-8") as f:
        json.dump({"2F": {str(x): {"白班護理": f"護{x}"} for x in range(1, 32)}},
                  f, ensure_ascii=False)

    # 指定 10 月（31 天）
    out = _os.path.join(tempfile.gettempdir(), "care_10.docx")
    fcr.fill(tpl, aj, "2F", out, roc_year=115, month=10)
    d2 = Document(out)
    title = next(p.text for p in d2.paragraphs if "年" in p.text and "月" in p.text)
    check("標題改為 10 月", "10 月" in title or "10月" in title, title)
    check("標題不再是 9 月", "9 月" not in title.replace("19 月", ""), title)
    row = d2.tables[0].rows[1]
    eq("第31欄有填(10月有31天)", row.cells[31].text.strip(), "護31")
    eq("第31欄日期標題保留", d2.tables[0].rows[0].cells[31].text.strip(), "31")

    # 同一份範本指定 9 月（30 天）→ 第 31 欄留白
    out9 = _os.path.join(tempfile.gettempdir(), "care_09.docx")
    fcr.fill(tpl, aj, "2F", out9, roc_year=115, month=9)
    d3 = Document(out9)
    eq("9月：第30欄有填", d3.tables[0].rows[1].cells[30].text.strip(), "護30")
    eq("9月：第31欄留白", d3.tables[0].rows[1].cells[31].text.strip(), "")


def test_set_title_year_month_keeps_width():
    """標題改月份時維持寬度：位數變多就吃掉前面的空白，不擠壓後面欄位。"""
    try:
        import docx
    except Exception:
        print("  ⏭ 略過（無 python-docx）"); return
    from docx import Document
    import sys as _sys, importlib
    _sys.path.insert(0, _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "docskills", "namecopy"))
    fcr = importlib.import_module("fill_care_record")
    d = Document(); d.add_paragraph("115年   9 月      姓名:")
    before = d.paragraphs[0].text
    eq("改到 1 處", fcr.set_title_year_month(d, 115, 10), 1)
    after = d.paragraphs[0].text
    eq("9→10 後總長度不變", len(after), len(before))
    check("內容為 10 月", "10 月" in after, after)
    eq("10→9 再改回來", fcr.set_title_year_month(d, 115, 9), 1)
    eq("改回後與原標題相同", d.paragraphs[0].text, before)


def test_build_namecopy_passes_month_through():
    """迴歸：docgen.build_namecopy 必須把年月傳給 fill()。
    這正是 115.10 產出卻印成 9 月、只有 30 天的成因——
    build_namecopy 有 roc_year/month 卻沒往下傳，月份只好由範本標題決定。"""
    try:
        import docx
    except Exception:
        print("  ⏭ 略過（無 python-docx）"); return
    from docx import Document
    from fban import docgen
    # 範本標題停在 9 月，但日期欄有 1..31
    d = Document()
    d.add_paragraph("115年   9 月      姓名:")
    t = d.add_table(rows=2, cols=1 + 31)
    t.rows[0].cells[0].text = "日期"
    for day in range(1, 32):
        t.rows[0].cells[day].text = str(day)
    t.rows[1].cells[0].text = "責任護士 簽名"
    tpl = _os.path.join(tempfile.gettempdir(), "tpl_bn.docx"); d.save(tpl)

    cfg = make_cfg(週起始星期=6)
    conv = [_mk_full("護甲", "護理", "護甲",
                     {**{x: "D4x" for x in range(1, 32)},
                      **{("fl", x): "2F" for x in range(1, 32)}}, cfg)]
    outdir = _os.path.join(tempfile.gettempdir(), "bn_out")
    paths = docgen.build_namecopy(conv, 31, 115, 10, {"2F": tpl}, outdir)
    check("有產出檔案", bool(paths), str(paths))
    if not paths:
        return
    d2 = Document(paths[0])
    title = next(p.text for p in d2.paragraphs if "年" in p.text and "月" in p.text)
    check("標題依指定月份改為 10 月(非範本的9月)", "10 月" in title or "10月" in title, title)
    eq("第31欄日期標題保留(10月有31天)",
       d2.tables[0].rows[0].cells[31].text.strip(), "31")
    eq("第31欄填入護甲", d2.tables[0].rows[1].cells[31].text.strip(), "護甲")


def _care_tpl_with_blank_last_day(path, n_cols=31, blank_last=True):
    """造一個照護表範本：日期列 1..n，最後一欄可留白（模擬機構空白表單）。
    另含白/晚標籤列，供日期欄判定。"""
    from docx import Document
    d = Document()
    d.add_paragraph("115年   9 月      姓名:")
    t = d.add_table(rows=3, cols=1 + n_cols)
    t.rows[0].cells[0].text = "日期"
    for day in range(1, n_cols + 1):
        if blank_last and day == n_cols:
            continue                      # 最後一格留白
        t.rows[0].cells[day].text = str(day)
    t.rows[1].cells[0].text = "班別"
    for ci in range(1, n_cols + 1):
        t.rows[1].cells[ci].text = "白 晚"
    t.rows[2].cells[0].text = "責任護士 簽名"
    d.save(path)
    return path


def test_restore_blank_last_day_header():
    """迴歸：範本日期列最後一格留白（機構空白表單如此）時，
    產 31 天的月份要把『31』補回去並填入姓名；30 天的月份則不可補。"""
    try:
        import docx
    except Exception:
        print("  ⏭ 略過（無 python-docx）"); return
    from docx import Document
    import sys as _sys, importlib, json
    _sys.path.insert(0, _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "docskills", "namecopy"))
    fcr = importlib.import_module("fill_care_record")

    tpl = _care_tpl_with_blank_last_day(
        _os.path.join(tempfile.gettempdir(), "tpl_blank31.docx"))
    aj = _os.path.join(tempfile.gettempdir(), "asg_blank31.json")
    with open(aj, "w", encoding="utf-8") as f:
        json.dump({"2F": {str(x): {"白班護理": f"護{x}"} for x in range(1, 32)}},
                  f, ensure_ascii=False)

    out10 = _os.path.join(tempfile.gettempdir(), "blank31_10.docx")
    fcr.fill(tpl, aj, "2F", out10, roc_year=115, month=10)
    d10 = Document(out10)
    eq("10月：第31欄日期補回", d10.tables[0].rows[0].cells[31].text.strip(), "31")
    eq("10月：第31欄填入姓名", d10.tables[0].rows[2].cells[31].text.strip(), "護31")

    out9 = _os.path.join(tempfile.gettempdir(), "blank31_9.docx")
    fcr.fill(tpl, aj, "2F", out9, roc_year=115, month=9)
    d9 = Document(out9)
    eq("9月：第31欄不補日期", d9.tables[0].rows[0].cells[31].text.strip(), "")
    eq("9月：第31欄不填姓名", d9.tables[0].rows[2].cells[31].text.strip(), "")
    eq("9月：第30欄仍有姓名", d9.tables[0].rows[2].cells[30].text.strip(), "護30")


def test_blank_out_of_range_keeps_headers():
    """迴歸：清空越界日時不可動到日期列與白/晚標籤列。
    否則產一次 30 天的月份就會把『31』與『白 晚』永久擦掉，
    該輸出若被存回去當範本，之後就再也認不出那一欄。"""
    try:
        import docx
    except Exception:
        print("  ⏭ 略過（無 python-docx）"); return
    from docx import Document
    import sys as _sys, importlib, json
    _sys.path.insert(0, _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "docskills", "namecopy"))
    fcr = importlib.import_module("fill_care_record")

    tpl = _care_tpl_with_blank_last_day(
        _os.path.join(tempfile.gettempdir(), "tpl_full31.docx"), blank_last=False)
    aj = _os.path.join(tempfile.gettempdir(), "asg_full31.json")
    with open(aj, "w", encoding="utf-8") as f:
        json.dump({"2F": {str(x): {"白班護理": f"護{x}"} for x in range(1, 32)}},
                  f, ensure_ascii=False)
    out = _os.path.join(tempfile.gettempdir(), "full31_9.docx")
    fcr.fill(tpl, aj, "2F", out, roc_year=115, month=9)
    d = Document(out)
    eq("30天月份：日期『31』仍在", d.tables[0].rows[0].cells[31].text.strip(), "31")
    check("30天月份：白/晚標籤仍在",
          "白" in d.tables[0].rows[1].cells[31].text, d.tables[0].rows[1].cells[31].text)
    eq("30天月份：第31欄姓名留白", d.tables[0].rows[2].cells[31].text.strip(), "")


def test_new_day_cell_copies_row_formatting():
    """迴歸：範本空白格（例未編號的第31欄）填入姓名時，字型/大小/顏色要跟同列其他日相同。
    之前只設字型大小不設顏色，新建的 run 會變成預設黑色，整份只有 31 號是黑的。"""
    try:
        import docx
    except Exception:
        print("  ⏭ 略過（無 python-docx）"); return
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.oxml.ns import qn
    import sys as _sys, importlib, json
    _sys.path.insert(0, _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "docskills", "namecopy"))
    fcr = importlib.import_module("fill_care_record")

    # 範本：1..30 的姓名格已帶淺灰格式，第31欄日期與姓名格都是空的
    d = Document()
    d.add_paragraph("115年   9 月      姓名:")
    t = d.add_table(rows=3, cols=32)
    t.rows[0].cells[0].text = "日期"
    for day in range(1, 31):
        t.rows[0].cells[day].text = str(day)
    t.rows[1].cells[0].text = "班別"
    for ci in range(1, 32):
        t.rows[1].cells[ci].text = "白 晚"
    t.rows[2].cells[0].text = "責任護士 簽名"
    for ci in range(1, 31):
        r = t.rows[2].cells[ci].paragraphs[0].add_run("")
        r.font.size = Pt(8); r.font.bold = True
        r.font.color.rgb = RGBColor(0xAE, 0xAB, 0xAB)
    tpl = _os.path.join(tempfile.gettempdir(), "tpl_fmt.docx"); d.save(tpl)
    aj = _os.path.join(tempfile.gettempdir(), "asg_fmt.json")
    with open(aj, "w", encoding="utf-8") as f:
        json.dump({"2F": {str(x): {"白班護理": f"護{x}"} for x in range(1, 32)}},
                  f, ensure_ascii=False)
    out = _os.path.join(tempfile.gettempdir(), "fmt_out.docx")
    fcr.fill(tpl, aj, "2F", out, roc_year=115, month=10)

    d2 = Document(out)
    row = d2.tables[0].rows[2]
    def color_of(ci):
        runs = row.cells[ci].paragraphs[0].runs
        if not runs:
            return None
        rPr = runs[0]._element.find(qn("w:rPr"))
        c = rPr.find(qn("w:color")) if rPr is not None else None
        return c.get(qn("w:val")) if c is not None else None
    eq("第30日有姓名", row.cells[30].text.strip(), "護30")
    eq("第31日有姓名", row.cells[31].text.strip(), "護31")
    eq("第30日顏色為範本的淺灰", color_of(30), "AEABAB")
    eq("第31日顏色與第30日相同", color_of(31), color_of(30))
    r30 = row.cells[30].paragraphs[0].runs[0]
    r31 = row.cells[31].paragraphs[0].runs[0]
    eq("第31日字級與第30日相同", r31.font.size, r30.font.size)
    eq("第31日粗體與第30日相同", r31.font.bold, r30.font.bold)


def test_unknown_stamp_name_detected():
    """核章人員的忽略清單：載入後台設定時記錄，供報告與畫面提示。
    （行為面的驗證見 test_unknown_stamp_is_ignored_not_printed）"""
    from fban import config as cfgmod
    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    cfgpath = _os.path.join(root, "後台設定.xlsx")
    if not _os.path.exists(cfgpath):
        print("  ⏭ 略過(無後台設定.xlsx)"); return
    cfg = cfgmod.load(cfgpath)
    check("實際後台設定無查無此人的核章人員",
          not cfgmod.unknown_stamp_names(cfg), str(cfgmod.unknown_stamp_names(cfg)))
    check("清單與 ignored_stamps 一致",
          cfgmod.unknown_stamp_names(cfg) == list(cfg.ignored_stamps), "")

def test_unknown_stamp_is_ignored_not_printed():
    """迴歸：核章人員指向主檔查無的人時，一律忽略、印本人姓名。
    舊的後台設定或舊的 F 班殘留這種值（例：洪瑞輝→王淑環）時，
    絕不可把不存在的同仁印到稽核文件上。"""
    from fban import config as cfgmod
    import openpyxl, shutil
    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    cfgpath = _os.path.join(root, "後台設定.xlsx")
    if not _os.path.exists(cfgpath):
        print("  ⏭ 略過(無後台設定.xlsx)"); return

    # 路徑一：後台設定殘留查無此人的核章人員
    bad = _os.path.join(tempfile.gettempdir(), "cfg_badstamp.xlsx")
    shutil.copy(cfgpath, bad)
    wb = openpyxl.load_workbook(bad); ws = wb["人員主檔"]
    hdr = [c.value for c in ws[1]]
    i_name = hdr.index("姓名") + 1
    i_stamp = hdr.index("核章人員(人頭牌照,留空=本人)") + 1
    target_row = next(r for r in range(2, ws.max_row + 1) if ws.cell(r, i_name).value)
    who = str(ws.cell(target_row, i_name).value).strip()
    ws.cell(target_row, i_stamp, "查無此人甲")
    wb.save(bad)
    cfg = cfgmod.load(bad)
    eq(f"{who} 文件用名為本人", cfg.person_by_name(who).record_name, who)
    check("已記錄被忽略的核章人員",
          (who, "查無此人甲") in cfg.ignored_stamps, str(cfg.ignored_stamps))
    check("報告用的清單也看得到",
          (who, "查無此人甲") in cfgmod.unknown_stamp_names(cfg), "")

    # 路徑二：上傳的 F 班裡那一欄殘留查無此人
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill
    good = cfgmod.load(cfgpath)
    wb2 = Workbook(); ws2 = wb2.active; ws2.title = "115.10"
    ws2.cell(3, 5, "台籍照服員")
    for h, c in (("序", 1), ("帳號", 2), ("核章人員", 3), ("人員", 4), ("班種", 5)):
        ws2.cell(4, c, h)
    for d in range(1, 32):
        ws2.cell(3, 5 + d, d)
    ws2.cell(5, 1, 1); ws2.cell(5, 3, "查無此人乙"); ws2.cell(5, 4, "洪瑞輝")
    fill = PatternFill("solid", fgColor="FFFF2F92")
    for d in range(1, 32):
        c = ws2.cell(5, 5 + d, "D5x"); c.fill = fill
    fp = _os.path.join(tempfile.gettempdir(), "F_badstamp.xlsx"); wb2.save(fp)
    conv, _ = read_fban.load(fp, good, "115.10")
    check("讀到人員", bool(conv), "")
    if conv:
        eq("上傳路徑 文件用名為本人", conv[0]["record_name"], "洪瑞輝")
        eq("原始核章欄值仍保留供查核", conv[0]["stamp"], "查無此人乙")


def run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        print(f"\n▶ {t.__name__}")
        try:
            t()
        except Exception:
            global _FAIL; _FAIL += 1; print("  ❌ 例外："); traceback.print_exc()
    print(f"\n{'='*40}\n總計：{_PASS} 通過 / {_FAIL} 失敗")
    return _FAIL


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
