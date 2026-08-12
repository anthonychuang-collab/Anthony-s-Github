'use strict';
/**
 * 極簡設定讀取器：如果專案根目錄有 .env 檔就讀進來，
 * 讓我們不用額外安裝 dotenv 套件。已存在的環境變數優先，不會被覆蓋。
 */
const fs = require('fs');
const path = require('path');

function loadEnvFile() {
  const envPath = path.join(__dirname, '..', '.env');
  if (!fs.existsSync(envPath)) return;
  const text = fs.readFileSync(envPath, 'utf8');
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq === -1) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    // 去掉包住值的引號
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    if (!(key in process.env)) process.env[key] = value;
  }
}

loadEnvFile();

const config = {
  port: parseInt(process.env.PORT, 10) || 3000,
  jwtSecret: process.env.JWT_SECRET || '',
  jwtExpiresIn: process.env.JWT_EXPIRES_IN || '30d',
  dbPath: process.env.DB_PATH || path.join(__dirname, '..', 'data', 'scheduling.db'),
  nodeEnv: process.env.NODE_ENV || 'development',
};

// 上線環境一定要設定 JWT_SECRET，否則直接讓程式停下來提醒。
if (!config.jwtSecret) {
  if (config.nodeEnv === 'production') {
    console.error('\n[致命錯誤] 尚未設定 JWT_SECRET。請複製 .env.example 成 .env 並填入一串很長的隨機字串後再啟動。\n');
    process.exit(1);
  } else {
    // 開發模式給一個臨時金鑰，方便本機測試（重啟後大家要重新登入）。
    config.jwtSecret = 'dev-only-insecure-secret-change-me';
    console.warn('[警告] 未設定 JWT_SECRET，正在使用開發用的臨時金鑰。正式上線前務必到 .env 設定。');
  }
}

module.exports = config;
