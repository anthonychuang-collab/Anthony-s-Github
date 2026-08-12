'use strict';
/**
 * SQLite 資料庫層。使用 better-sqlite3（同步 API，適合這種內部工具的規模）。
 *
 * 兩張表：
 *   users —— 使用者帳號，密碼用 bcrypt 雜湊後儲存（絕不存明文）
 *   kv    —— 排班系統的共用資料，全部是 key -> JSON 字串。所有登入者共用同一份。
 */
const fs = require('fs');
const path = require('path');
const Database = require('better-sqlite3');
const config = require('./config');

// 確保資料庫檔案所在的資料夾存在
fs.mkdirSync(path.dirname(config.dbPath), { recursive: true });

const db = new Database(config.dbPath);
db.pragma('journal_mode = WAL'); // 允許多人同時讀取更順暢
db.pragma('foreign_keys = ON');

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    edit_roles    TEXT NOT NULL DEFAULT '[]',
    view_roles    TEXT NOT NULL DEFAULT '[]',
    is_super_admin INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS kv (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TEXT NOT NULL
  );
`);

module.exports = db;
