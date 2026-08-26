# CHANGELOG — 後端正式版

## 2026-08 — 同步原型 v0.5.0(修正7 CIS 視覺 + 修正8 匯入 Excel)

以精確 diff(v0.4.0→v0.5.0)只取這兩塊 delta 套進後端版,先前所有功能與認證/儲存層不受影響。

### 修正8:匯入 Excel
- 新增「⭱ 匯入 Excel」按鈕 + 隱藏的 `<input type="file">`,用既有的 SheetJS(`XLSX`)解析。
- 沿用系統匯出的欄位順序(第0欄姓名、第1欄代碼、第2欄起為每日),用**目前畫面月份**的天數對應,不讀 Excel 表頭判斷月份。
- **姓名完全比對**目前職務的人員;比對不到的列出但不匯入(不自動新增人員)。
- **先預覽再確認**:顯示 `#importPreviewPanel`(比對成功/失敗名單),按「確認匯入」才寫入,「取消」作廢。
- **只覆蓋 Excel 有值的儲存格**,空白不動既有資料;異動寫入 `undoStack`,可 Ctrl+Z 復原。
- 已知限制:不自動偵測月份、姓名需完全相同(不做去空白/簡繁/模糊)、不處理同名同姓、固定假設是本系統匯出的欄位格式。

### 修正7:CIS 品牌視覺微調(純 CSS)
- 面板圓角 14→16px、按鈕圓角 9→11px;面板標題前加品牌主色小圓點(`h3::before`)。
- 頂部副標題改大地棕、登入鈕改品牌主色綠、頁尾水彩漸層加深(opacity 0.5→0.65、高度 12→14px)。
- 健檢人力統計新增 `.zero` 樣式:當天人力為 0 時整格紅底白字(不論門檻),圖例同步說明。

### ⚠️ 相依提醒(離線影響)
匯入與匯出都依賴 CDN 載入的 SheetJS(`cdnjs.cloudflare.com/.../xlsx.full.min.js`),**需要網路**才能用。若要離線也能匯入/匯出,需把 SheetJS 改成本地打包(尚未做,可後續加)。

### 驗證
- `npm test` 全綠;新增 `test_import_matching.js` 6 項(姓名比對成功/失敗、班別對應、空白保留、姓名空白列略過)。
- Playwright 實測:匯入按鈕/檔案輸入/預覽面板皆存在;「確認匯入」寫入路徑正確(空白格不覆蓋、有值才寫)、匯入後面板關閉;品牌圓點 7px;**0 個 JS 執行期例外**。(沙盒擋 CDN,故 XLSX 解析本身未在此環境端對端測試,由 `test_import_matching.js` 覆蓋解析後的比對邏輯。)

---

## 2026-08 — 同步原型 v0.4.0 的休假統計拆分(修正6)

原型 (artifact 線) 更新到 v0.4.0,新增「休假統計拆分」。以精確 diff 只取這一塊 delta 套進後端版,不影響先前已加的三項功能與認證/儲存層。

### 內容
- 自訂班別代碼新增 `leaveCategory` 欄位(下拉:不算休假 / 算特休天數 / 算一般休假天數),存在 `customShiftCodes` 每筆資料裡。
- 新增共用函式 `customLeaveCategory()` / `isSpecialLeaveCode()` / `isRegularLeaveCodeOnly()`;全域 `isRestCode()`、`isWorkCode()` 一併更新,讓自訂的休假代碼自動被健檢的「每月休假天數」「14天例假」等規則納入。
- 班表最右邊「本月休假總計」拆成三欄:**休假天數 / 特休天數 / 合計**;Excel 匯出同步拆三欄、欄寬調整。
- 自訂代碼表格與貼上/複製、序列化(ccColumns/ccToRow/rowToCc)都加入第 4 欄。

### 使用注意
需使用者到後台把每個自訂代碼手動標記類別(系統不會自動猜「特」=特休)。沒標記的代碼維持「不算休假」,不會出現在任何統計欄——這是預期行為。

### 驗證
- `npm test` 全綠;新增 `test_leave_category_split.js` 6 項(一般休假加總、特休加總、合計、不算休假的代碼不誤算、工作代碼不誤算、未定義代碼不報錯)。
- Playwright 實測:表頭正確顯示「休假天數/特休天數/合計」;一位同仁排 3特休+2休+1訓+上班 → 統計 [2, 3, 5] 完全正確;**0 個 JS 執行期例外**。

---

## 2026-08 — 補完三項待辦功能(週末 w2/w3/w4、Shift 選取、顏色疊加)

延續前一輪合併時列在「尚未處理」的三項,全部做完:

### 1. 排班健檢:週末需求 w2/w3/w4
`runHealthCheck` 原本只判斷 w1(六日至少休一)、w5(六日都休),現補齊:
- **w2**「每月至少一次六日連休,其餘週末至少上一天」:計算完整六日連休(六、日都休)的週末數,0 次或 ≥2 次都會被標示。
- **w3**「休假希望兩日連休」:掃全月,若有「孤立單日休假」(前後兩天都不是休假)就標示,並列出是幾號。
- **w4**「休假希望不要連休」:掃全月,若出現連續兩天(含)以上休假就標示,並列出連休區間。
- 三者沿用修正4的「星期六配對隔天星期日」分組,不重新發明分組方式。

