// 驗證「匯入 Excel」功能的姓名比對邏輯:
// - 姓名完全相符才算比對成功
// - 比對不到的姓名要被列出來,不能悄悄跳過或自動新增人員
// - Excel 裡的空白儲存格不應該覆蓋既有資料(這個規則在實際寫入 monthData 時套用,這裡先測比對本身)

function matchImportRows(rows, items, nDays){
  const matched = [];
  const unmatchedNames = [];
  for(let r=1; r<rows.length; r++){
    const row = rows[r];
    const name = String(row[0]||'').trim();
    if(!name) continue;
    const p = items.find(x=>x.name===name);
    const dayVals = [];
    for(let day=1; day<=nDays; day++){
      const cellVal = row[1+day];
      dayVals.push(cellVal===undefined || cellVal===null ? '' : String(cellVal).trim());
    }
    if(p){ matched.push({staffId:p.id, name, values:dayVals}); }
    else { unmatchedNames.push(name); }
  }
  return {matched, unmatchedNames};
}

let pass=0, fail=0;
function test(name, cond){
  if(cond){ pass++; console.log(`✅ ${name}`); }
  else { fail++; console.log(`❌ ${name}`); }
}

const items = [
  {id:'A', name:'王小明'},
  {id:'B', name:'陳小華'},
];
const nDays = 3;

// 模擬 sheet_to_json({header:1}) 的輸出格式:第0欄姓名,第1欄代碼,第2欄起是日期
const rows = [
  ['姓名','代碼','8/1(六)','8/2(日)','8/3(一)'],
  ['王小明','N001','2Di','休','2Di'],
  ['陳小華','N002','','E',''],       // 有空白儲存格,應該保留空字串而不是報錯
  ['林大同','N999','休','休','休'],   // 系統裡沒有這個人,應該進 unmatchedNames
];

const result = matchImportRows(rows, items, nDays);

test('比對成功2位', result.matched.length===2);
test('比對不到1位(林大同)', result.unmatchedNames.length===1 && result.unmatchedNames[0]==='林大同');
test('王小明的班別資料正確對應(2Di,休,2Di)', JSON.stringify(result.matched.find(m=>m.name==='王小明').values)===JSON.stringify(['2Di','休','2Di']));
test('陳小華的空白儲存格保留為空字串,不是undefined', result.matched.find(m=>m.name==='陳小華').values[0]==='');
test('陳小華的空白儲存格數量正確(2個空白)', result.matched.find(m=>m.name==='陳小華').values.filter(v=>v==='').length===2);

// 空白列應該被略過,不算進matched也不算進unmatched
const rowsWithBlank = rows.concat([['']]);
const result2 = matchImportRows(rowsWithBlank, items, nDays);
test('姓名空白的列會被略過,不影響比對結果數量', result2.matched.length===2 && result2.unmatchedNames.length===1);

console.log(`\n通過 ${pass} / 失敗 ${fail}`);
process.exit(fail>0?1:0);
