#!/bin/bash
LABEL="com.dazhong.fban"; PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
echo "==== 移除 F 班系統 開機自動啟動 ===="
launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
echo "已停用並移除（執行檔與設定檔仍保留）。"
read -p "按 Enter 關閉"
