# Mac 主機部署指南（免安裝執行檔＋開機自動啟動）

在 Finder 雙擊 `mac/` 內檔案，不必打指令。

## 步驟1：打包免安裝執行檔（做一次）
雙擊 `mac/1_打包執行檔.command` → 產生 `dist/F班系統`。
依提示把 `後台設定.xlsx` 複製到 `dist/`。換機只要複製 dist/ 整包、不必裝 Python。
> 若被擋（未識別開發者）：右鍵→打開；或系統設定→隱私權與安全性→允許。

## 步驟2：開機自動啟動（做一次）
雙擊 `mac/2_安裝開機自動啟動.command` → 輸入存取密碼 → 立即啟動且開機自動執行、當掉自動重開。
畫面顯示連線網址 `http://主機IP:5000`。

停用：雙擊 `mac/3_移除自動啟動.command`。
記錄：`runtime/service.log`。
第一次打包需連網下載工具；之後執行離線可用、資料不外流。

## 選用：文件 PDF 定版
產出約束評估記錄單／住民日常生活照護表時，系統會同時附一份 PDF（避免換電腦開啟時版面跑掉）。
PDF 由 LibreOffice 轉檔，需在主機安裝一次（免費、離線）：
- 下載安裝 <https://zh-tw.libreoffice.org/download/> ，或用 Homebrew：`brew install --cask libreoffice`。
- 標楷體等字型由主機提供，PDF 版面與 Word 一致。
- 沒安裝也能用：系統會只給 Word 檔（不會出錯）。
