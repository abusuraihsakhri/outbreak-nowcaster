/* Pure, dependency-free illustrative reporting-delay correction. */
(function (root) {
  'use strict';
  const CSV_HEADERS = ['date','reported','age_days','completeness','nowcast','additional_estimated'];
  function parseDate(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error('Dates must use YYYY-MM-DD.');
    const ms = Date.parse(`${value}T00:00:00Z`);
    if (!Number.isFinite(ms) || new Date(ms).toISOString().slice(0,10) !== value) throw new Error(`Invalid calendar date: ${value}`);
    return ms;
  }
  function parseDelays(value) {
    const parts = String(value).split(',').map(x => x.trim());
    if (parts.length < 1 || parts.length > 60 || parts.some(x => x === '')) throw new Error('Provide 1–60 comma-separated reporting-delay weights.');
    const weights = parts.map(Number);
    if (weights.some(x => !Number.isFinite(x) || x < 0)) throw new Error('Reporting-delay weights must be finite and nonnegative.');
    const total = weights.reduce((a,b)=>a+b,0);
    if (!Number.isFinite(total) || total <= 0 || weights[0] <= 0) throw new Error('Delay weights must sum to a positive value, including day zero.');
    return weights.map(x=>x/total);
  }
  function parseCSV(text) {
    if (typeof text !== 'string' || text.length > 1000000) throw new Error('CSV is limited to 1 MB of text.');
    const raw = text.replace(/^\uFEFF/, '');
    const lines = [];
    let row=[], cell='', insideQuotes=false, closedQuote=false;
    for (let i=0; i<raw.length; i++) {
      const char=raw[i];
      if (insideQuotes) {
        if (char === '"' && raw[i+1] === '"') { cell+='"'; i++; }
        else if (char === '"') { insideQuotes=false; closedQuote=true; }
        else cell+=char;
      } else if (char === '"' && !cell && !closedQuote) insideQuotes=true;
      else if (char === ',') { row.push(cell); cell=''; closedQuote=false; }
      else if (char === '\r' || char === '\n') {
        if (char === '\r' && raw[i+1] === '\n') i++;
        row.push(cell); cell=''; closedQuote=false;
        if (row.some(x=>x.trim()!=='')) lines.push(row);
        row=[];
      } else {
        if (closedQuote || char === '"') throw new Error('Malformed CSV quotation.');
        cell+=char;
      }
    }
    if (insideQuotes) throw new Error('Unterminated quoted CSV cell.');
    row.push(cell);
    if (row.some(x=>x.trim()!=='')) lines.push(row);
    if (lines.length<2) throw new Error('Supply a header and at least one data row.');
    const headers=lines.shift().map(x=>x.trim().toLowerCase());
    const d=headers.indexOf('date'), c=headers.indexOf('reported');
    if (d<0 || c<0 || headers.filter(x=>x==='date').length!==1 || headers.filter(x=>x==='reported').length!==1) throw new Error('CSV needs unique date,reported column headers.');
    return lines.map((fields,i)=>{
      if (fields.length!==headers.length) throw new Error(`CSV row ${i+2} has the wrong number of columns.`);
      return {date:fields[d].trim(),reported:fields[c].trim()};
    });
  }
  function nowcastCounts(rows, asOf, delays) {
    const currentMs=parseDate(asOf);
    if (!Array.isArray(delays) || !delays.length || delays.some(x=>!Number.isFinite(x)||x<0)) throw new Error('Invalid delay distribution.');
    const sum=delays.reduce((a,b)=>a+b,0);
    if (Math.abs(sum-1)>1e-9 || !(delays[0]>0)) throw new Error('Delay probabilities must sum to one with positive day-zero probability.');
    const cumulative=[]; let total=0;
    for(const p of delays) { total+=p; cumulative.push(Math.min(1,total)); }
    if(!rows.length) throw new Error('No observations.');
    const seen=new Set();
    const output=rows.map(row=>{
      const ms=parseDate(row.date);
      if(ms>currentMs) throw new Error(`Event date ${row.date} is after as-of date.`);
      if(seen.has(row.date)) throw new Error(`Duplicate event date: ${row.date}`);
      seen.add(row.date);
      const raw=String(row.reported).trim();
      if(!/^\d+$/.test(raw)) throw new Error(`Cases must be nonnegative integers on ${row.date}.`);
      const observed=Number(raw);
      if(!Number.isSafeInteger(observed)) throw new Error(`Case count too large on ${row.date}.`);
      const age=Math.round((currentMs-ms)/86400000);
      const complete=cumulative[Math.min(age,cumulative.length-1)];
      const estimate=observed/complete;
      if(!Number.isFinite(estimate)||estimate>Number.MAX_SAFE_INTEGER) throw new Error(`Nowcast overflow on ${row.date}.`);
      return {date:row.date,reported:observed,age_days:age,completeness:Math.round(complete*1e6)/1e6,
        nowcast:Math.round(estimate*100)/100,additional_estimated:Math.round((estimate-observed)*100)/100};
    });
    return output.sort((a,b)=>a.date.localeCompare(b.date));
  }
  function toCSV(rows) { return [CSV_HEADERS.join(','),...rows.map(row=>CSV_HEADERS.map(k=>row[k]).join(','))].join('\r\n')+'\r\n'; }
  const api={parseDate,parseDelays,parseCSV,nowcastCounts,toCSV};
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
  root.OutbreakNowcast=api;
})(typeof globalThis!=='undefined'?globalThis:this);
