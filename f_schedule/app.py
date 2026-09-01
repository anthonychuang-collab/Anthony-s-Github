# -*- coding: utf-8 -*-
"""F 班自動排定 — 網頁介面（登入 + 產F班 + 下游文件工作流）。"""
import os
import re
import sys
import io
import uuid
import zipfile
import socket
import secrets
import functools
import datetime
from flask import (Flask, request, render_template, send_file,
                   redirect, url_for, abort, session)

from generate_fban import run
from fban import docgen, read_fban, pdfexport
from fban import config as cfgmod

if getattr(sys, "frozen", False):
    BUNDLE = sys._MEIPASS
    BASE = os.path.dirname(sys.executable)
else:
    BUNDLE = BASE = os.path.dirname(os.path.abspath(__file__))

CONFIG = os.path.join(BASE, "後台設定.xlsx")
WORK = os.path.join(BASE, "runtime")
os.makedirs(WORK, exist_ok=True)

# 後台範本儲存：照護表各樓層範本只在後台存一次，之後每月自動沿用。
STORE = os.path.join(BASE, "後台範本")
os.makedirs(STORE, exist_ok=True)
CARE_FLOORS = ("2F", "3F", "5F")


def _stored_care_tpl(fl):
    """回傳該樓層已存於後台的照護表範本路徑，沒有則 None。"""
    p = os.path.join(STORE, f"照護表_{fl}.docx")
    return p if os.path.exists(p) else None


def _care_tpl_status():
    """各樓層後台範本狀態：{'2F': {'set': True, 'mtime': '...'}, ...}。"""
    out = {}
    for fl in CARE_FLOORS:
        p = _stored_care_tpl(fl)
        if p:
            ts = datetime.datetime.fromtimestamp(os.path.getmtime(p))
            out[fl] = {"set": True, "mtime": ts.strftime("%Y-%m-%d %H:%M")}
        else:
            out[fl] = {"set": False, "mtime": None}
    return out

if not os.path.exists(CONFIG):
    try:
        import build_config_template
        build_config_template.build(CONFIG)
        print(f"（已自動產生預設後台設定：{CONFIG}）")
    except Exception as _e:
        print(f"（提醒：找不到後台設定.xlsx，自動產生失敗：{_e}）")

PASSWORD = os.environ.get("FBAN_PASSWORD", "dazhong123")
SECRET = os.environ.get("FBAN_SECRET", secrets.token_hex(16))

app = Flask(__name__,
            template_folder=os.path.join(BUNDLE, "templates"),
            static_folder=os.path.join(BUNDLE, "static"))
app.secret_key = SECRET
app.config["MAX_CONTENT_LENGTH"] = 40 * 1024 * 1024

BLOCKS = [("nurse", "護理", "護理 T 班"),
          ("tw", "台籍照服", "台籍照服 T 班"),
          ("foreign", "外籍照服", "外籍照服 T 班")]
JOBS = {}


