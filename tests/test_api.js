'use strict';
/**
 * 後端 API 端對端測試。
 * 用一個暫時的資料庫檔啟動真正的 Express 伺服器,再用 fetch 打 API,
 * 驗證:第一次設定管理者、登入、共用資料讀寫、帳號管理、權限保護、防止把最後管理者刪光。
 *
 * 執行:node tests/test_api.js（需 Node 18+,內建 fetch）
 */
const path = require('path');
const fs = require('fs');
const os = require('os');
const assert = require('assert');

// 用暫存資料庫 + 測試用金鑰,不動到正式資料
const tmpDb = path.join(os.tmpdir(), 'sched-test-' + Date.now() + '.db');
process.env.DB_PATH = tmpDb;
process.env.JWT_SECRET = 'test-secret';
process.env.PORT = '0'; // 讓系統自動配一個空閒的埠
process.env.NODE_ENV = 'test';

const app = require('../server/index');

let pass = 0, fail = 0;
async function check(name, fn){
  try { await fn(); console.log('✅ ' + name); pass++; }
  catch(e){ console.log('❌ ' + name + ' → ' + e.message); fail++; }
}

(async function run(){
  // 啟動伺服器,取得實際埠號
  const server = app.listen(0);
  await new Promise(r => server.once('listening', r));
  const base = 'http://127.0.0.1:' + server.address().port;

  const req = async (method, url, { token, body } = {}) => {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const res = await fetch(base + url, { method, headers, body: body != null ? JSON.stringify(body) : undefined });
    let data = null; try { data = await res.json(); } catch(e){}
    return { status: res.status, data };
  };

  let adminToken = null;
  let staffUserId = null;
  let adminRecoveryCode = null;

  await check('一開始 needsSetup 應為 true', async () => {
    const r = await req('GET', '/api/auth/status');
    assert.strictEqual(r.data.needsSetup, true);
  });

  await check('未登入時讀取共用資料應被擋(401)', async () => {
    const r = await req('GET', '/api/storage/staff-data-v3');
    assert.strictEqual(r.status, 401);
  });

  await check('setup 建立第一個管理者並拿到 token', async () => {
    const r = await req('POST', '/api/auth/setup', { body: { username: 'admin', password: 'secret123' } });
    assert.strictEqual(r.status, 200);
    assert.ok(r.data.token, '應回傳 token');
    assert.strictEqual(r.data.user.isSuperAdmin, true);
    adminToken = r.data.token;
    assert.ok(/^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(r.data.recoveryCode || ''), 'setup 應回傳 XXXX-XXXX-XXXX 格式的救援碼');
    adminRecoveryCode = r.data.recoveryCode;
  });

  await check('已有帳號後 needsSetup 應為 false', async () => {
    const r = await req('GET', '/api/auth/status');
    assert.strictEqual(r.data.needsSetup, false);
  });

  await check('重複 setup 應被拒(409)', async () => {
    const r = await req('POST', '/api/auth/setup', { body: { username: 'x', password: 'y' } });
    assert.strictEqual(r.status, 409);
  });

  await check('密碼錯誤登入失敗(401)', async () => {
    const r = await req('POST', '/api/auth/login', { body: { username: 'admin', password: 'wrong' } });
    assert.strictEqual(r.status, 401);
  });

  await check('密碼正確登入成功', async () => {
    const r = await req('POST', '/api/auth/login', { body: { username: 'admin', password: 'secret123' } });
    assert.strictEqual(r.status, 200);
    assert.ok(r.data.token);
  });

  await check('登入後可寫入並讀回共用資料', async () => {
    const payload = JSON.stringify([{ id: 's1', name: '王小明' }]);
    const w = await req('PUT', '/api/storage/staff-data-v3', { token: adminToken, body: { value: payload } });
    assert.strictEqual(w.status, 200);
    const rd = await req('GET', '/api/storage/staff-data-v3', { token: adminToken });
    assert.strictEqual(rd.data.value, payload);
  });

  await check('第二個人用自己的 token 也看得到同一份共用資料', async () => {
    // 先建立一個一般帳號
    const c = await req('POST', '/api/users', { token: adminToken, body: {
      username: 'nurse1', password: 'pw123456', editRoles: ['nursing'], viewRoles: ['nursing'], isSuperAdmin: false } });
    assert.strictEqual(c.status, 201);
    staffUserId = c.data.user.id;
    const login = await req('POST', '/api/auth/login', { body: { username: 'nurse1', password: 'pw123456' } });
    const nurseToken = login.data.token;
    const rd = await req('GET', '/api/storage/staff-data-v3', { token: nurseToken });
    assert.ok(rd.data.value.includes('王小明'), '應看到同一份資料');
  });

  await check('一般帳號不能管理使用者(403)', async () => {
    const login = await req('POST', '/api/auth/login', { body: { username: 'nurse1', password: 'pw123456' } });
    const r = await req('GET', '/api/users', { token: login.data.token });
    assert.strictEqual(r.status, 403);
  });

  await check('帳號名稱重複應被拒(409)', async () => {
    const r = await req('POST', '/api/users', { token: adminToken, body: { username: 'admin', password: 'zzz111' } });
    assert.strictEqual(r.status, 409);
  });

  await check('可以刪除一般帳號', async () => {
    const r = await req('DELETE', '/api/users/' + staffUserId, { token: adminToken });
    assert.strictEqual(r.status, 200);
  });

  await check('不能刪掉最後一個超級管理者', async () => {
    const list = await req('GET', '/api/users', { token: adminToken });
    const admin = list.data.users.find(u => u.username === 'admin');
    const r = await req('DELETE', '/api/users/' + admin.id, { token: adminToken });
    assert.strictEqual(r.status, 400);
  });

  await check('/api/auth/me 用 token 換回目前使用者', async () => {
    const r = await req('GET', '/api/auth/me', { token: adminToken });
    assert.strictEqual(r.data.user.username, 'admin');
  });

  await check('偽造 token 應被拒(401)', async () => {
    const r = await req('GET', '/api/auth/me', { token: 'not-a-real-token' });
    assert.strictEqual(r.status, 401);
  });

  // ---- 忘記密碼救援機制（修正14，後端原生實作）----
  await check('忘記密碼:錯誤救援碼應被拒(401)', async () => {
    const r = await req('POST', '/api/auth/recover', { body: { username: 'admin', recoveryCode: 'WRON-GWRO-NGWR', newPassword: 'newpass123' } });
    assert.strictEqual(r.status, 401);
  });

  await check('忘記密碼:不存在的帳號應回 404', async () => {
    const r = await req('POST', '/api/auth/recover', { body: { username: '查無此人', recoveryCode: adminRecoveryCode, newPassword: 'x' } });
    assert.strictEqual(r.status, 404);
  });

  await check('忘記密碼:正確救援碼可重設密碼(大小寫/空白不敏感)', async () => {
    const messyCode = ('  ' + adminRecoveryCode.toLowerCase() + '  ');
    const r = await req('POST', '/api/auth/recover', { body: { username: 'admin', recoveryCode: messyCode, newPassword: 'brandNew123' } });
    assert.strictEqual(r.status, 200);
  });

  await check('重設後:舊密碼失敗、新密碼成功', async () => {
    const oldLogin = await req('POST', '/api/auth/login', { body: { username: 'admin', password: 'secret123' } });
    assert.strictEqual(oldLogin.status, 401);
    const newLogin = await req('POST', '/api/auth/login', { body: { username: 'admin', password: 'brandNew123' } });
    assert.strictEqual(newLogin.status, 200);
    adminToken = newLogin.data.token;
  });

  await check('救援碼是一次性:同一組不會外洩在使用者清單裡', async () => {
    const r = await req('GET', '/api/users', { token: adminToken });
    const admin = r.data.users.find(u => u.username === 'admin');
    assert.ok(admin && admin.recoveryCode === undefined && admin.recovery_code === undefined, '使用者清單不應含救援碼');
  });

  await check('新增帳號會回傳一次性救援碼', async () => {
    const r = await req('POST', '/api/users', { token: adminToken, body: { username: 'nurse_r', password: 'pw123456', editRoles: [], viewRoles: [], isSuperAdmin: false } });
    assert.strictEqual(r.status, 201);
    assert.ok(/^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(r.data.recoveryCode || ''), '新增帳號應回傳救援碼');
  });

  await check('超級管理者可重設某帳號的救援碼,新碼可用來重設密碼', async () => {
    const list = await req('GET', '/api/users', { token: adminToken });
    const nurse = list.data.users.find(u => u.username === 'nurse_r');
    const reset = await req('POST', '/api/users/' + nurse.id + '/reset-recovery', { token: adminToken });
    assert.strictEqual(reset.status, 200);
    const newCode = reset.data.recoveryCode;
    assert.ok(/^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(newCode || ''), '應回傳新救援碼');
    const rec = await req('POST', '/api/auth/recover', { body: { username: 'nurse_r', recoveryCode: newCode, newPassword: 'resetpw999' } });
    assert.strictEqual(rec.status, 200);
    const login = await req('POST', '/api/auth/login', { body: { username: 'nurse_r', password: 'resetpw999' } });
    assert.strictEqual(login.status, 200);
  });

  await check('一般帳號不能重設別人的救援碼(403)', async () => {
    const login = await req('POST', '/api/auth/login', { body: { username: 'nurse_r', password: 'resetpw999' } });
    const list = await req('GET', '/api/users', { token: adminToken });
    const someone = list.data.users.find(u => u.username === 'admin');
    const r = await req('POST', '/api/users/' + someone.id + '/reset-recovery', { token: login.data.token });
    assert.strictEqual(r.status, 403);
  });

  server.close();
  try { fs.unlinkSync(tmpDb); } catch(e){}
  try { fs.unlinkSync(tmpDb + '-wal'); } catch(e){}
  try { fs.unlinkSync(tmpDb + '-shm'); } catch(e){}

  console.log('\n通過 ' + pass + ' / 失敗 ' + fail);
  process.exit(fail === 0 ? 0 : 1);
})();
