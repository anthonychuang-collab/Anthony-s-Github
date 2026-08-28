# -*- coding: utf-8 -*-
"""F 班自動產生主程式。"""
import argparse
from fban import config as cfgmod
from fban import tsheet, tsheet_pdf
from fban.config import Person
from fban.codes import CodeBook
from fban.convert import convert_person
from fban.coverage import check_coverage, check_labor
from fban.fillin import auto_fill
from fban.writer import write


def run(config_path, t_specs, out_path, report_path, month_label=None, fill=False):
    cfg = cfgmod.load(config_path)
    codebook = CodeBook(cfg.code_map)
    if month_label is None:
        month_label = str(cfg.setting("民國年月", "115.07"))
    else:
        m = str(month_label).replace("/", ".").split(".")
        if len(m) >= 2 and m[0].isdigit() and m[1].isdigit():
            roc_y, mon = int(m[0]), int(m[1])
            cfg.settings["民國年月"] = month_label
            cfg.settings["西元年"] = roc_y + 1911
            cfg.settings["月份"] = mon

    # 讀入所有 T 班來源
    tmap = {}
    n_days = 0
    for path, sheet, block_hint in t_specs:
        if str(path).lower().endswith(".pdf"):
            data = tsheet_pdf.read(path)
        else:
            data = tsheet.read(path, sheet)
        n_days = max(n_days, data["n_days"])
        for r in data["rows"]:
            tmap[r["name"]] = (r, block_hint)

    converted = []
    unmatched = [p.name for p in cfg.people if p.name not in tmap]
    auto_added = []
    excluded_hit = []
    for name, (trow, block_hint) in tmap.items():
        if name in cfg.exclude:
            excluded_hit.append(name)
            continue
        p = cfg.person_by_name(name)
        if p is None:
            if not block_hint:
                continue
            p = Person(name=name, block=block_hint)
            auto_added.append(f"{name}({block_hint})")
        converted.append(convert_person(p, trow, codebook, cfg))

    pre_issues, _ = check_coverage(converted, n_days, cfg)

    fill_log = []
    n_heads = 0
    if fill:
        head_people, fill_log = auto_fill(converted, n_days, cfg)
        converted += head_people
        n_heads = len(head_people)

    cov_issues, counts = check_coverage(converted, n_days, cfg)
    lab_issues = check_labor(converted, cfg)

    write(converted, n_days, cfg, out_path, month_label)

    lines = []
    lines.append(f"===== {month_label} F 班檢核報告 =====")
    lines.append(f"天數：{n_days}")
    lines.append(f"納入人數：{len(converted)}（護理"
                 f"{sum(1 for p in converted if p['block']=='護理')}、"
                 f"台籍照服{sum(1 for p in converted if p['block']=='台籍照服')}、"
                 f"外籍照服{sum(1 for p in converted if p['block']=='外籍照服')}）")
    if fill:
        lines.append(f"自動補人頭：已補 {n_heads} 位人頭；補班前缺口 {len(pre_issues)} 項 → 補班後 {len(cov_issues)} 項")
    if excluded_hit:
        lines.append(f"\n【已依『排除人員』設定排除（不列入F班）】\n  " + "、".join(excluded_hit))
    if auto_added:
        lines.append(f"\n【主檔沒有、依來源區塊自動納入】\n  " + "、".join(auto_added))
    if unmatched:
        lines.append(f"\n【主檔有列、但 T 班找不到姓名（未納入）】\n  " + "、".join(unmatched))
    if fill_log:
        lines.append("\n【補人頭時無法補足/少休情形】")
        lines += ["  ! " + s for s in fill_log]
    lines.append("\n----- 設立標準檢核（護理24hr／夜間台籍照服／每班≥7人）-----")
    lines += ["  ✔ 全部通過"] if not cov_issues else ["  ✗ " + s for s in cov_issues]
    lines.append("\n----- 勞基法檢核（例假每14天≥2／三班順排）-----")
    lines += ["  ✔ 全部通過"] if not lab_issues else ["  ✗ " + s for s in lab_issues]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"\n已輸出 F 班：{out_path}")
    print(f"已輸出報告：{report_path}")
    shaoxiu_total = sum(len(p.get("shaoxiu", [])) for p in converted)
    return {
        "converted": converted, "cov_issues": cov_issues, "lab_issues": lab_issues,
        "out_path": out_path, "report_path": report_path, "month_label": month_label,
        "n_days": n_days, "n_people": len(converted),
        "n_nurse": sum(1 for p in converted if p["block"] == "護理"),
        "n_tw": sum(1 for p in converted if p["block"] == "台籍照服"),
        "n_foreign": sum(1 for p in converted if p["block"] == "外籍照服"),
        "pre_gap": len(pre_issues), "post_gap": len(cov_issues),
        "lab_count": len(lab_issues), "n_heads": n_heads,
        "shaoxiu_total": shaoxiu_total, "fill_log": fill_log,
        "unmatched": unmatched, "auto_added": auto_added, "excluded_hit": excluded_hit,
        "report_text": "\n".join(lines),
    }


def _parse_t(spec):
    parts = spec.split(":")
    path = parts[0]
    if path.lower().endswith(".pdf"):
        block = parts[1] if len(parts) > 1 else ""
        return path, None, block
    sheet = parts[1] if len(parts) > 1 else "115-07"
    block = parts[2] if len(parts) > 2 else ""
    return path, sheet, block


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="後台設定.xlsx")
    ap.add_argument("--t", action="append", required=True, help="T班來源 檔名:分頁[:區塊]")
    ap.add_argument("--out", default="F班.xlsx")
    ap.add_argument("--report", default="檢核報告.txt")
    ap.add_argument("--month", default=None)
    ap.add_argument("--fill", action="store_true")
    args = ap.parse_args()
    t_specs = [_parse_t(s) for s in args.t]
    run(args.config, t_specs, args.out, args.report, args.month, fill=args.fill)
