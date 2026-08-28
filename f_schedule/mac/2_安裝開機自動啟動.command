#!/bin/bash
# 安裝「開機自動啟動」：Mac 一開機就自動跑 F 班系統，當掉自動重開(launchd)。雙擊執行。
set -e
cd "$(dirname "$0")/.."
PROJ="$(pwd)"; LABEL="com.dazhong.fban"; PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
echo "==== 安裝 F 班系統 開機自動啟動 ===="
if [ -x "$PROJ/dist/F班系統" ]; then
  PROG="$PROJ/dist/F班系統"; ARG=""; WORKDIR="$PROJ/dist"; echo "→ 使用免安裝執行檔"
elif [ -x "$PROJ/.buildenv/bin/python" ]; then
  PROG="$PROJ/.buildenv/bin/python"; ARG="$PROJ/app.py"; WORKDIR="$PROJ"; echo "→ 使用虛擬環境 python"
else
  PROG="$(command -v python3)"; ARG="$PROJ/app.py"; WORKDIR="$PROJ"; echo "→ 使用系統 python3"
fi
read -p "請設定存取密碼(其他電腦連線要輸入): " PW; [ -z "$PW" ] && PW="dazhong123"
mkdir -p "$HOME/Library/LaunchAgents" "$PROJ/runtime"
{
cat <<HEAD
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key><array>
    <string>${PROG}</string>
HEAD
[ -n "$ARG" ] && echo "    <string>${ARG}</string>"
cat <<TAIL
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>FBAN_PASSWORD</key><string>${PW}</string>
    <key>FBAN_HOST</key><string>0.0.0.0</string>
    <key>FBAN_PORT</key><string>5000</string>
    <key>FBAN_SECRET</key><string>$(python3 -c 'import secrets;print(secrets.token_hex(16))')</string>
  </dict>
  <key>WorkingDirectory</key><string>${WORKDIR}</string>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>${PROJ}/runtime/service.log</string>
  <key>StandardErrorPath</key><string>${PROJ}/runtime/service.err.log</string>
</dict></plist>
TAIL
} > "$PLIST"
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"
sleep 2
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "本機IP")
echo ""; echo "==== 完成，已啟動且會開機自動執行 ===="
echo "  本機：http://127.0.0.1:5000   其他電腦：http://${IP}:5000   密碼：${PW}"
echo "（停用請雙擊 3_移除自動啟動.command）"
read -p "按 Enter 關閉"
