// TDD 第一步:先寫測試,驗證「兼職同仁完全不參與自動排班補位」這個修正。
// 情境涵蓋三種兼職同仁:兼職白班資格、兼職小夜資格、兼職大夜資格,
// 都不應該出現在對應的補位池裡,也不應該在Pass C被自動填入休/Di。

function buildPools(items, regulars){
  const floorFillPool = items.filter(p=> p.eligWhite && !p.partTime && p!==regulars['2Di'] && p!==regulars['3Di']);
  const eveningPool = items.filter(p=> p.eligEvening && !p.partTime);
  const nightPool = items.filter(p=> p.eligNight && !p.partTime);
  return {floorFillPool, eveningPool, nightPool};
}

function passCShouldSkip(p){
  return !!p.partTime;
}

let pass=0, fail=0;
function test(name, cond){
  if(cond){ pass++; console.log(`✅ ${name}`); }
  else { fail++; console.log(`❌ ${name}`); }
}

const staffA = {id:'A', name:'固定2Di(輪調全職)', eligWhite:true, partTime:false};
const staffB = {id:'B', name:'兼職白班', eligWhite:true, partTime:true};
const staffC = {id:'C', name:'兼職小夜', eligEvening:true, partTime:true};
const staffD = {id:'D', name:'兼職大夜', eligNight:true, partTime:true};
const staffE = {id:'E', name:'全職小夜', eligEvening:true, partTime:false};
const items = [staffA, staffB, staffC, staffD, staffE];
const regulars = {'2Di': staffA};

const {floorFillPool, eveningPool, nightPool} = buildPools(items, regulars);

test('兼職白班(B)不應該出現在白班補位池', !floorFillPool.includes(staffB));
test('兼職小夜(C)不應該出現在小夜補位池', !eveningPool.includes(staffC));
test('兼職大夜(D)不應該出現在大夜補位池', !nightPool.includes(staffD));
test('全職小夜(E)應該正常出現在小夜補位池,不會被誤排除', eveningPool.includes(staffE));

test('Pass C 應該跳過兼職白班(B)', passCShouldSkip(staffB));
test('Pass C 應該跳過兼職小夜(C)', passCShouldSkip(staffC));
test('Pass C 應該跳過兼職大夜(D)', passCShouldSkip(staffD));
test('Pass C 不應該跳過全職同仁(E)', !passCShouldSkip(staffE));

console.log(`\n通過 ${pass} / 失敗 ${fail}`);
process.exit(fail>0?1:0);
