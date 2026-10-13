(function(){
  'use strict';
  const calc=globalThis.OutbreakNowcast;
  const get=id=>document.getElementById(id);
  const number=v=>Number(v).toLocaleString(undefined,{maximumFractionDigits:2});
  let last=null;
  function dateString(date){return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;}
  function loadExample(){
    const date=new Date(`${get('as-of').value}T12:00:00`);
    if(!Number.isFinite(date.getTime()))return;
    const counts=[16,18,15,20,21,25,23,27,29,26,30,23,15,11], lines=['date,reported'];
    counts.forEach((count,i)=>{
      const day=new Date(date);day.setDate(date.getDate()-(counts.length-1-i));
      lines.push(`${dateString(day)},${count}`);
    });
    get('observations').value=lines.join('\n');get('error').hidden=true;
  }
  function render(rows){
    last=rows;get('export').disabled=false;
    get('result-caption').textContent=`As of ${get('as-of').value} · ${rows.length} event dates · fixed reporting-delay correction`;
    const sum=key=>rows.reduce((acc,row)=>acc+row[key],0);
    get('total-reported').textContent=number(sum('reported'));
    get('total-nowcast').textContent=number(sum('nowcast'));
    get('total-extra').textContent=number(sum('additional_estimated'));
    const tbody=get('table-body');tbody.replaceChildren();
    for(const row of rows){
      const tr=document.createElement('tr');
      for(const val of [row.date,number(row.reported),`${number(row.completeness*100)}%`,number(row.nowcast)]){
        const td=document.createElement('td');td.textContent=val;tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    const display=rows.slice(-30), chart=get('chart');chart.replaceChildren();
    const max=Math.max(1,...display.map(row=>row.nowcast));
    display.forEach((row,i)=>{
      const col=document.createElement('div');col.className='bar-col';
      col.title=`${row.date}: reported ${row.reported}, nowcast ${row.nowcast}`;
      for(const [cls,val] of [['observed',row.reported],['adjusted',row.nowcast]]){
        const bar=document.createElement('div');bar.className=`bar ${cls}`;
        bar.style.height=`${100*val/max}%`;col.appendChild(bar);
      }
      if(i%Math.max(1,Math.ceil(display.length/6))===0||i===display.length-1){
        const label=document.createElement('span');label.className='bar-label';
        label.textContent=row.date.slice(5);col.appendChild(label);
      }
      chart.appendChild(col);
    });
    chart.setAttribute('aria-label',`Observed versus delay-adjusted event counts for ${display.length} dates through ${rows.at(-1).date}. Numeric values appear in the table below.`);
  }
  get('as-of').value=dateString(new Date());loadExample();
  get('load-example').addEventListener('click',loadExample);
  get('nowcast-form').addEventListener('submit',event=>{
    event.preventDefault();
    const error=get('error');error.hidden=true;last=null;get('export').disabled=true;
    try{
      const delays=calc.parseDelays(get('delays').value);
      const observations=calc.parseCSV(get('observations').value);
      render(calc.nowcastCounts(observations,get('as-of').value,delays));
    }catch(exc){
      error.textContent=exc instanceof Error?exc.message:'Invalid input.';
      error.hidden=false;
      for(const id of ['total-reported','total-nowcast','total-extra'])get(id).textContent='—';
      get('chart').replaceChildren();get('table-body').replaceChildren();
      get('result-caption').textContent='Correct the data and recalculate.';
    }
  });
  get('csv-upload').addEventListener('change',async event=>{
    const file=event.target.files?.[0];if(!file)return;
    try{
      if(file.size>1000000)throw new Error('CSV is limited to 1 MB.');
      const content=await file.text();calc.parseCSV(content);
      get('observations').value=content;get('error').hidden=true;
    }catch(exc){get('error').textContent=exc.message||'Could not read the CSV.';get('error').hidden=false;}
    finally{event.target.value='';}
  });
  get('export').addEventListener('click',()=>{
    if(!last)return;
    const blob=new Blob([calc.toCSV(last)],{type:'text/csv;charset=utf-8'});
    const url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download='outbreak-nowcast.csv';document.body.appendChild(link);
    link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
})();
