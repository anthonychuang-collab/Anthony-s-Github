// 驗證顏色選擇從固定6色升級成完整色票(任意hex色碼)後的相容邏輯。
// 舊資料存的是像 'blue'/'green' 這種代號,新資料存的是像 '#3A7BD5' 這種hex色碼,
// resolveColor() 要兩種都能正確處理,不能讓舊資料顯示壞掉。

const EVENT_COLORS = [
  {v:'blue', t:'藍', bg:'#DCEBFB', fg:'#1D5FA8'},
  {v:'green', t:'綠', bg:'#DCEEDC', fg:'#2E7D32'},
  {v:'orange', t:'橘', bg:'#FBE7CE', fg:'#B5651D'},
  {v:'red', t:'紅', bg:'#FBDCDC', fg:'#C1573A'},
  {v:'purple', t:'紫', bg:'#EAE0F5', fg:'#6A3FA0'},
  {v:'gray', t:'灰', bg:'#E6E6E0', fg:'#5C5C52'},
];

function contrastTextColor(hex){
  const h = hex.replace('#','');
  if(h.length!==6) return '#000';
  const r = parseInt(h.substr(0,2),16), g = parseInt(h.substr(2,2),16), b = parseInt(h.substr(4,2),16);
  const luminance = (0.299*r + 0.587*g + 0.114*b) / 255;
  return luminance > 0.6 ? '#1F2A1D' : '#FFFFFF';
}
function tintBg(hex){
  const h = hex.replace('#','');
  if(h.length!==6) return {bg:hex, fg:contrastTextColor(hex)};
  const r = parseInt(h.substr(0,2),16), g = parseInt(h.substr(2,2),16), b = parseInt(h.substr(4,2),16);
  const mix = (c)=> Math.round(c + (255-c)*0.78);
  const bg = `#${[mix(r),mix(g),mix(b)].map(n=>n.toString(16).padStart(2,'0')).join('')}`;
  return {bg, fg:hex};
}
function resolveColor(v){
  if(!v) return EVENT_COLORS[3];
  const preset = EVENT_COLORS.find(c=>c.v===v);
  if(preset) return preset;
  if(/^#[0-9A-Fa-f]{6}$/.test(v)){
    const t = tintBg(v);
    return {v, t:v, bg:t.bg, fg:t.fg};
  }
  return EVENT_COLORS[3];
}
function presetToHex(v){
  if(/^#[0-9A-Fa-f]{6}$/.test(v)) return v;
  const p = EVENT_COLORS.find(c=>c.v===v);
  return p ? p.fg : '#5AA94E';
}

let pass=0, fail=0;
function test(name, cond){
  if(cond){ pass++; console.log(`✅ ${name}`); }
  else { fail++; console.log(`❌ ${name}`); }
}

// ---- 舊資料相容性(存的是代號,不是hex) ----
test('舊資料"blue"仍能正確解析成藍色系樣式', resolveColor('blue').bg==='#DCEBFB' && resolveColor('blue').fg==='#1D5FA8');
test('舊資料"red"仍能正確解析', resolveColor('red').fg==='#C1573A');
test('presetToHex把舊代號轉成色票初始值(給color input用)', presetToHex('green')==='#2E7D32');
test('presetToHex遇到已經是hex的值,原樣傳回', presetToHex('#3A7BD5')==='#3A7BD5');

// ---- 新資料(使用者自己用色票選的hex) ----
const custom = resolveColor('#3A7BD5');
test('新的hex色碼能被正確辨識、不會被誤判成預設紅色', custom.fg==='#3A7BD5');
test('hex色碼會自動算出一個淺色底(tint background)', /^#[0-9A-Fa-f]{6}$/.test(custom.bg) && custom.bg!=='#3A7BD5');

// ---- 對比色計算 ----
test('淺色(接近白色)背景應該配深色文字', contrastTextColor('#F5F5F0')==='#1F2A1D');
test('深色背景應該配白色文字', contrastTextColor('#1A1A1A')==='#FFFFFF');

// ---- 異常輸入不應該報錯,要有合理fallback ----
test('空值不報錯,回傳預設(紅色系)', resolveColor('').fg==='#C1573A');
test('格式不對的字串(不是hex也不是預設代號)不報錯,回傳預設', resolveColor('not-a-color').fg==='#C1573A');
test('3碼簡寫hex(不符合完整6碼規則)視為無效,回傳預設', resolveColor('#fff').fg==='#C1573A');

console.log(`\n通過 ${pass} / 失敗 ${fail}`);
process.exit(fail>0?1:0);
