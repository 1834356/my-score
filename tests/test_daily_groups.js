'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8');
const context=vm.createContext({});
vm.runInContext(html.split('\n').find(line=>line.startsWith('const lamps=')),context);
for(const name of ['dailyChanges','reachedAAA','scoreRate','lampCounts','monthsFor','calendarDates','monthSummary','sheetChunks']){
  const definition=html.split('\n').find(line=>line.startsWith(`function ${name}(`));
  assert.ok(definition,`Missing ${name}`);
  vm.runInContext(definition,context);
}
const records=[
  {chartId:'a',oldLamp:2,newLamp:3,oldMinBp:50,newMinBp:30,oldExScore:150,newExScore:160,totalNotes:100},
  {chartId:'b',oldLamp:1,newLamp:1,oldMinBp:200,newMinBp:200,oldExScore:50,newExScore:50,totalNotes:100},
  {chartId:'a',oldLamp:3,newLamp:4,oldMinBp:30,newMinBp:0,oldExScore:160,newExScore:180,totalNotes:100},
];
const changes=context.dailyChanges(records);
assert.equal(changes.length,2);
assert.equal(changes[0].oldLamp,2);
assert.equal(changes[0].newLamp,4);
assert.equal(changes[0].oldMinBp,50);
assert.equal(changes[0].newMinBp,0);
assert.equal(changes[0].oldExScore,150);
assert.equal(changes[0].newExScore,180);
assert.equal(records[0].newLamp,3,'Original play records stay unchanged');
assert.equal(context.reachedAAA(177,100),false);
assert.equal(context.reachedAAA(178,100),true);
assert.equal(context.reachedAAA(16,9),true);
assert.equal(context.reachedAAA(null,100),false);
assert.equal(context.reachedAAA(0,0),false);
assert.equal(context.scoreRate(180,100),90);
assert.equal(context.scoreRate(0,100),0);
assert.equal(context.scoreRate(200,100),100);
assert.equal(context.scoreRate(null,100),null);
assert.equal(context.scoreRate(10,0),null);
assert.equal(context.scoreRate(undefined,100),null);
assert.deepEqual(Array.from(context.lampCounts([{lamp:2},{lamp:2},{lamp:0},{lamp:6}])),[1,0,2,0,0,0,1]);
console.log('Daily grouping, score rate, and lamp breakdown checks passed');

assert.deepEqual(Array.from(context.monthsFor([{date:'2024-12-31'},{date:'2025-02-01'}],'2025-03-01T12:00:00+09:00')),['2025-03','2025-02','2025-01','2024-12']);
assert.deepEqual(Array.from(context.monthsFor([],null)),[]);
const leap=context.calendarDates('2024-02');
assert.equal(leap.filter(Boolean).length,29);
assert.deepEqual(Array.from(leap.slice(0,4)),[null,null,null,null]);
assert.equal(leap.at(-1),'2024-02-29');
assert.equal(context.calendarDates('2026-02').filter(Boolean).length,28);
const month=context.monthSummary([{date:'2024-02-01',plays:2,notes:2000,seconds:240,notesMissingPlays:0},{date:'2024-02-02',plays:1,notes:0,seconds:60,notesMissingPlays:1},{date:'2024-02-03',plays:0,notes:0,seconds:0},{date:'2024-02-04',plays:1,seconds:30},{date:'2024-03-01',plays:99,notes:99000,seconds:9900}], '2024-02');
assert.equal(month.notes,2000);assert.equal(month.plays,4);assert.equal(month.playDays,3);assert.equal(month.seconds,330);assert.equal(month.missingPlays,1);assert.equal(month.missingDays,1);
console.log('Monthly totals, missing note counts, leap years and year boundaries passed');

for(const counts of [[],[1],[75],[2,4,25,2,60],[1,1,1,1,1,1,1,1,1],[200,1,400]]){
 for(let columns=1;columns<=6;columns++){
  const packed=context.sheetChunks(counts,columns);
  assert.equal(packed.length,columns);
  const actual=Array.from(packed).flatMap(column=>Array.from(column).flatMap(chunk=>Array.from({length:chunk.end-chunk.start},(_,i)=>`${chunk.group}:${chunk.start+i}`)));
  const expected=counts.flatMap((count,group)=>Array.from({length:count},(_,i)=>`${group}:${i}`));
  assert.deepEqual(actual,expected,'All screenshot updates remain present exactly once and in order');
 }
}
console.log('Screenshot column splitting preserves all updates across 1–6 columns');
