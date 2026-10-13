const test = require('node:test');
const assert = require('node:assert/strict');
const {parseCSV,parseDelays,parseDate,nowcastCounts,toCSV} = require('./nowcast.js');
test('validated weighted delay correction agrees with Python test vector',()=>{
  const records=nowcastCounts(parseCSV('date,reported\n2026-10-11,90\n2026-10-13,5\n2026-10-12,15\n2026-10-10,100'),'2026-10-13',parseDelays('0.5,0.3,0.2'));
  assert.deepEqual(records.map(x=>x.nowcast),[100,90,18.75,10]);
  assert.deepEqual(records.map(x=>x.completeness),[1,1,.8,.5]);
  assert.match(toCSV(records),/^date,reported,age_days,completeness,nowcast,additional_estimated/);
});
test('quoted CSV and CRLF parsed without treating values as markup',()=>{
  const csv='note,date,reported\r\n"<img src=x>",2026-10-12,"12"\r\n';
  assert.deepEqual(parseCSV(csv),[{date:'2026-10-12',reported:'12'}]);
});
test('reject invalid weights and dates',()=>{
  for(const value of ['0,1','nan,1','-1,2','','1,','Infinity,1']) assert.throws(()=>parseDelays(value));
  assert.throws(()=>parseDate('2026-02-30'));
  assert.throws(()=>parseDate('20261012'));
});
test('reject duplicate, future, malformed and unsafe counts',()=>{
  const reference='2026-10-13', delays=parseDelays('0.5,0.5');
  for(const [date,reported] of [['2026-10-14','1'],['2026-10-13','-1'],['2026-10-13','1.5'],['2026-10-13','NaN'],['2026-10-13','9007199254740992']]) assert.throws(()=>nowcastCounts([{date,reported}],reference,delays));
  assert.throws(()=>nowcastCounts([{date:reference,reported:'1'},{date:reference,reported:'2'}],reference,delays));
});
test('malformed CSV rejected',()=>{
  for(const txt of ['date,reported\n"2026-10-13,5','date,reported\n2026-10-13','date,date,reported\n2026-10-13,2026-10-13,5']) assert.throws(()=>parseCSV(txt));
});
