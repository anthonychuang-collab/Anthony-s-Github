# 部署指南

這份文件說明幾種常見的上線方式，從最簡單到比較正式。挑一種適合你的即可。

---

## 情境一：辦公室一台電腦當伺服器（最簡單，同一區網共用）

適合：機構內部、大家在同一個網路裡使用。

1. 在那台電腦裝好 Node.js 18+，把整個專案放上去。
2. `npm install`，複製 `.env.example` 成 `.env` 並設定 `JWT_SECRET`。
3. `npm start`。
4. 其他電腦用 `http://<這台電腦的區網IP>:3000` 連線（IP 查法見 README）。

### 讓它「開機自動啟動、當掉自動重開」

**方法 A：用 Docker（推薦）**
`docker-compose.yml` 已設定 `restart: unless-stopped`，開機會自動拉起來：
```bash
docker compose up -d
```

**方法 B：用 pm2（不想碰 Docker 時）**
```bash
npm install -g pm2
pm2 start server/index.js --name scheduling
pm2 save
pm2 startup      # 依畫面指示複製貼上一行指令，設定開機自動啟動
```

---

## 情境二：加上 HTTPS / 讓機構外部也能連

只要不是「同一區網、純內部」使用，就**強烈建議加 HTTPS**，否則帳密會以明碼在網路上傳輸。

作法是在前面擺一個反向代理（Nginx / Caddy），由它負責 HTTPS，再把流量轉給本系統的 3000 埠。

### 用 Caddy（設定最短，會自動申請憑證）

`Caddyfile`：
```
schedule.你的網域.com {
    reverse_proxy localhost:3000
}
```
```bash
caddy run
```
Caddy 會自動申請並更新 Let's Encrypt 憑證（前提是網域已指到這台主機、443 埠對外開放）。

### 用 Nginx（大略設定）

```nginx
server {
    listen 443 ssl;
    server_name schedule.你的網域.com;

    ssl_certificate     /etc/letsencrypt/live/schedule.你的網域.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/schedule.你的網域.com/privkey.pem;

    client_max_body_size 8m;   # 排班資料較大時放寬

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

憑證可用 certbot 申請。設定好後，本系統仍照常在 3000 埠跑（可只綁 `127.0.0.1`，不直接對外）。

---

## 情境三：雲端主機（VPS）

1. 開一台 Linux 主機（例如 Ubuntu）。
2. 裝 Docker，把專案上傳。
3. 改好 `docker-compose.yml` 的 `JWT_SECRET`。
4. `docker compose up -d`。
5. 依情境二加上 Caddy/Nginx 做 HTTPS。

---

## 環境變數一覽

| 變數 | 預設 | 說明 |
|------|------|------|
| `PORT` | `3000` | 伺服器監聽的埠 |
| `JWT_SECRET` | （無） | **必填**（正式模式沒設會拒絕啟動）。登入 token 的簽章金鑰，要長且隨機 |
| `JWT_EXPIRES_IN` | `30d` | 登入多久後需重新登入（如 `12h`、`7d`、`30d`） |
| `DB_PATH` | `data/scheduling.db` | SQLite 資料庫檔位置 |
| `NODE_ENV` | `development` | 設成 `production` 會強制要求 `JWT_SECRET` |

---

## 備份與還原

- 資料就是一個檔案：`DB_PATH` 指到的 `scheduling.db`。
- **備份**：直接複製該檔（連同 `-wal`、`-shm` 若存在）。可寫個排程每天複製到別的硬碟/雲端。
- **還原**：把備份的 `.db` 檔放回原位，重啟伺服器即可。
- Docker 版資料在 `scheduling-data` volume，可用：
  ```bash
  docker run --rm -v scheduling-data:/data -v "$PWD":/backup alpine \
    sh -c "cp /data/scheduling.db /backup/scheduling-backup.db"
  ```

---

## 常見問題

- **其他電腦連不上** → 檢查伺服器那台的防火牆有沒有開放對應埠；確認用的是區網 IP 不是 `localhost`。
- **大家看到的班表不一樣** → 幾乎都是連到不同伺服器（例如各自開了自己的），確認所有人網址一致。
- **忘記管理者密碼** → 目前沒有自助重設。可由另一個超級管理者到後台改；若只有一個管理者且忘記，需在伺服器端直接改資料庫（進階操作）。
- **升級程式後要重跑** → `git pull` 後 `npm install` 再 `npm start`；Docker 則 `docker compose up -d --build`。資料庫不受影響。
