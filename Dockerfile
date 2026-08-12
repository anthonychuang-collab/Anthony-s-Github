# 線東大眾護理之家 機構排班系統 —— 正式版容器映像
FROM node:20-bookworm-slim

WORKDIR /app

# 先只複製套件清單,善用 Docker 快取
COPY package.json package-lock.json* ./
RUN npm install --omit=dev

# 複製其餘程式
COPY server ./server
COPY public ./public

# 資料庫檔案放在 /app/data,建議用 volume 掛出來以免容器刪掉後資料不見
ENV NODE_ENV=production
ENV PORT=3000
ENV DB_PATH=/app/data/scheduling.db
VOLUME ["/app/data"]

EXPOSE 3000

CMD ["node", "server/index.js"]
