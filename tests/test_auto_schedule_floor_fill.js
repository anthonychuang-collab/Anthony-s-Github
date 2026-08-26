// 這份測試驗證「自動排班 bug 修正」:
// 沒有設定三個月輪調、但有白班資格的護理人員,應該要能被排入 2Di/3Di 實際班別,
// 而不是像修正前那樣整個月只拿到休假。
//
// 注意:這裡複製了一份簡化版的 Pass B 補位邏輯進行測試,
// 不是直接 import src/index.html(因為那個檔案不是模組)。
// 如果之後把商業邏輯抽成獨立模組,這份測試應該改成真正 import 那個模組。

function runPassB(items, data, regulars, nDays){
  function getCode(p, day){ return data[p.id][day] || ''; }
  function setCode(p, day, code){ data[p.id][day] = code; }
  function isEmpty(p, day){ return !getCode(p, day); }

  const floorFillPool = items.filter(p=> p.eligWhite && p!==regulars['2Di'] && p!==regulars['3Di']);
  const eveningPool = items.filter(p=> p.eligEvening);
  const floorCount = {}, eCount = {};
  items.forEach(p=>{ floorCount[p.id]=0; eCount[p.id]=0; });

  for(let day=1; day<=nDays; day++){
    ['2Di','3Di'].forEach(cat=>{
      const covered = items.some(p=> getCode(p, day)===cat);
      if(covered) return;
      const candidates = floorFillPool.filter(p=> isEmpty(p, day));
      candidates.sort((a,b)=> floorCount[a.id]-floorCount[b.id]);
      if(candidates.length){ setCode(candidates[0], day, cat); floorCount[candidates[0].id]++; }
    });
    const dayHasE = items.some(p=> getCode(p, day)==='E');
    if(!dayHasE){
      const candidates = eveningPool.filter(p=> isEmpty(p, day));
      candidates.sort((a,b)=> eCount[a.id]-eCount[b.id]);
      if(candidates.length){ setCode(candidates[0], day, 'E'); eCount[candidates[0].id]++; }
    }
  }
}

let pass=0, fail=0;
function test(name, cond){
  if(cond){ pass++; console.log(`✅ ${name}`); }
  else { fail++; console.log(`❌ ${name}`); }
}

// ---- 情境:1位固定2Di(輪調), 1位一般白班無輪調, 1位小夜資格 ----
const nDays = 10;
const staffA = {id:'A', name:'固定2Di(輪調)', eligWhite:true};
const staffB = {id:'B', name:'一般白班(無輪調)', eligWhite:true};
const staffC = {id:'C', name:'小夜資格', eligEvening:true};
const items = [staffA, staffB, staffC];
const data = {A:{}, B:{}, C:{}};

const regulars = {'2Di': staffA};
for(let d=1; d<=nDays; d++){ data.A[d] = (d%6===0) ? '休' : '2Di'; }

runPassB(items, data, regulars, nDays);

// ---- 驗證 ----
const bCodes = [];
for(let d=1; d<=nDays; d++) bCodes.push(data.B[d]);
test('B(一般白班,無輪調)本月有被排到至少一次3Di或2Di', bCodes.some(v=>v==='2Di'||v==='3Di'));
test('B完全沒有被排到工作班別的情況(修正前的bug)不應該發生', !(bCodes.every(v=>!v || v==='休')));

const cCodes = [];
for(let d=1; d<=nDays; d++) cCodes.push(data.C[d]);
test('C(小夜資格)本月至少被排一次E班', cCodes.some(v=>v==='E'));

// A休假那天(第6天),應該有人補上2Di的缺
test('A第6天休假,2Di缺口應該被B或其他人補上', data.B[6]==='2Di' || items.some(p=>data[p.id][6]==='2Di'));

console.log(`\n通過 ${pass} / 失敗 ${fail}`);
process.exit(fail>0?1:0);