def login_required(view):
    @functools.wraps(view)
    def wrapped(*a, **k):
        if not session.get("ok"):
            return redirect(url_for("login", next=request.path))
        return view(*a, **k)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (request.form.get("password") or "") == PASSWORD:
            session["ok"] = True
            return redirect(request.args.get("next") or url_for("index"))
        return render_template("login.html", error="密碼錯誤，請重新輸入")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def _safe_ext(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext if ext in (".xlsx", ".xlsm", ".pdf") else None


def _guess_month():
    now = datetime.date.today()
    return f"{now.year - 1911}.{now.month:02d}"


@app.route("/")
@login_required
def index():
    return render_template("index.html", blocks=BLOCKS, default_month=_guess_month())


@app.route("/generate", methods=["POST"])
@login_required
def generate():
    month = (request.form.get("month") or "").strip()
    if not re.match(r"^\d{3}\.\d{1,2}$", month):
        return render_template("index.html", blocks=BLOCKS, default_month=_guess_month(),
                               error="月份格式請填 民國年.月，例如 115.08")
    fill = request.form.get("fill") == "on"
    token = uuid.uuid4().hex[:12]
    job_dir = os.path.join(WORK, token)
    os.makedirs(job_dir, exist_ok=True)

    t_specs = []
    got_any = False
    for key, block, _label in BLOCKS:
        f = request.files.get(key)
        if not f or not f.filename:
            continue
        ext = _safe_ext(f.filename)
        if not ext:
            return render_template("index.html", blocks=BLOCKS, default_month=month,
                                   error=f"{_label}檔案格式不支援（僅 .xlsx/.pdf）")
        save_as = os.path.join(job_dir, f"{key}{ext}")
        f.save(save_as)
        got_any = True
        if ext == ".pdf":
            t_specs.append((save_as, None, block))
        else:
            sheet = (request.form.get(f"{key}_sheet") or "").strip() or None
            t_specs.append((save_as, sheet, block))
    if not got_any:
        return render_template("index.html", blocks=BLOCKS, default_month=month,
                               error="請至少上傳一個班表檔案")

    out_path = os.path.join(job_dir, f"{month}_F班.xlsx")
    report_path = os.path.join(job_dir, f"{month}_檢核報告.txt")
    try:
        summary = run(CONFIG, t_specs, out_path, report_path, month_label=month, fill=fill)
    except Exception as e:
        return render_template("index.html", blocks=BLOCKS, default_month=month,
                               error=f"產生失敗：{e}")

    m = month.split(".")
    JOBS[token] = {"out": out_path, "report": report_path, "month": month,
                   "converted": summary["converted"], "n_days": summary["n_days"],
                   "roc": int(m[0]), "mon": int(m[1]), "dir": job_dir}
    return render_template("result.html", s=summary, token=token, month=month)


@app.route("/docs", methods=["GET", "POST"])
@login_required
def docs_home():
    """上傳自己的 F 班（本系統格式 xlsx）→ 直接進入文件工作流。"""
    if request.method == "GET":
        return render_template("docs.html", default_month=_guess_month())
    month = (request.form.get("month") or "").strip()
    if not re.match(r"^\d{3}\.\d{1,2}$", month):
        return render_template("docs.html", default_month=_guess_month(),
                               error="月份格式請填 民國年.月，例如 115.08")
    f = request.files.get("fban")
    if not f or not f.filename or not f.filename.lower().endswith((".xlsx", ".xlsm")):
        return render_template("docs.html", default_month=month,
                               error="請上傳 F 班 xlsx（本系統產生的格式）")
    token = uuid.uuid4().hex[:12]
    job_dir = os.path.join(WORK, token)
    os.makedirs(job_dir, exist_ok=True)
    path = os.path.join(job_dir, "F.xlsx")
    f.save(path)
    try:
        cfg = cfgmod.load(CONFIG)
        converted, n_days = read_fban.load(path, cfg, month)
    except Exception as e:
        return render_template("docs.html", default_month=month, error=f"讀取失敗：{e}")
    if not converted:
        return render_template("docs.html", default_month=month,
                               error=f"讀不到任何人員。請確認檔案裡有『{month}』這個月份的分頁，"
                                     "且欄位含「核章人員／護理人員／班種」與日期列。")
    n_nurse = sum(1 for p in converted if p["block"] == "護理")
    if n_nurse < 2:
        return render_template("docs.html", default_month=month,
                               error=f"只讀到 {len(converted)} 位人員（護理 {n_nurse} 位），"
                                     f"疑似欄位或月份分頁對不上，已中止以免產出空白表單。"
                                     f"請確認上傳檔含『{month}』分頁且版面正確。")
    m = month.split(".")
    JOBS[token] = {"month": month, "converted": converted, "n_days": n_days,
                   "roc": int(m[0]), "mon": int(m[1]), "dir": job_dir,
                   "out": path, "report": None}
    return redirect(url_for("workflow", token=token))


@app.route("/download/<token>/<which>")
@login_required
def download(token, which):
    job = JOBS.get(token)
    if not job:
        abort(404)
    path = job.get("out" if which == "f" else "report")
    if not path or not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


def _with_pdfs(docx_paths, out_dir):
    """在 docx 之外，另用 LibreOffice 產生對應 PDF（定版）。找不到轉檔器則只回 docx。"""
    all_paths = list(docx_paths)
    try:
        all_paths += pdfexport.docx_to_pdf(docx_paths, out_dir)
    except Exception:
        pass
    return all_paths


def _zip_files(paths, zip_name):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, os.path.basename(p))
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=zip_name,
                     mimetype="application/zip")


