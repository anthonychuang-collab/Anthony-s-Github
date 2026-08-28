# -*- coding: utf-8 -*-
"""T 班班別碼解析與 F 碼對應。"""
import re

FLOOR_BY_DIGIT = {"2": "2F", "3": "3F", "5": "5F"}
REST_TOKENS = {"R"}


def leading_floor(raw):
    """取代碼開頭的樓層數字：2Di->2F, 3Da->3F, Di->None。"""
    m = re.match(r"^([235])", str(raw).strip())
    if m:
        return FLOOR_BY_DIGIT[m.group(1)]
    return None


class CodeBook:
    """封裝『班別碼對照』表，提供 raw T 碼 -> (F碼, 大類, 樓層)。"""

    def __init__(self, code_map_rows):
        self.exact = {}
        for r in code_map_rows:
            raw = str(r.get("T班原始碼") or "").strip()
            if not raw:
                continue
            self.exact[raw] = (
                str(r.get("F班顯示碼") or "").strip(),
                str(r.get("班別大類") or "").strip(),
            )

    def lookup(self, raw):
        """回傳 (F碼, 大類, 樓層)。找不到時盡量以規則推斷。"""
        s = str(raw).strip() if raw is not None else ""
        s = s.rstrip("-")                     # 去除尾註記（如 D2b-）
        floor = leading_floor(s)
        # 兼職/預備班（Ep, Dp, Np…）：顯示原碼但不計入照護人力、不套例假
        if re.match(r"^[DNE]p$", s):
            return s, "其他", None
        if s in self.exact:
            fcode, cat = self.exact[s]
            return fcode, cat, floor
        # 外籍照服碼：[D/N/E][樓層2/3/5][a/b] 或 [樓層][D/N/E][a/b]
        m = re.match(r"^([DNE])([235])([ab])$", s)
        base = fl_digit = ab = None
        if m:
            base, fl_digit, ab = m.group(1), m.group(2), m.group(3)
        else:
            m2 = re.match(r"^([235])([DNE])([ab])$", s)
            if m2:
                base, fl_digit, ab = m2.group(2), m2.group(1), m2.group(3)
        if base:
            # 外籍照服採簡化碼：D2a/N3b -> Dx/Nx/Ex（a/b 不顯示，樓層以底色表示）
            fcode = f"{base}x"
            cat = {"D": "D白", "N": "N大夜", "E": "E小夜"}[base]
            return fcode, cat, FLOOR_BY_DIGIT[fl_digit]
        # 去掉樓層前綴再找一次（例：4Di 未列，但 Di 有列）
        stripped = re.sub(r"^[235]", "", s)
        if stripped in self.exact:
            fcode, cat = self.exact[stripped]
            return fcode, cat, floor
        # 廚房/煮飯等非照護工作碼：保留但不計入照護人力
        if s in ("C", "K", "煮", "廚"):
            return s, "其他", None
        # 仍找不到：原樣回傳
        return s, "未知", floor


def classify(fcode, category):
    """把大類正規化成 D白/E小夜/N大夜/例休/其他，供上色與統計。"""
    if category in ("D白", "E小夜", "N大夜", "例休", "特", "國", "空", "其他"):
        return category
    f = str(fcode)
    if f.startswith("D"):
        return "D白"
    if f.startswith("E"):
        return "E小夜"
    if f.startswith("N"):
        return "N大夜"
    return "其他"
