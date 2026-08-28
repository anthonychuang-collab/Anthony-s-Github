#!/bin/bash
# =============================================================
#  線東大眾護理之家 機構排班系統 —— Mac 一鍵啟動
#
#  使用方法：在 Finder 直接「連點兩下」這個檔案即可。
#  （第一次可能要按右鍵 → 打開，因為 macOS 會確認來源）
# =============================================================

# 切換到這個檔案所在的資料夾，這樣從哪裡點都能正常運作
cd "$(dirname "$0")" || exit 1

clear
echo "===================================================="
echo "   線東大眾護理之家 機構排班系統"
echo "===================================================="
echo ""

# ---- 1) 檢查有沒有裝 Node.js ----
if ! command -v node >/dev/null 2>&1; then
  echo "⚠️  這台電腦還沒有安裝 Node.js（只需安裝一次）"
  echo ""
  echo "   請照下面步驟做："
  echo "     1. 打開瀏覽器前往： https://nodejs.org/"
  echo "     2. 下載畫面左邊那顆綠色「LTS」按鈕並安裝"
  echo "     3. 安裝完，把這個視窗關掉，再連點兩下本檔案一次"
  echo ""
  echo "   （按 Enter 鍵關閉視窗）"
  read -r _
  exit 1
fi

echo "✅ Node.js 版本： $(node -v)"
echo ""

# ---- 2) 第一次啟動：安裝必要元件 ----
if [ ! -d node_modules ] || [ ! -d node_modules/better-sqlite3 ]; then
  echo "🔧 第一次啟動，正在安裝必要元件…"
  echo "   （大約 1～3 分鐘，只有第一次需要，請耐心等候）"
  echo ""
  if ! npm install; then
    echo ""
    echo "⚠️  元件安裝失敗，通常是網路問題。請確認電腦有連上網路後再試一次。"
    echo "   （按 Enter 鍵關閉視窗）"
    read -r _
    exit 1
  fi
  echo ""
  echo "✅ 元件安裝完成"
  echo ""
fi

# ---- 3) 產生設定檔 .env（含隨機安全金鑰）——只有第一次 ----
if [ ! -f .env ]; then
  echo "🔑 正在建立設定檔並產生專屬安全金鑰…"
  SECRET=$(node -e "console.log(require('crypto').randomBytes(48).toString('hex'))")
  cat > .env <<EOF
# 這個檔案由啟動器自動產生，請勿分享給別人
PORT=3000
JWT_SECRET=$SECRET
JWT_EXPIRES_IN=30d
DB_PATH=data/scheduling.db
EOF
  echo "✅ 設定檔已建立"
  echo ""
fi

# ---- 4) 讀出設定的埠號（預設 3000）----
APP_PORT="$(grep -E '^PORT=' .env 2>/dev/null | head -1 | cut -d= -f2 | tr -d ' \r')"
[ -z "$APP_PORT" ] && APP_PORT=3000

# ---- 4.5) 先看看系統是不是「已經在執行了」，避免重複啟動撞埠號 ----
if curl -s "http://localhost:${APP_PORT}/api/health" >/dev/null 2>&1; then
  echo "ℹ️  排班系統已經在執行中了,直接幫你打開瀏覽器。"
  echo "   (如果你是想「重新啟動」,請先關掉另一個正在執行的黑色視窗,再點一次本檔案。)"
  echo ""
  open "http://localhost:${APP_PORT}"
  echo "   這個視窗可以直接關掉。"
  echo ""
  echo "   (按 Enter 鍵關閉)"
  read -r _
  exit 0
fi

# ---- 5) 伺服器起來後，自動打開瀏覽器 ----
( sleep 2 && open "http://localhost:${APP_PORT}" ) >/dev/null 2>&1 &

echo "----------------------------------------------------"
echo "  系統啟動中，稍等一下瀏覽器會自動打開："
echo "     http://localhost:${APP_PORT}"
echo ""
echo "  要結束系統：關掉這個黑色視窗，或按 Control + C"
echo "  提醒：同一時間只要開「一個」系統視窗就好。"
echo "----------------------------------------------------"
echo ""

# ---- 6) 啟動伺服器（前景執行）----
node server/index.js
