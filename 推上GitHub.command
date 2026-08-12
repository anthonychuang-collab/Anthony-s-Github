#!/bin/bash
# =====================================================================
#  線東大眾護理之家 排班系統 —— 一鍵推上 GitHub(Mac 版)
#  用法:把這個檔案跟專案放在同一個資料夾,雙擊執行即可。
#  第一次雙擊若出現「無法驗證開發者」,請改成:對檔案按右鍵 → 打開。
# =====================================================================

# 切換到這個腳本所在的資料夾(也就是專案資料夾)
cd "$(dirname "$0")" || exit 1

OWNER="anthonychuang-collab"
REPO="Anthony-s-Github"
BRANCH="claude/program-startup-n3pxm3"

echo "============================================================"
echo "  排班系統(正式版) — 推上 GitHub"
echo "  資料夾:$(pwd)"
echo "============================================================"
echo

# 1. 檢查有沒有 git
if ! command -v git >/dev/null 2>&1; then
  echo "❌ 這台 Mac 還沒有 git。"
  echo "   請先在「終端機」執行下面這行安裝,裝好再雙擊我一次:"
  echo "     xcode-select --install"
  echo
  read -r -p "按 Enter 關閉視窗"
  exit 1
fi

# 2. 檢查專案檔案在不在(避免放錯資料夾)
if [ ! -f "package.json" ] || [ ! -d "server" ]; then
  echo "⚠  這個資料夾裡沒看到 package.json / server 資料夾。"
  echo "   請確認我(這個 .command 檔)有跟解壓後的專案放在同一個資料夾裡。"
  echo
  read -r -p "按 Enter 關閉視窗"
  exit 1
fi

# 3. 初始化 git(若尚未初始化)
if [ ! -d ".git" ]; then
  echo "→ 初始化 git…"
  git init -q
fi
git config user.name  "Anthony Chuang" 2>/dev/null
git config user.email "anthony.chuang@dazhongcare.com.tw" 2>/dev/null

# 4. 加入檔案並提交(若有變更)
git add -A
if git rev-parse HEAD >/dev/null 2>&1 && git diff --cached --quiet; then
  echo "→ 沒有新變更,沿用現有提交。"
else
  echo "→ 建立提交…"
  git commit -q -m "建立多人共用正式版:Express + SQLite 後端、bcrypt/JWT 登入"
fi

# 5. 設定分支與遠端(origin 保持乾淨、不含 token)
git branch -M "$BRANCH"
git remote remove origin 2>/dev/null
git remote add origin "https://github.com/$OWNER/$REPO.git"

# 6. 詢問 Personal Access Token
echo
echo "請貼上你的 GitHub Personal Access Token,然後按 Enter。"
echo "(基於安全,輸入時畫面不會顯示任何字,這是正常的)"
printf "Token: "
read -r -s TOKEN
echo
if [ -z "$TOKEN" ]; then
  echo "❌ 沒有輸入 token,已取消。"
  read -r -p "按 Enter 關閉視窗"
  exit 1
fi

# 7. 推送(token 只用在這一次的網址,不會被存進設定檔)
echo
echo "→ 推送中,請稍候…"
if git push "https://${OWNER}:${TOKEN}@github.com/${OWNER}/${REPO}.git" "${BRANCH}:${BRANCH}"; then
  git branch --set-upstream-to="origin/${BRANCH}" "${BRANCH}" 2>/dev/null
  echo
  echo "✅ 成功!已推上分支:"
  echo "   https://github.com/${OWNER}/${REPO}/tree/${BRANCH}"
else
  echo
  echo "❌ 推送失敗。最常見的兩個原因:"
  echo "   1) Token 沒有勾到這個 repo 的『Contents = Read and write』權限"
  echo "   2) 帳號或 repo 名稱不對(目前設定:${OWNER}/${REPO})"
  echo "   確認後再雙擊我一次即可。"
fi

echo
read -r -p "按 Enter 關閉視窗"
