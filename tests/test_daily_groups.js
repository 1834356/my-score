'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8');
const context=vm.createContext({});
vm.runInContext(html.split('\n').find(line=>line.startsWith('const lamps=')),context);
for(const name of ['dailyChanges','reachedAAA','scoreRate','lampCounts']){
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
