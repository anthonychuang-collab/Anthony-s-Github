# 線東大眾護理之家 — 排班相關系統

這個 repo 收了兩套系統，都給線東大眾護理之家使用，各自獨立執行：

| 系統 | 位置 | 技術 | 做什麼 |
|---|---|---|---|
| **① 機構排班系統** | 本目錄 | Node.js + Express + SQLite | **排出班表**：日曆介面填班別、多人即時同步、權限分級、勞基法健檢、護理自動排班草稿 |
| **② F 班自動排定系統** | [`f_schedule/`](f_schedule/) | Python + Flask | **班表轉文件**：T 班 → 上色補人頭的 F 班 → 約束評估記錄單、住民日常生活照護表 |

兩者是同一條流程的前後段（①排出 T 班 → ②轉成 F 班與稽核文件），但可以分開啟動、分開使用。
②的說明見 [`f_schedule/README.md`](f_schedule/README.md)。

以下是**①機構排班系統**的說明。

---

## 機構排班系統（多人共用正式版）

這是機構排班系統的**正式版**：有真正的後端伺服器、資料庫、以及安全的帳號登入。
不同電腦連到同一台伺服器，就會看到**同一份、即時同步**的班表。

> 前身是一個在 Claude.ai artifact 環境跑的單一 HTML 原型（靠 `window.storage` 存資料，密碼明文、無法多人共用）。
> 這一版把儲存與登入整層換成真正的後端，原本好用的操作介面與排班邏輯則完整保留。

---

## 這一版做了什麼（跟原型的差別）

| 項目 | 原型（artifact 單檔） | 這一版（正式版） |
|------|----------------------|------------------|
| 資料儲存 | `window.storage`（Claude.ai 專屬，一般瀏覽器不存在） | 自己的後端 API + **SQLite 資料庫** |
| 多人共用 | 做不到（換裝置就看不到） | ✅ 所有人連同一台伺服器，看同一份資料 |
| 登入 | 前端比對，**密碼明文** | 後端驗證，密碼用 **bcrypt 雜湊**，連線用 **JWT** |
| 權限保護 | 只是介面隱藏 | API 層強制檢查（沒登入讀不到資料、非管理者不能改帳號） |
| 重新整理 | 每次都要重登 | ✅ 保持登入（記住 token） |
| 前端畫面與排班邏輯 | —— | 完全沿用，沒有改動功能 |

---

## 快速啟動

需要 **Node.js 18 以上**（用 Docker 的話不需要另外裝 Node）。

### 方法一：直接用 Node 跑（最簡單，適合放在辦公室一台電腦上）

```bash
# 1. 安裝套件
npm install

# 2. 設定金鑰（第一次才要做）
cp .env.example .env
#    打開 .env，把 JWT_SECRET 改成一串很長的隨機字。產生方法：
node -e "console.log(require('crypto').randomBytes(48).toString('hex'))"

# 3. 啟動
npm start
```

啟動後畫面會顯示網址，用瀏覽器打開 <http://localhost:3000> 即可。

### 方法二：用 Docker（推薦，環境最乾淨）

先把 `docker-compose.yml` 裡的 `JWT_SECRET` 改成一串長隨機字，然後：

```bash
docker compose up -d          # 啟動（背景執行）
docker compose logs -f        # 看紀錄
docker compose down           # 停止
```

---

## 第一次使用

1. 第一次打開，畫面會是 **「設定第一個管理者帳號」**。
2. 輸入你要的帳號、密碼，按下去就會建立一個**擁有全部權限的超級管理者**並自動登入。
3. 之後在 **後台管理 → 使用者帳號管理** 裡，可以再幫其他同仁開帳號、設定各自能看/能改哪些職務（護理／行政／照服），以及要不要給後台管理權限。

---

## 讓其他電腦一起用（同一間辦公室 / 區網）

1. 在**跑伺服器那台電腦**查它的區網 IP：
   - Windows：命令提示字元輸入 `ipconfig`，找「IPv4 位址」（像 `192.168.1.50`）
   - Mac：`ipconfig getifaddr en0`
