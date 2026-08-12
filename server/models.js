'use strict';
/**
 * 資料存取層：把資料庫的一列轉成前端看得懂的物件，並提供 CRUD 方法。
 */
const db = require('./db');
const { hashPassword } = require('./auth');

function nowIso() {
  return new Date().toISOString();
}

function genId() {
  // 不依賴外部套件的簡單唯一 ID
  return 'u' + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36);
}

// 把資料庫的一列使用者轉成前端物件（永遠不含密碼雜湊）
function toPublicUser(row) {
  if (!row) return null;
  return {
    id: row.id,
    username: row.username,
    editRoles: JSON.parse(row.edit_roles || '[]'),
    viewRoles: JSON.parse(row.view_roles || '[]'),
    isSuperAdmin: !!row.is_super_admin,
  };
}

const Users = {
  count() {
    return db.prepare('SELECT COUNT(*) AS n FROM users').get().n;
  },

  list() {
    const rows = db.prepare('SELECT * FROM users ORDER BY created_at ASC').all();
    return rows.map(toPublicUser);
  },

  findById(id) {
    return db.prepare('SELECT * FROM users WHERE id = ?').get(id);
  },

  findByUsername(username) {
    return db.prepare('SELECT * FROM users WHERE username = ? COLLATE NOCASE').get(username);
  },

  create({ username, password, editRoles = [], viewRoles = [], isSuperAdmin = false }) {
    const id = genId();
    const ts = nowIso();
    db.prepare(`
      INSERT INTO users (id, username, password_hash, edit_roles, view_roles, is_super_admin, created_at, updated_at)
      VALUES (@id, @username, @password_hash, @edit_roles, @view_roles, @is_super_admin, @created_at, @updated_at)
    `).run({
      id,
      username,
      password_hash: hashPassword(password),
      edit_roles: JSON.stringify(editRoles),
      view_roles: JSON.stringify(viewRoles),
      is_super_admin: isSuperAdmin ? 1 : 0,
      created_at: ts,
      updated_at: ts,
    });
    return toPublicUser(this.findById(id));
  },

  update(id, { username, password, editRoles, viewRoles, isSuperAdmin }) {
    const existing = this.findById(id);
    if (!existing) return null;
    const next = {
      id,
      username: username != null ? username : existing.username,
      password_hash: password ? hashPassword(password) : existing.password_hash,
      edit_roles: editRoles != null ? JSON.stringify(editRoles) : existing.edit_roles,
      view_roles: viewRoles != null ? JSON.stringify(viewRoles) : existing.view_roles,
      is_super_admin: (isSuperAdmin != null ? isSuperAdmin : !!existing.is_super_admin) ? 1 : 0,
      updated_at: nowIso(),
    };
    db.prepare(`
      UPDATE users SET username=@username, password_hash=@password_hash,
        edit_roles=@edit_roles, view_roles=@view_roles, is_super_admin=@is_super_admin, updated_at=@updated_at
      WHERE id=@id
    `).run(next);
    return toPublicUser(this.findById(id));
  },

  remove(id) {
    return db.prepare('DELETE FROM users WHERE id = ?').run(id).changes > 0;
  },
};

const KV = {
  get(key) {
    const row = db.prepare('SELECT value FROM kv WHERE key = ?').get(key);
    return row ? row.value : null;
  },

  set(key, value) {
    db.prepare(`
      INSERT INTO kv (key, value, updated_at) VALUES (?, ?, ?)
      ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
    `).run(key, value, nowIso());
    return true;
  },

  delete(key) {
    return db.prepare('DELETE FROM kv WHERE key = ?').run(key).changes > 0;
  },
};

module.exports = { Users, KV, toPublicUser };
