'use strict';
/**
 * 共用資料的儲存路由（需登入）。這一層取代了原本 Claude.ai 的 window.storage：
 *   GET    /api/storage/:key  —— 讀一筆共用資料
 *   PUT    /api/storage/:key  —— 寫一筆共用資料
 *   DELETE /api/storage/:key  —— 刪一筆共用資料
 *
 * 所有登入者共用同一份資料（等同原本 shared=true 的行為），
 * 這樣不同電腦、不同人看到的排班表才會是同一份、即時同步。
 */
const express = require('express');
const router = express.Router();
const { KV } = require('../models');
const { requireAuth } = require('../middleware');

router.use(requireAuth);

router.get('/:key', (req, res) => {
  const value = KV.get(req.params.key);
  res.json({ key: req.params.key, value: value == null ? null : value });
});

router.put('/:key', (req, res) => {
  const { value } = req.body || {};
  // value 一律以字串儲存（前端傳進來的本來就是 JSON.stringify 過的字串）
  const toStore = value == null ? null : (typeof value === 'string' ? value : JSON.stringify(value));
  KV.set(req.params.key, toStore);
  res.json({ ok: true });
});

router.delete('/:key', (req, res) => {
  KV.delete(req.params.key);
  res.json({ ok: true });
});

module.exports = router;
