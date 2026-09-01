# -*- coding: utf-8 -*-
"""把產出的 Word(.docx) 轉一份 PDF（定版用，避免不同電腦開啟時版面跑掉）。

用 LibreOffice(soffice) 無頭轉檔：Mac 主機安裝 LibreOffice 後即可，
標楷體等字型由主機提供。找不到 soffice 時回傳空清單（仍給 Word）。
"""
import os
import shutil
import subprocess

# 常見 soffice 位置（macOS / Linux）
_CANDIDATES = [
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",  # macOS
    "/opt/homebrew/bin/soffice",
    "/usr/local/bin/soffice",
    "/usr/bin/soffice",
    "soffice",
    "libreoffice",
]
_PROFILE = "file:///tmp/lo_fban_profile"  # 獨立設定檔，避免與使用者的 LO 衝突


def find_soffice():
    for c in _CANDIDATES:
        if os.path.isabs(c):
            if os.path.exists(c):
                return c
        else:
            p = shutil.which(c)
            if p:
                return p
    return None


def available():
    return find_soffice() is not None


def docx_to_pdf(paths, out_dir, timeout=180):
    """把一個或多個 docx 轉成 PDF，輸出到 out_dir。回傳成功產生的 PDF 路徑清單。
    找不到 soffice 或轉檔失敗時回傳已成功的部分（可能為空），不丟例外。"""
    soffice = find_soffice()
    if not soffice:
        return []
    if isinstance(paths, str):
        paths = [paths]
    paths = [p for p in paths if p and p.lower().endswith(".docx") and os.path.exists(p)]
    if not paths:
        return []
    os.makedirs(out_dir, exist_ok=True)
    try:
        subprocess.run(
            [soffice, "--headless", "--norestore", "--nolockcheck",
             "-env:UserInstallation=" + _PROFILE,
             "--convert-to", "pdf", "--outdir", out_dir, *paths],
            check=True, timeout=timeout,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    out = []
    for p in paths:
        pdf = os.path.join(out_dir, os.path.splitext(os.path.basename(p))[0] + ".pdf")
        if os.path.exists(pdf):
            out.append(pdf)
    return out
