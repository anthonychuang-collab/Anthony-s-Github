#!/bin/bash
# 在 Mac 上把 F 班系統打包成免安裝執行檔。Finder 直接雙擊即可。
# 產出：dist/F班系統（單一執行檔，複製到任何 Mac 都能跑）
set -e
cd "$(dirname "$0")/.."
echo "==== F 班系統：打包免安裝執行檔 ===="
if ! command -v python3 >/dev/null 2>&1; then
  echo "找不到 python3。請先安裝 https://www.python.org/downloads/"; read -p "按 Enter 關閉"; exit 1
fi
echo "→ 建立虛擬環境並安裝套件（第一次會花幾分鐘）"
python3 -m venv .buildenv
source .buildenv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt pyinstaller
echo "→ 開始打包"
pyinstaller --noconfirm --clean --onefile --name "F班系統" \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --add-data "docskills:docskills" \
  --collect-all pdfplumber \
  --collect-all pdfminer \
  --collect-all docx \
  --hidden-import build_config_template \
  app.py
deactivate
echo ""
echo "==== 完成 ===="
echo "執行檔在：$(pwd)/dist/F班系統"
echo "請把『後台設定.xlsx』放在執行檔同資料夾(dist/)，之後雙擊 dist/F班系統 即可啟動。"
read -p "按 Enter 關閉"