2. 其他電腦的瀏覽器打開 `http://<那台電腦的IP>:3000`，例如 `http://192.168.1.50:3000`。
3. 用各自的帳號登入即可，大家看到的是同一份班表。

> 若連不上，通常是那台電腦的防火牆擋了 3000 埠，開放它即可。
> 想從公司外面 / 網際網路連線、或加上 HTTPS，請看 [`docs/deployment.md`](docs/deployment.md)。

---

## 資料存在哪裡、怎麼備份

- 所有資料都在一個 SQLite 檔案裡，預設是 `data/scheduling.db`（Docker 則存在名為 `scheduling-data` 的 volume）。
- **備份＝複製這個檔案**。建議定期複製到另一顆硬碟或雲端。
- 這個檔案不會被上傳到 GitHub（已寫進 `.gitignore`）。

---

## 專案結構

```
.
├── server/                 後端(Node/Express)
│   ├── index.js            伺服器進入點:掛 API、送前端網頁
│   ├── config.js           讀取 .env 設定
│   ├── db.js               SQLite 連線與資料表
│   ├── models.js           使用者 / 共用資料的存取
│   ├── auth.js             bcrypt 密碼雜湊、JWT 簽發驗證
│   ├── middleware.js       登入檢查、超級管理者檢查
│   └── routes/
│       ├── auth.js         /api/auth  設定第一位管理者、登入、目前使用者
│       ├── users.js        /api/users 帳號管理(限超級管理者)
│       └── storage.js      /api/storage 共用排班資料的讀寫
├── public/
│   └── index.html          前端(沿用原型,只換掉儲存與登入層;Logo 已內嵌)
├── docs/
│   ├── PRD.md              產品規格書(功能、使用者故事、驗收標準、已知限制)
│   ├── deployment.md       部署指南(區網 / 對外 / HTTPS / 開機自動啟動)
│   └── development-summary.md
├── tests/                  測試
│   ├── test_rotation.js       輪調邏輯
│   ├── test_rest_interval.js  換班休息間隔
│   └── test_api.js            後端 API 端對端測試
├── Dockerfile / docker-compose.yml
├── .env.example            設定範本(複製成 .env)
└── package.json
```

---

## API 一覽

所有 `/api/storage` 與 `/api/users` 都需要在標頭帶 `Authorization: Bearer <token>`。

| 方法 | 路徑 | 說明 | 權限 |
|------|------|------|------|
| GET  | `/api/auth/status` | 是否還沒有任何帳號 | 公開 |
| POST | `/api/auth/setup`  | 建立第一位超級管理者 | 僅在無帳號時 |
| POST | `/api/auth/login`  | 帳號密碼登入，回傳 token | 公開 |
| GET  | `/api/auth/me`     | 用 token 換回目前使用者 | 需登入 |
| GET  | `/api/users`       | 列出帳號 | 超級管理者 |
| POST | `/api/users`       | 新增帳號 | 超級管理者 |
| PUT  | `/api/users/:id`   | 修改帳號 | 超級管理者 |
| DELETE | `/api/users/:id` | 刪除帳號 | 超級管理者 |
| GET/PUT/DELETE | `/api/storage/:key` | 共用資料讀寫刪 | 需登入 |

---

## 測試

```bash
npm test
```

會依序跑：輪調邏輯、換班休息間隔、以及後端 API 的端對端測試（設定管理者、登入、共用資料、權限保護等）。

---

## 安全性叮嚀

- **一定要設 `JWT_SECRET`**，而且要長、要隨機、不要外流。正式模式（`NODE_ENV=production`）沒設的話伺服器會直接拒絕啟動。
- 若要讓機構外部（網際網路）也能連，**務必加上 HTTPS**（見 `docs/deployment.md`），否則帳號密碼會以明碼在網路上傳輸。
- 密碼已用 bcrypt 雜湊儲存，資料庫外洩也不會直接看到明文；但仍請妥善保管資料庫檔案與伺服器。
