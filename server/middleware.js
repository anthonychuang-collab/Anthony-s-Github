'use strict';
/**
 * Express 中介層：驗證 JWT、載入目前使用者、限制只有超級管理者能用的路由。
 */
const { verifyToken, extractToken } = require('./auth');
const { Users, toPublicUser } = require('./models');

// 需要登入才能使用。通過後 req.user 會是完整的使用者物件（含權限）。
function requireAuth(req, res, next) {
  const token = extractToken(req);
  if (!token) return res.status(401).json({ error: '尚未登入' });
  const payload = verifyToken(token);
  if (!payload) return res.status(401).json({ error: '登入已過期，請重新登入' });
  const row = Users.findById(payload.sub);
  if (!row) return res.status(401).json({ error: '帳號已不存在' });
  req.user = toPublicUser(row);
  next();
}

// 需要「後台管理權限」（超級管理者）才能使用。
function requireSuperAdmin(req, res, next) {
  if (!req.user || !req.user.isSuperAdmin) {
    return res.status(403).json({ error: '您的帳號沒有後台管理權限' });
  }
  next();
}

module.exports = { requireAuth, requireSuperAdmin };
