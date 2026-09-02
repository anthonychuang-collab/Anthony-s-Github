# CLAUDE.md — 專案指南（給 Claude Code）

線東大眾護理之家「F 班自動排定系統」。把護理／台籍照服／外籍照服的 **T 班**轉成
上色、補人頭、合規的 **F 班**，並可接著產出約束評估記錄單與住民日常生活照護表。
純本機執行、瀏覽器操作、資料不外流。

## 常用指令

```bash
pip install -r requirements.txt          # openpyxl pdfplumber flask python-docx waitress
python3 tests/test_fban.py               # 跑測試（零依賴，改 code 前後都先跑）
python3 build_config_template.py         # 重新產生 後台設定.xlsx 範本
python app.py                            # 啟動網頁 (http://127.0.0.1:5000，密碼見 FBAN_PASSWORD)
# CLI 直接產 F 班：
python generate_fban.py --config 後台設定.xlsx --t 護理T.pdf:護理 --out F.xlsx --report r.txt --month 115.08 --fill
```

**改任何 code 後，務必先跑 `python3 tests/test_fban.py`，全綠(目前60項)才算沒改壞。**

## 架構

```
fban/                 核心套件（純邏輯，無 web 相依）
├─ config.py          讀 後台設定.xlsx → Config/Person/HeadStaff
├─ codes.py           班別碼解析 CodeBook（Di→D4x、外籍 D3a→Dx…）
├─ tsheet.py          讀 T 班 xlsx（自動偵測日期列/分頁）
├─ tsheet_pdf.py      讀 T 班 PDF（列印版備援）
├─ convert.py         T→F 轉換：碼、例/休/國配額、樓層上色、人頭改名
├─ coverage.py        設立標準＋勞基法檢核
├─ fillin.py          自動補人頭（含少休機制）
├─ writer.py          寫出 F 班 xlsx（四區塊+底色+統計）
├─ read_fban.py       讀 F 班 xlsx（機構原生多分頁＋本系統格式；標題對位、theme色解析、依月份挑分頁）← 上傳路徑用
├─ pdfexport.py       docx→PDF（LibreOffice soffice；找不到則只給 Word）
└─ docgen.py          下游文件：呼叫 docskills 的 gen_form / fill_care_record
generate_fban.py      CLI 主流程 run()（回傳 summary dict）
app.py                Flask 網頁：登入 + 產F班 + 上傳F班 + 文件工作流
templates/  static/   介面(品牌 CI) 與 logo/CSS
docskills/            兩個 skill 的 docx 引擎與約束表範本
tests/test_fban.py    自製零依賴測試（60項）
後台設定.xlsx         唯一要維護的主檔（人員/人頭/顏色/行事曆…）
```

## 資料流（兩條路徑）

1. **自動**：上傳 T 班 → `generate_fban.run()` → converted 資料 → 產 F 班 → 工作流。
2. **上傳**：上傳本系統格式 F 班 xlsx → `read_fban.load()`（讀底色還原 converted）→ 工作流。

`converted` 是核心資料結構：`[{name, record_name, block, n_days, days:{d:{code,cat,floor,color,is_work}}}]`。
下游文件由 `docgen` 從 converted 直接產生（不再讀色），姓名一律用 `record_name`（人頭牌照持有人＝核章）。兩條路徑的 `record_name` 語意必須一致：`config.Person.record_name` 與 `read_fban` 都取核章人員欄、留空才用本人；`tests/test_head_name_same_on_both_paths` 鎖住這點。

## 慣例／注意

- **規則不寫死在程式**：顏色、班別碼、人頭池、行事曆配額全部在 `後台設定.xlsx`，改 Excel 即可。
- 樓層色：2F綠FF70AD47 / 3F藍FF5B9BD5 / 5F紅FFFF2F92；護理小夜橘、大夜灰。
- 例/休/國依〈年度行事曆〉每月配額；例假數嚴守配額，例假硬底線=每14天≥2。
- 文件產生**不需 LibreOffice/字型**（標楷體於 Mac 開檔時算繪）。
- 照護表範本存後台 `後台範本/照護表_{2F,3F,5F}.docx`（`/settings/templates` 維護），產文件時優先用後台範本，工作流當次上傳＝臨時覆蓋。約束表範本內建。
- 上傳 F 班：`read_fban.load(path, cfg, month)` 依月份挑分頁；欄位靠標題（帳號/核章人員/區塊名/班種）自動對位；樓層由儲存格底色（含 theme color→RGB）比對後台〈樓層顏色規則〉。同日同樓層多位白班時，`docgen._pick(..., avoid_head=True)` 會跳過護理長（班種 D0，`read_fban.HEAD_KINDS`）取實際責任護士。
- 每份文件同時輸出 PDF（`pdfexport`，soffice）。app 上傳路徑有低人數警告防呆。
- 環境變數：`FBAN_PASSWORD`（存取密碼）、`FBAN_HOST`/`FBAN_PORT`、`FBAN_SECRET`。
- 詳細規格見 `F班系統_規格書PRD.md`。
