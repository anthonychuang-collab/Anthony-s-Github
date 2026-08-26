# CHANGELOG — 後端正式版

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
