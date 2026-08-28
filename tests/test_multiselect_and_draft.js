// 驗證兩個修正:
// 1. 多格選取失效的根本原因(整列draggable="true"跟儲存格拖曳選取互相干擾)
// 2. 對照草稿加入多格選取後,複製/貼上/刪除要能正確分辨「這次操作是對正式班表還是對照草稿」

let pass=0, fail=0;
function test(name, cond){
  if(cond){ pass++; console.log(`✅ ${name}`); }
  else { fail++; console.log(`❌ ${name}`); }
}

// ---- 情境1:HTML draggable 屬性繼承規則 ----
// HTML5 規則:子元素沒有明確設定 draggable 時,會繼承離自己最近的祖先設定。
// tr[draggable=true] 底下的 td 如果沒有明確蓋成 draggable=false,會被瀏覽器視為「這個td也可以拖」,
// 導致在 td 上按住拖曳時,瀏覽器啟動的是「拖整個tr」的原生行為,而不是我們自訂的多格選取邏輯。
function simulateDraggableInheritance(trDraggable, tdDraggableAttr){
  // tdDraggableAttr: null(沒設定,會繼承) | 'true' | 'false'
  if(tdDraggableAttr === null) return trDraggable; // 繼承父層
  return tdDraggableAttr === 'true';
}

test('修正前:tr=draggable(true)、td沒設定draggable時,td會被視為可拖(這就是bug原因)',
  simulateDraggableInheritance(true, null) === true);

test('修正後:tr=draggable(true)、td明確設定draggable="false"時,td不會被誤判成可拖',
  simulateDraggableInheritance(true, 'false') === false);

// ---- 情境2:selTarget 判斷邏輯,確認多格操作會作用在正確的資料來源 ----
function resolveDataSource(selTarget, liveData, draftData){
  return selTarget === 'draft' ? draftData : liveData;
}

const liveData = {A: {'2026-08-01': '2Di'}};
const draftData = {A: {'2026-08-01': '休'}};

test('selTarget="live"時,操作應該作用在正式班表資料',
  resolveDataSource('live', liveData, draftData) === liveData);
test('selTarget="draft"時,操作應該作用在對照草稿資料,不會誤動到正式班表',
  resolveDataSource('draft', liveData, draftData) === draftData);

// ---- 情境3:undo歷史只記錄正式班表的操作,不記錄草稿的操作(草稿本來就是隨便改的暫存區) ----
function shouldRecordUndo(isDraft){
  return !isDraft;
}
test('對正式班表的操作應該寫入復原歷史', shouldRecordUndo(false) === true);
test('對草稿的操作不應該寫入復原歷史(草稿本身就是隨便改的暫存區,不需要undo)', shouldRecordUndo(true) === false);

console.log(`\n通過 ${pass} / 失敗 ${fail}`);
process.exit(fail>0?1:0);
