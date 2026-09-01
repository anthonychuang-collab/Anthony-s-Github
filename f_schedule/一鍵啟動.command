#!/bin/bash
# 線東大眾護理之家 — F 班自動排定系統　一鍵啟動
# 雙擊本檔即可。第一次會自動安裝所需套件（約 1 分鐘），之後啟動只要幾秒。

cd "$(dirname "$0")" || exit 1

echo "======================================================"
echo " 線東大眾護理之家　F 班自動排定系統"
echo "======================================================"
echo

bye() {                       # 出錯時停住視窗，讓使用者看得到訊息
  echo
  echo "------------------------------------------------------"
  echo "$1"
  echo "（把上面的訊息整段拍給資訊窗口或貼給 Claude，就能知道怎麼處理）"
  echo
  read -r -p "按 Enter 鍵關閉這個視窗…" _
  exit 1
}

if [ ! -f "app.py" ]; then
  bye "找不到 app.py。請確認這個啟動檔沒有被搬離 f_schedule 資料夾。"
fi

if ! command -v python3 >/dev/null 2>&1; then
  bye "這台電腦還沒有安裝 Python 3。
請到 https://www.python.org/downloads/ 下載安裝（一路按繼續即可），
安裝完成後再雙擊本檔一次。"
fi

# ---- 第一次執行：建立獨立環境並安裝套件（不會動到系統的 Python）----
if [ ! -x ".venv/bin/python" ]; then
  echo "第一次啟動，正在安裝必要套件，請稍候約 1 分鐘…"
  echo "（只有第一次要等，之後都是幾秒鐘）"
  echo
  rm -rf .venv
  python3 -m venv .venv || bye "建立獨立環境失敗。"
  .venv/bin/python -m pip install --upgrade pip >/dev/null 2>&1
  .venv/bin/python -m pip install -r requirements.txt \
    || bye "套件安裝失敗，可能是網路不通或需要重試一次。"
  echo
  echo "套件安裝完成。"
  echo
fi

# ---- 挑一個沒被佔用的埠：macOS 的 AirPlay 接收器會佔用 5000 ----
PORT=$(.venv/bin/python - <<'PY'
import socket
for p in (5050, 5051, 5052, 5060, 8080, 8000, 5000):
    s = socket.socket()
    s.settimeout(0.3)
    try:
        s.connect(("127.0.0.1", p))     # 連得上 = 已被別的程式佔用
        s.close()
    except OSError:
        print(p)
        break
else:
    print(5050)
PY
)
[ -z "$PORT" ] && PORT=5050

echo "網址：http://127.0.0.1:${PORT}"
echo "密碼：${FBAN_PASSWORD:-dazhong123}"
echo
echo "瀏覽器會自動打開。要結束系統：關掉這個視窗，或按 Control + C。"
echo "======================================================"
echo

# 稍等伺服器起來再開瀏覽器
( sleep 2; command -v open >/dev/null 2>&1 && open "http://127.0.0.1:${PORT}" ) >/dev/null 2>&1 &

FBAN_PORT="$PORT" .venv/bin/python app.py

echo
read -r -p "系統已結束。按 Enter 鍵關閉這個視窗…" _
