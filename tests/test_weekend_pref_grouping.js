// 驗證「週末需求健檢誤判」bug 的修正。
// 問題:原本用 Math.ceil((day + firstWd) / 7) 幫星期六/日分組,
// 在某些月份起始星期下,會把同一個週末的六跟日拆到不同組別,導致誤判「六日都沒休」。
// 修正:改成「星期六一定跟隔天的星期日配對」,不再用公式硬算分組。

function isRestCode(v){ return v==='休' || v==='R1' || v==='R2' || v==='R'; }

// 模擬某個月的星期對照(day1 = 星期二,對照使用者實際回報問題的那個月)
function getWeekday(day){
  const map = [2,3,4,5,6,0,1]; // 0=Sun...6=Sat, day1對應星期二(2)
  return map[(day-1)%7];
}

function checkWeekendPref(codes, nDays, prefType){
  const weekends = [];
  for(let day=1; day<=nDays; day++){
    const wd = getWeekday(day);
    if(wd===6){
      const sunDay = day+1;
      const sunRest = sunDay<=nDays ? isRestCode(codes[sunDay-1]) : null;
      weekends.push({sat: isRestCode(codes[day-1]), sun: sunRest});
    } else if(wd===0 && day===1){
      weekends.push({sat: null, sun: isRestCode(codes[day-1])});
    }
  }
  if(prefType==='w1') return !weekends.some(w=> !(w.sat||w.sun)); // true = 有滿足
  if(prefType==='w5') return !weekends.some(w=> w.sat===false || w.sun===false);
  return null;
}

let pass=0, fail=0;
function test(name, cond){
  if(cond){ pass++; console.log(`✅ ${name}`); }
  else { fail++; console.log(`❌ ${name}`); }
}

// ---- 案例1:使用者實際回報的情境(劉婷貞,8月,1號=星期二) ----
// 每個週末六或日至少有一天是R(休假),理論上應該「滿足」w1需求
const codes1 = ['R','3Di','3Di','3Di','3Di','R','3Di','3Di','R','3Di','3Di','3Di','R','3Di','3Di','R','3Di','3Di','3Di','R','3Di','3Di','R','3Di','3Di','R','3Di','3Di','R','R'];
test('案例1:六日至少休一天,實際上每週末都有休,應判定為「滿足」', checkWeekendPref(codes1, codes1.length, 'w1'));

// ---- 案例2:真的沒有滿足的情況,應該要抓出來(不能改過頭變成都不檢查) ----
// 故意讓某個週末六日都上班
const codes2 = codes1.slice();
codes2[4] = '3Di';  // day5(六) 改成上班
codes2[5] = '3Di';  // day6(日) 改成上班,這個週末六日都沒休
test('案例2:真的有一個週末六日都沒休,應該判定為「未滿足」', !checkWeekendPref(codes2, codes2.length, 'w1'));

// ---- 案例3:w5(六日都要休),驗證同樣的分組修正也適用 ----
const codes3 = codes1.map(v=> (v==='3Di') ? '休' : v); // 假設全部白班日都改休,週末應該都符合w5
test('案例3:六日都休息(w5),全部休假的情境應判定為「滿足」', checkWeekendPref(codes3, codes3.length, 'w5'));

console.log(`\n通過 ${pass} / 失敗 ${fail}`);
process.exit(fail>0?1:0);
