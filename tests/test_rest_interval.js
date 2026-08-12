// ---- 從系統複製過來的實作 ----
const SHIFT_TIME_RANGE = {'Di':[8,16],'2Di':[8,16],'3Di':[8,16],'2D8':[8,20],'3D8':[8,20],'D8':[8,20],'E':[16,24],'E8':[20,32],'N':[24,32]};
function gapHours(prevCode, nextCode){
  if(!SHIFT_TIME_RANGE[prevCode] || !SHIFT_TIME_RANGE[nextCode]) return null;
  const end1 = SHIFT_TIME_RANGE[prevCode][1];
  const start2 = 24 + SHIFT_TIME_RANGE[nextCode][0];
  return start2 - end1;
}

let pass=0, fail=0;
function test(name, actual, expected){
  const ok = actual === expected;
  if(ok){ pass++; console.log(`✅ ${name}`); }
  else { fail++; console.log(`❌ ${name}  期望=${expected}  實際=${actual}`); }
}

// 大夜(N, 24-32即當日24:00~隔日08:00)接白班(Di, 08:00-16:00),應該是0小時銜接(明顯違規)
test('N接隔天Di,間隔應為0小時', gapHours('N','Di'), 0);

// 大夜接小夜(隔天16:00),應為8小時(N結束08:00,小夜16:00開始)
test('N接隔天E,間隔應為8小時', gapHours('N','E'), 8);

// 白班(結束16:00)接隔天白班(08:00開始) = 24-16+8 = 16小時,足夠
test('Di接隔天Di,間隔應為16小時', gapHours('Di','Di'), 16);

// 白班(結束16:00)接隔天小夜(16:00開始) = 24小時,足夠
test('Di接隔天E,間隔應為24小時', gapHours('Di','E'), 24);

// 小夜(結束24:00)接隔天大夜(24:00開始,即當天24:00到隔天08:00)= 24小時,足夠
test('E接隔天N,間隔應為24小時', gapHours('E','N'), 24);

// 12小時大夜支援(E8, 20:00-隔日08:00)接白班(08:00) = 0小時,違規
test('E8接隔天Di,間隔應為0小時', gapHours('E8','Di'), 0);

// 未知代碼(如休/R1/兼職Dp)應該回傳null,不應該被誤判成有間隔問題
test('未定義代碼(休)回傳null,不納入計算', gapHours('休','Di'), null);
test('未定義代碼(Dp兼職)回傳null,不納入計算', gapHours('Dp','E'), null);

console.log(`\n通過 ${pass} / 失敗 ${fail}`);
process.exit(fail>0?1:0);