@app.route("/workflow/<token>")
@login_required
def workflow(token):
    job = JOBS.get(token)
    if not job:
        abort(404)
    return render_template("workflow.html", token=token, month=job["month"],
                           care_status=_care_tpl_status())


@app.route("/make/restraint/<token>", methods=["POST"])
@login_required
def make_restraint(token):
    job = JOBS.get(token)
    if not job:
        abort(404)
    outdir = os.path.join(job["dir"], "restraint")
    paths = docgen.build_restraint(job["converted"], job["n_days"], job["roc"], job["mon"], outdir)
    paths = _with_pdfs(paths, outdir)
    return _zip_files(paths, f"{job['month']}_約束評估記錄單.zip")


@app.route("/make/namecopy/<token>", methods=["POST"])
@login_required
def make_namecopy(token):
    job = JOBS.get(token)
    if not job:
        abort(404)
    tpl_dir = os.path.join(job["dir"], "care_templates")
    os.makedirs(tpl_dir, exist_ok=True)
    templates = {}
    for fl in CARE_FLOORS:
        f = request.files.get("tpl_" + fl)
        if f and f.filename and f.filename.lower().endswith(".docx"):
            # 當次上傳＝臨時覆蓋這個樓層
            path = os.path.join(tpl_dir, f"{fl}.docx")
            f.save(path)
            templates[fl] = path
        else:
            # 沒上傳就用後台已存的範本
            sp = _stored_care_tpl(fl)
            if sp:
                templates[fl] = sp
    if not templates:
        return render_template("workflow.html", token=token, month=job["month"],
                               care_status=_care_tpl_status(),
                               error="尚未設定任何樓層的照護表範本。請先到「後台範本設定」上傳，或在此當場上傳。")
    outdir = os.path.join(job["dir"], "namecopy")
    paths = docgen.build_namecopy(job["converted"], job["n_days"], job["roc"], job["mon"], templates, outdir)
    if paths:
        paths = _with_pdfs(paths, outdir)
    if not paths:
        return render_template("workflow.html", token=token, month=job["month"],
                               care_status=_care_tpl_status(),
                               error="產出失敗：範本結構可能與預期不符")
    return _zip_files(paths, f"{job['month']}_住民日常生活照護表.zip")


@app.route("/settings/templates", methods=["GET", "POST"])
@login_required
def care_templates():
    """後台範本設定：照護表各樓層範本上傳／更換／移除（存後台，之後每月自動沿用）。"""
    msg = err = None
    if request.method == "POST":
        act = request.form.get("action")
        fl = request.form.get("floor")
        if fl not in CARE_FLOORS:
            err = "樓層參數錯誤"
        elif act == "remove":
            p = _stored_care_tpl(fl)
            if p:
                os.remove(p)
                msg = f"已移除 {fl} 照護表範本"
            else:
                err = f"{fl} 尚未設定範本"
        else:  # upload / replace
            f = request.files.get("tpl")
            if not f or not f.filename or not f.filename.lower().endswith(".docx"):
                err = "請選擇 .docx 範本檔"
            else:
                f.save(os.path.join(STORE, f"照護表_{fl}.docx"))
                msg = f"已儲存 {fl} 照護表範本，之後每月自動沿用"
    return render_template("settings_templates.html",
                           status=_care_tpl_status(), msg=msg, err=err)


def _lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _banner(host, port):
    ip = _lan_ip()
    print("=" * 54)
    print(" F 班自動排定系統　已啟動（區網內部使用）")
    print("-" * 54)
    print(f"  本機開啟：http://127.0.0.1:{port}")
    if host == "0.0.0.0":
        print(f"  同網段其他電腦/手機開啟：http://{ip}:{port}")
    print(f"  存取密碼：環境變數 FBAN_PASSWORD" +
          ("（未設定，預設 dazhong123，請盡快更改！）" if "FBAN_PASSWORD" not in os.environ else "（已自訂）"))
    print("  資料僅存在本機，未對外連線。")
    print("=" * 54)


if __name__ == "__main__":
    host = os.environ.get("FBAN_HOST", "0.0.0.0")
    port = int(os.environ.get("FBAN_PORT", "5000"))
    _banner(host, port)
    try:
        from waitress import serve
        serve(app, host=host, port=port, threads=8)
    except ImportError:
        app.run(host=host, port=port, debug=False, threaded=True)
