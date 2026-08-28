# -*- coding: utf-8 -*-
"""從 PDF 版 T 班擷取每人每日原始碼（列印版備援；建議仍以 xlsx 為主）。"""
import re
import pdfplumber

ROLE_TAGS = {"PT", "書記", "照服組長", "特助", "社工", "SW", "組長", "書 記"}
# 合法班別碼
CODE_RE = re.compile(r"^(R|特|國|公|休|例|C|K|/|[DNE][A-Za-z0-9.*+\-]{0,3}|[235][DNE][A-Za-z0-9]{0,2})$")


def _is_num(tok):
    return bool(re.match(r"^\d+$", str(tok)))


def _has_cjk(tok):
    return bool(re.search(r"[一-鿿]", str(tok)))


def read(path, n_days=None):
    lines = []
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            lines += (p.extract_text() or "").split("\n")

    if n_days is None:
        n_days = 31
        for ln in lines:
            toks = ln.split()
            seq = [int(t) for t in toks if _is_num(t)]
            if seq and 1 in seq:
                run = 1
                while (run + 1) in seq:
                    run += 1
                if run >= 28:
                    n_days = run
                    break

    rows = []
    for ln in lines:
        toks = ln.split()
        if not toks:
            continue
        i = 0
        while i < len(toks) and (toks[i] in ROLE_TAGS or re.match(r"^特\d$", toks[i])):
            i += 1
        if i >= len(toks) or not _has_cjk(toks[i]):
            continue
        name = toks[i]
        j = i + 1
        # 跳過姓名後的識別欄（員工代碼/排班#等，可能 1~2 個），直到第一個合法班別碼
        account_toks = []
        while j < len(toks) and not CODE_RE.match(toks[j]):
            account_toks.append(toks[j])
            j += 1
        account = next((a for a in account_toks if _is_num(a)),
                       account_toks[0] if account_toks else "")
        codes = toks[j:j + n_days]
        valid = sum(1 for c in codes if CODE_RE.match(c))
        if len(codes) < n_days or valid < n_days * 0.6:
            continue
        days = {d: (codes[d - 1] if codes[d - 1] not in ("", "-") else None)
                for d in range(1, n_days + 1)}
        rows.append({"name": name, "account": account, "days": days})

    return {"n_days": n_days, "rows": rows}
