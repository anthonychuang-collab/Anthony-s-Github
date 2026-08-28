'use strict';
/**
 * 資料存取層：把資料庫的一列轉成前端看得懂的物件，並提供 CRUD 方法。
 */
const db = require('./db');
const { hashPassword, verifyPassword } = require('./auth');

function nowIso() {
  return new Date().toISOString();
}

function genId() {
  // 不依賴外部套件的簡單唯一 ID
  return 'u' + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36);
}

// 忘記密碼救援碼：XXXX-XXXX-XXXX（英數大寫），只顯示一次，資料庫裡存 bcrypt 雜湊
function genRecoveryCode() {
  const seg = () => Math.random().toString(36).slice(2, 6).toUpperCase().padEnd(4, '0');
  return `${seg()}-${seg()}-${seg()}`;
}

function normalizeRecovery(code) {
  return String(code || '').trim().toUpperCase();
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

  // 建立帳號並自動產生一組救援碼。回傳 { user, recoveryCode }，
  // recoveryCode 是明碼、只在這一次回傳（資料庫只存雜湊）。
  create({ username, password, editRoles = [], viewRoles = [], isSuperAdmin = false }) {
    const id = genId();
    const ts = nowIso();
    const recoveryCode = genRecoveryCode();
    db.prepare(`
      INSERT INTO users (id, username, password_hash, edit_roles, view_roles, is_super_admin, recovery_code, created_at, updated_at)
      VALUES (@id, @username, @password_hash, @edit_roles, @view_roles, @is_super_admin, @recovery_code, @created_at, @updated_at)
    `).run({
      id,
      username,
      password_hash: hashPassword(password),
      edit_roles: JSON.stringify(editRoles),
      view_roles: JSON.stringify(viewRoles),
      is_super_admin: isSuperAdmin ? 1 : 0,
      recovery_code: hashPassword(normalizeRecovery(recoveryCode)),
      created_at: ts,
      updated_at: ts,
    });
    return { user: toPublicUser(this.findById(id)), recoveryCode };
  },

  // 用救援碼重設密碼（忘記密碼流程）。成功回傳 true，帳號不存在或救援碼不符回傳對應原因。
  resetPasswordByRecovery(username, code, newPassword) {
    const row = this.findByUsername(String(username || '').trim());
    if (!row) return { ok: false, reason: 'no_user' };
    if (!row.recovery_code || !verifyPassword(normalizeRecovery(code), row.recovery_code)) {
      return { ok: false, reason: 'bad_code' };
    }
    db.prepare('UPDATE users SET password_hash=?, updated_at=? WHERE id=?')
      .run(hashPassword(String(newPassword)), nowIso(), row.id);
    return { ok: true };
  },

  // 重新產生某帳號的救援碼（原救援碼也遺失時，由超級管理者代為重設）。回傳新的明碼救援碼。
  resetRecoveryCode(id) {
    const row = this.findById(id);
    if (!row) return null;
    const recoveryCode = genRecoveryCode();
    db.prepare('UPDATE users SET recovery_code=?, updated_at=? WHERE id=?')
      .run(hashPassword(normalizeRecovery(recoveryCode)), nowIso(), id);
    return recoveryCode;
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