### 2. 多格選取:Shift+方向鍵擴充(Excel 式)
- 新增 `selAnchor`/`selCursor` 狀態,滑鼠拖曳與鍵盤共用同一組錨點。
- `Shift+↑↓←→` 以固定錨點擴充選取範圍,超出邊界自動夾住,移動到的格子會 `scrollIntoView`;正在編輯儲存格/後台欄位時不攔截方向鍵。
- 沒有任何選取時,第一次按 Shift+方向鍵從左上角(第一位同仁、1 號)開始。

### 3. 內建代碼顏色改為「疊加」而非「取代」
新增 `builtinTintStyle()`,選自訂顏色時保留原本的特殊視覺語意:
- **N 大夜**:保留深色底,文字換成選的顏色
- **Dp/Ep 兼職**:保留斜紋,只換斜紋色相
- **D8/2D8/3D8/E8 12小時支援**:保留虛線外框,只換底色
- 其餘代碼:單純實色色塊
- `cellStyleFor()`(班表)與 `renderCodeRefStrip` 的 `styleFor()`(代碼參考列)共用同一 helper,兩處呈現一致;後台提示文字同步更新。

### 驗證
- `npm test` 全綠;`test_weekend_pref_grouping.js` 擴充到 10 項(新增 w2/w3/w4 各滿足/未滿足案例)。
- Playwright 實載入:顏色疊加 N=深底藍字、Dp=綠斜紋、D8=橘底虛線框、Di=純色塊皆正確;Shift+方向鍵從左上角按「右右下」正確選出 2×3=6 格;**0 個 JS 執行期例外**。

---

## 2026-08 — 從 artifact 原型 (v0.3.0) 合併 4 塊功能進正式後端版

### 背景
存在兩條分岔的版本:
- **原型 (v0.3.0)**:單檔 HTML、用 Claude.ai 的 `window.storage`,不能部署,但有較新的功能與演算法修正。
- **後端正式版 (本專案 v1.0.0)**:Express + SQLite + JWT + bcrypt,可部署,但前端是從「更早的原型」migrate 的,缺這些新功能、演算法還是舊的有 bug 版本。

### 合併策略
**以本後端版為基底**,只把原型的 4 塊 delta 移植進 `public/index.html`,
**完全保留**後端的儲存/認證層(`window.storage`→REST API 的 shim、JWT 自動登入、`/api/auth`、`/api/users`、bcrypt)。原型那套把帳號退回明文 `window.storage` 的部分**不採用**。

### 移植的 4 塊功能
1. **多格選取**(拖曳選取 / 批次刪除 / 批次貼上)
   - 新增 `selRange`/`isDragSelecting`/`dragAnchor` 狀態
   - `setSelRange`/`clearSelRange`/`applySelHighlight`/`deleteSelectedRange`/`fillSelectedRangeWithMatrix`
   - `renderGrid` 的 `.shift-cell` 加上 `mousedown`/`mouseenter` 拖曳;`.multi-selected` CSS
   - 鍵盤:`Delete`/`Backspace` 清空選取範圍、`Ctrl/Cmd+C`/`Ctrl/Cmd+V` 批次複製貼上、`Esc` 取消
2. **班別代碼參考列** `renderCodeRefStrip()`
   - 班表下方一排可點擊的代碼;有選取範圍就整塊套用,沒有就複製提示貼上
3. **內建代碼自訂顏色**
   - `builtinCodeColors` 狀態 + 儲存 key `builtin-code-colors`(透過既有後端 kv 表,無需改後端)
   - `saveBuiltinColors()`、後台「班別代碼維護」新增顏色下拉、`cellStyleFor()` 與參考列 `styleFor()` 優先套用覆寫色
   - 取捨:覆寫色會取代 N/Dp/Ep/D8 等的深底/斜紋/虛線特殊樣式(選「系統預設樣式」則不受影響)
4. **自動排班修正 (修正1) + 週末健檢修正 (修正4)**
   - `autoScheduleNursing` 改為 `floorFillPool` 補位池 + Pass A/B/C:有白班資格但沒設輪調的同仁也會被正確排入 2Di/3Di,不再只拿到休假
   - `runHealthCheck` 週末分組從 `wkKey` 公式改為「星期六配對隔天星期日」,不再因月份起始日誤判

### 驗證
- `npm test` 全綠:rotation、rest_interval、**auto_schedule_floor_fill (新增)**、**weekend_pref_grouping (新增)**、api 整合測試 15 項
- Playwright 實際載入:建立管理者 → 進主畫面 → 代碼參考列 15 chip、後台顏色下拉 15×7 選項、關鍵函式全載入、**0 個 JS 執行期例外**

### 尚未處理(沿用原型 CHANGELOG 的已知限制)
- 多格選取還沒做 Shift+方向鍵擴充(目前只有滑鼠拖曳)
- 自動排班 Pass B「同一人同一天不會被指派兩個班」尚無明確測試
- 週末規則 w2/w3/w4 尚未實作(要做請沿用修正4的星期六配對邏輯)
- 內建代碼顏色覆寫是「取代」而非「疊加」原本特殊樣式
