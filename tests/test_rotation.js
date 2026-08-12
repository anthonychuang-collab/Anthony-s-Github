// ---- 把系統中的實作複製過來(之後要跟正式檔案同步) ----
const ROTATION_SEQUENCE = ['2Di','3Di','float'];
function rotationCategoryForMonth(p, monthCursorDate){
  if(!p.rotationStartMonth || !p.rotationStartShift) return null;
  const [sy, sm] = p.rotationStartMonth.split('-').map(Number);
  if(!sy || !sm) return null;
  const startIdx = ROTATION_SEQUENCE.indexOf(p.rotationStartShift);
  if(startIdx===-1) return null;
  const monthsElapsed = (monthCursorDate.getFullYear()*12 + monthCursorDate.getMonth()) - (sy*12 + (sm-1));
  if(monthsElapsed < 0) return null;
  const stepsForward = Math.floor(monthsElapsed / 3);
  const idx = (startIdx + stepsForward) % ROTATION_SEQUENCE.length;
  return ROTATION_SEQUENCE[idx];
}

// ---- 小型測試跑器 ----
let pass = 0, fail = 0;
function test(name, actual, expected){
  const ok = actual === expected;
  if(ok){ pass++; console.log(`✅ ${name}`); }
  else { fail++; console.log(`❌ ${name}  期望=${expected}  實際=${actual}`); }
}
function m(y, mo){ return new Date(y, mo-1, 1); } // mo: 1-12

// ---- 測試案例 ----

// 案例1:起始月份當月,應該就是起始班別本身
test('起始當月 = 起始班別(2Di)',
  rotationCategoryForMonth({rotationStartMonth:'2026-07', rotationStartShift:'2Di'}, m(2026,7)),
  '2Di');

// 案例2:起始後第1、2個月,還在同一輪(每3個月才換)
test('起始後第1個月,仍是2Di',
  rotationCategoryForMonth({rotationStartMonth:'2026-07', rotationStartShift:'2Di'}, m(2026,8)),
  '2Di');
test('起始後第2個月,仍是2Di',
  rotationCategoryForMonth({rotationStartMonth:'2026-07', rotationStartShift:'2Di'}, m(2026,9)),
  '2Di');

// 案例3:起始後第3個月,應該換下一班(2Di → 3Di)
test('起始後第3個月,換成3Di',
  rotationCategoryForMonth({rotationStartMonth:'2026-07', rotationStartShift:'2Di'}, m(2026,10)),
  '3Di');

// 案例4:起始後第6個月,應該再換一輪(3Di → 貼班)
test('起始後第6個月,換成float(貼班)',
  rotationCategoryForMonth({rotationStartMonth:'2026-07', rotationStartShift:'2Di'}, m(2027,1)),
  'float');

// 案例5:起始後第9個月,應該繞回2Di(循環)
test('起始後第9個月,繞回2Di',
  rotationCategoryForMonth({rotationStartMonth:'2026-07', rotationStartShift:'2Di'}, m(2027,4)),
  '2Di');

// 案例6:跨年份邊界(月份計算不能只看月份數字,要看年份)
test('跨年邊界:2026-11起算,查詢2027-02(隔3個月應換班)',
  rotationCategoryForMonth({rotationStartMonth:'2026-11', rotationStartShift:'3Di'}, m(2027,2)),
  'float');

// 案例7:查詢日期在起始月份「之前」,應該回傳 null(還沒開始輪調)
test('查詢月份早於起始月份,回傳null',
  rotationCategoryForMonth({rotationStartMonth:'2026-07', rotationStartShift:'2Di'}, m(2026,5)),
  null);

// 案例8:起始班別不是從2Di開始,而是從3Di開始(要能從中間起跳)
test('起始班別=3Di,起始當月就是3Di',
  rotationCategoryForMonth({rotationStartMonth:'2026-07', rotationStartShift:'3Di'}, m(2026,7)),
  '3Di');
test('起始班別=3Di,3個月後換float',
  rotationCategoryForMonth({rotationStartMonth:'2026-07', rotationStartShift:'3Di'}, m(2026,10)),
  'float');
test('起始班別=3Di,6個月後應該是2Di(繞了2/3圈,還沒回到3Di)',
  rotationCategoryForMonth({rotationStartMonth:'2026-07', rotationStartShift:'3Di'}, m(2027,1)),
  '2Di');
test('起始班別=3Di,9個月後才真正繞回3Di(完整一圈)',
  rotationCategoryForMonth({rotationStartMonth:'2026-07', rotationStartShift:'3Di'}, m(2027,4)),
  '3Di');

// 案例9:缺資料時要回傳null,不能拋錯
test('沒有設定輪調起始月份,回傳null',
  rotationCategoryForMonth({rotationStartMonth:'', rotationStartShift:'2Di'}, m(2026,7)),
  null);
test('沒有設定輪調起始班別,回傳null',
  rotationCategoryForMonth({rotationStartMonth:'2026-07', rotationStartShift:''}, m(2026,7)),
  null);

console.log(`\n通過 ${pass} / 失敗 ${fail}`);
process.exit(fail>0 ? 1 : 0);
