'use strict';
/**
 * 使用者帳號管理路由（只有超級管理者能用）：
 *   GET    /api/users      —— 列出所有帳號（不含密碼）
 *   POST   /api/users      —— 新增帳號
 *   PUT    /api/users/:id  —— 修改帳號（密碼留空則不變）
 *   DELETE /api/users/:id  —— 刪除帳號
 *
 * 內建保護：不允許刪到一個帳號都不剩，也不允許把最後一個超級管理者刪掉或降權，
 * 以免整個系統再也沒人能進後台。
 */
const express = require('express');
const router = express.Router();
const { Users } = require('../models');
const { requireAuth, requireSuperAdmin } = require('../middleware');

router.use(requireAuth, requireSuperAdmin);

function countSuperAdmins() {
  return Users.list().filter((u) => u.isSuperAdmin).length;
}

router.get('/', (req, res) => {
  res.json({ users: Users.list() });
});

router.post('/', (req, res) => {
  const { username, password, editRoles, viewRoles, isSuperAdmin } = req.body || {};
  const name = (username || '').trim();
  if (!name) return res.status(400).json({ error: '請輸入帳號' });
  if (!password) return res.status(400).json({ error: '請輸入密碼' });
  if (Users.findByUsername(name)) {
    return res.status(409).json({ error: '這個帳號名稱已經有人用了' });
  }
  const user = Users.create({
    username: name,
    password: String(password),
    editRoles: Array.isArray(editRoles) ? editRoles : [],
    viewRoles: Array.isArray(viewRoles) ? viewRoles : [],
    isSuperAdmin: !!isSuperAdmin,
  });
  res.status(201).json({ user });
});

router.put('/:id', (req, res) => {
  const target = Users.findById(req.params.id);
  if (!target) return res.status(404).json({ error: '找不到這個帳號' });

  const { username, password, editRoles, viewRoles, isSuperAdmin } = req.body || {};
  const name = username != null ? String(username).trim() : null;

  if (name === '') return res.status(400).json({ error: '帳號不能空白' });
  if (name) {
    const clash = Users.findByUsername(name);
    if (clash && clash.id !== target.id) {
      return res.status(409).json({ error: '這個帳號名稱已經有人用了' });
    }
  }

  // 不允許把最後一個超級管理者降權，否則沒人能進後台
  const willBeSuper = isSuperAdmin != null ? !!isSuperAdmin : !!target.is_super_admin;
  if (target.is_super_admin && !willBeSuper && countSuperAdmins() <= 1) {
    return res.status(400).json({ error: '至少要保留一個有後台管理權限的帳號' });
  }

  const user = Users.update(req.params.id, {
    username: name != null ? name : undefined,
    password: password || undefined,
    editRoles: Array.isArray(editRoles) ? editRoles : undefined,
    viewRoles: Array.isArray(viewRoles) ? viewRoles : undefined,
    isSuperAdmin: isSuperAdmin != null ? !!isSuperAdmin : undefined,
  });
  res.json({ user });
});

router.delete('/:id', (req, res) => {
  const target = Users.findById(req.params.id);
  if (!target) return res.status(404).json({ error: '找不到這個帳號' });

  if (Users.count() <= 1) {
    return res.status(400).json({ error: '至少要保留一個帳號' });
  }
  if (target.is_super_admin && countSuperAdmins() <= 1) {
    return res.status(400).json({ error: '至少要保留一個有後台管理權限的帳號' });
  }
  Users.remove(req.params.id);
  res.json({ ok: true });
});

module.exports = router;
