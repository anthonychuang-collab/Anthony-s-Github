'use strict';
/**
 * 認證路由：
 *   GET  /api/auth/status  —— 是否還沒有任何帳號（要不要顯示「設定第一個管理者」）
 *   POST /api/auth/setup   —— 建立第一個超級管理者（只有在完全沒有帳號時可用）
 *   POST /api/auth/login   —— 帳號密碼登入，成功回傳 JWT
 *   GET  /api/auth/me      —— 用 token 換回目前使用者資訊（用於重新整理後自動登入）
 */
const express = require('express');
const router = express.Router();
const { Users } = require('../models');
const { verifyPassword, signToken } = require('../auth');
const { requireAuth } = require('../middleware');

const ROLE_ALL = 'all';

router.get('/status', (req, res) => {
  res.json({ needsSetup: Users.count() === 0 });
});

router.post('/setup', (req, res) => {
  if (Users.count() > 0) {
    return res.status(409).json({ error: '系統已經有帳號了，請直接登入' });
  }
  const { username, password } = req.body || {};
  if (!username || !password) {
    return res.status(400).json({ error: '請輸入帳號與密碼' });
  }
  // 第一個帳號自動成為擁有全部權限的超級管理者
  const { user, recoveryCode } = Users.create({
    username: String(username).trim(),
    password: String(password),
    editRoles: [ROLE_ALL],
    viewRoles: [ROLE_ALL],
    isSuperAdmin: true,
  });
  const token = signToken(user);
  // recoveryCode 只在這一次回傳（之後查不到），前端要提示使用者記下
  res.json({ token, user, recoveryCode });
});

// 忘記密碼：用帳號 + 救援碼重設密碼（不需登入）
router.post('/recover', (req, res) => {
  const { username, recoveryCode, newPassword } = req.body || {};
  if (!username || !recoveryCode || !newPassword) {
    return res.status(400).json({ error: '請把帳號、救援碼、新密碼都填寫完整' });
  }
  const result = Users.resetPasswordByRecovery(username, recoveryCode, newPassword);
  if (!result.ok) {
    if (result.reason === 'no_user') return res.status(404).json({ error: '找不到這個帳號' });
    return res.status(401).json({ error: '救援碼不正確,請確認是否輸錯,或請有後台權限的人幫你重設密碼' });
  }
  res.json({ ok: true });
});

router.post('/login', (req, res) => {
  const { username, password } = req.body || {};
  if (!username || !password) {
    return res.status(400).json({ error: '請輸入帳號與密碼' });
  }
  const row = Users.findByUsername(String(username).trim());
  if (!row || !verifyPassword(password, row.password_hash)) {
    return res.status(401).json({ error: '帳號或密碼錯誤' });
  }
  const user = {
    id: row.id,
    username: row.username,
    editRoles: JSON.parse(row.edit_roles || '[]'),
    viewRoles: JSON.parse(row.view_roles || '[]'),
    isSuperAdmin: !!row.is_super_admin,
  };
  const token = signToken(user);
  res.json({ token, user });
});

router.get('/me', requireAuth, (req, res) => {
  res.json({ user: req.user });
});

module.exports = router;
