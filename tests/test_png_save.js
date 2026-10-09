'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
async function check(){
 const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8'),file={name:'lr2-record-2026-10-08-lamps.png',type:'image/png'},button={disabled:false},status={textContent:''},downloads=[],shares=[];
 const context=vm.createContext({sheetImage:file,sheetImageRevision:1,$:id=>id==='sheet-save'?button:status,downloadSheetImage:image=>downloads.push(image),navigator:{maxTouchPoints:1,canShare:()=>true,share:payload=>{shares.push(payload);return Promise.resolve()}}});
 vm.runInContext(html.match(/async function saveSheetImage\(\)\{[\s\S]*?\n\}/)[0],context);
 const sharing=context.saveSheetImage();
 assert.equal(shares.length,1,'Sharing starts synchronously while the button click is active');
 assert.equal(shares[0].files[0],file);await sharing;assert.equal(downloads.length,0);assert.equal(button.disabled,false);
 context.navigator.share=()=>Promise.reject(Object.assign(new Error('cancelled'),{name:'AbortError'}));await context.saveSheetImage();assert.equal(downloads.length,0,'Cancelling the share sheet does not download unexpectedly');assert.match(status.textContent,/キャンセル/);
 context.navigator.canShare=()=>false;await context.saveSheetImage();assert.equal(downloads.length,1);assert.equal(downloads[0],file);
 context.navigator.canShare=()=>true;context.navigator.share=()=>Promise.reject(Object.assign(new Error('not available'),{name:'NotAllowedError'}));await context.saveSheetImage();assert.equal(downloads.length,2,'Unavailable native sharing falls back to saving the same PNG');
 let finish;context.navigator.share=()=>new Promise(resolve=>{finish=resolve});const oldShare=context.saveSheetImage();context.sheetImageRevision++;context.sheetImage=null;button.disabled=true;finish();await oldShare;assert.equal(button.disabled,true,'An older share operation cannot enable an unprepared new image');
 console.log('PNG save: immediate native share, cancel, download fallback and image switching passed');
}
check().catch(error=>{console.error(error);process.exitCode=1});

