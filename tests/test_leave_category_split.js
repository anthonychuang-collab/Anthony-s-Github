// 驗證「休假天數 / 特休天數 / 合計」拆分邏輯。
// 問題:自訂代碼(例如使用者自己建的「特」代表特休)原本完全不會被算進休假統計,
// 因為系統只認得寫死的 休/R1/R2/R 幾種代碼。
// 修正:自訂代碼可以在後台標記「計入休假統計」為 不算/算特休/算一般休假,
// 系統依這個標記分別加總。

function customLeaveCategory(v, customShiftCodes){
  const c = customShiftCodes.find(c=>c.code===v);
  return c ? (c.leaveCategory || '') : '';
}
function isSpecialLeaveCode(v, customShiftCodes){
  return customLeaveCategory(v, customShiftCodes)==='special';
}
function isRegularLeaveCodeOnly(v, customShiftCodes){
  return v==='休' || v==='R1' || v==='R2' || v==='R' || customLeaveCategory(v, customShiftCodes)==='regular';
}

let pass=0, fail=0;
function test(name, cond){
  if(cond){ pass++; console.log(`✅ ${name}`); }
  else { fail++; console.log(`❌ ${name}`); }
}

// ---- 情境:使用者自訂了「特」代表特休,標記為 special ----
const customShiftCodes = [
  {code:'特', label:'特休', color:'orange', leaveCategory:'special'},
  {code:'公', label:'公假', color:'blue', leaveCategory:'regular'},
  {code:'訓', label:'教育訓練(不算休假)', color:'gray', leaveCategory:''},
];

const codes = ['休','R1','特','特','公','2Di','訓','R2','特'];

let regularCount = 0, specialCount = 0;
codes.forEach(v=>{
  if(isSpecialLeaveCode(v, customShiftCodes)) specialCount++;
  else if(isRegularLeaveCodeOnly(v, customShiftCodes)) regularCount++;
});

test('一般休假天數應為4天(休/R1/R2/公)', regularCount===4);
test('特休天數應為3天(3個「特」)', specialCount===3);
test('合計應為7天', regularCount+specialCount===7);
test('「訓」標記為不算休假,不應該被算進任何一欄', !isSpecialLeaveCode('訓', customShiftCodes) && !isRegularLeaveCodeOnly('訓', customShiftCodes));
test('「2Di」這種工作代碼不應該被誤算進休假', !isSpecialLeaveCode('2Di', customShiftCodes) && !isRegularLeaveCodeOnly('2Di', customShiftCodes));

// 沒有在 customShiftCodes 裡定義的代碼,不應該報錯,也不該被誤算
test('未定義的代碼不會報錯、也不算休假', !isSpecialLeaveCode('XYZ', customShiftCodes) && !isRegularLeaveCodeOnly('XYZ', customShiftCodes));

console.log(`\n通過 ${pass} / 失敗 ${fail}`);
process.exit(fail>0?1:0);
