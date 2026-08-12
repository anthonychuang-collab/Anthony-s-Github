'use strict';
/**
 * 線東大眾護理之家 機構排班系統 —— 後端伺服器進入點。
 *
 * 這支程式做兩件事：
 *   1. 提供 /api/... 的資料與帳號 API（後端 + 資料庫 + 真正的登入）
 *   2. 把 public/ 裡的前端網頁送給瀏覽器
 *
 * 啟動方式：npm start（或 node server/index.js）
 */
const path = require('path');
const express = require('express');
const config = require('./config');

// 先載入 db，確保資料庫與資料表在伺服器起來前就建立好
require('./db');

const authRoutes = require('./routes/auth');
const userRoutes = require('./routes/users');
const storageRoutes = require('./routes/storage');

const app = express();

app.use(express.json({ limit: '5mb' })); // 排班資料可能較大，放寬上限

// --- API ---
app.use('/api/auth', authRoutes);
app.use('/api/users', userRoutes);
app.use('/api/storage', storageRoutes);

app.get('/api/health', (req, res) => res.json({ ok: true }));

// --- 前端靜態檔案 ---
const publicDir = path.join(__dirname, '..', 'public');
app.use(express.static(publicDir));

// 其他非 /api 的路徑都回傳前端首頁（單頁應用）
app.get(/^(?!\/api).*/, (req, res) => {
  res.sendFile(path.join(publicDir, 'index.html'));
});

// --- 統一錯誤處理 ---
app.use((err, req, res, next) => {
  console.error('伺服器錯誤：', err);
  if (res.headersSent) return next(err);
  res.status(500).json({ error: '伺服器內部錯誤' });
});

// 只有「直接執行這支檔案」時才真的開始監聽埠號;
// 被測試 require 進來時不會自動綁埠,方便測試各自開自己的伺服器。
if (require.main === module) {
  const server = app.listen(config.port, () => {
    console.log('====================================================');
    console.log('  線東大眾護理之家 機構排班系統 已啟動');
    console.log('  本機開啟： http://localhost:' + config.port);
    console.log('  同一區網的其他電腦：http://<這台電腦的IP>:' + config.port);
    console.log('  資料庫檔案：' + config.dbPath);
    console.log('  結束請按 Ctrl+C');
    console.log('====================================================');
  });

  // 讓 Docker / 系統可以優雅關閉
  const shutdown = () => {
    console.log('\n正在關閉伺服器…');
    server.close(() => process.exit(0));
  };
  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
}

module.exports = app;
