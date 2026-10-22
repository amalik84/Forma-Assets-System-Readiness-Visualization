"""Renders the snapshot into ONE self-contained HTML file (no internet, no AI needed).

Visual language: "Go / No-Go gate board" (warm neutral palette, verdict stamp,
gate matrix, trend line). Systems = rows, issue types / forms = gates.
"""
import json
import re

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FOMO1 · System Readiness Board</title>
<style>
:root{--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink-2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);
--good:#0ca30c;--warning:#fab219;--serious:#ec835a;--critical:#d03b3b;--accent:#2a78d6}
*{box-sizing:border-box}
body{margin:0;font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--page);color:var(--ink)}
header{padding:14px 24px;background:var(--surface);border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}
header h1{font-size:18px;margin:0}
.sub{color:var(--ink-2);font-size:13px}
.seg{display:inline-flex;border:1px solid var(--axis);border-radius:8px;overflow:hidden}
.seg button{border:0;background:#fff;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer;border-right:1px solid var(--grid)}
.seg button:last-child{border-right:0}.seg button.on{background:#0b0b0b;color:#fff}
.controls{display:flex;gap:10px;flex-wrap:wrap;padding:12px 24px;align-items:center}
.controls input{padding:6px 9px;border:1px solid var(--axis);border-radius:6px;font:inherit;font-size:13px;background:#fff;width:210px}
.grid{display:grid;grid-template-columns:1fr 420px;gap:16px;padding:0 24px 24px}
.col{display:flex;flex-direction:column;gap:16px;min-width:0}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px}
.card h2{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--ink-2);margin:0 0 10px}
.hero{display:grid;grid-template-columns:auto 1fr 1fr 1fr;gap:24px;align-items:center}
.hero .big{font-size:40px;font-weight:700;line-height:1}.hero .lbl{color:var(--ink-2);font-size:12px}
.stamp{display:inline-flex;align-items:center;gap:10px;padding:10px 16px;border-radius:10px;font-weight:700;font-size:20px;border:2px solid}
.stamp.go{color:#006300;border-color:var(--good);background:#eef8ee}
.stamp.nogo{color:#a32727;border-color:var(--critical);background:#fbeeee}
.stamp.none{color:var(--muted);border-color:var(--axis);background:#f0efec}
.vbar{grid-column:1/-1;display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--grid)}
.vbar i{display:block;height:100%}
.vleg{grid-column:1/-1;display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--ink-2);margin-top:-12px}
table.matrix{border-collapse:separate;border-spacing:2px;width:100%;font-size:12px}
.matrix th{font-weight:600;color:var(--ink-2);padding:4px;text-align:center;vertical-align:bottom;max-width:92px}
.matrix th.rowh{text-align:left}
.matrix td{padding:0;height:34px;text-align:center;border-radius:4px;font-variant-numeric:tabular-nums}
.matrix td.name{text-align:left;padding:0 8px;background:transparent;white-space:nowrap;cursor:pointer;border-radius:6px}
.matrix td.name:hover,.matrix td.name.sel{background:#eeede8}
.matrix td.name .meta{color:var(--muted);font-size:11px}
.mini{height:3px;width:120px;background:#f3d6d6;border-radius:2px;margin-top:3px;overflow:hidden}.mini i{display:block;height:100%;background:var(--good)}
.cell{cursor:pointer;font-weight:600}
.cell.clear{background:#eef8ee;color:#006300}
.cell.risk{background:#fdecc4;color:#6b4700}
.cell.block{background:var(--critical);color:#fff}
.cell.sel{outline:2px solid var(--accent);outline-offset:1px}
.verdict{font-weight:700;white-space:nowrap;padding:0 8px;text-align:left!important}
.verdict.go{color:#006300}.verdict.cond{color:#6b4700}.verdict.nogo{color:#a32727}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--ink-2);margin-top:10px}
.sw{display:inline-block;width:14px;height:14px;border-radius:3px;vertical-align:-3px;margin-right:4px;border:1px solid var(--border)}
table.blist{width:100%;border-collapse:collapse;font-size:12px}
.blist th{text-align:left;color:var(--ink-2);font-weight:600;border-bottom:1px solid var(--axis);padding:5px 6px;position:sticky;top:0;background:var(--surface)}
.blist td{border-bottom:1px solid var(--grid);padding:5px 6px;vertical-align:top}
.blist tr.grp td{background:#f0efec;font-weight:600;cursor:pointer;border-bottom:0;padding-top:8px}
.blist tr.grp td .meta{font-weight:400;color:var(--ink-2)}
.blist tr.a{cursor:pointer}.blist tr.a:hover td{background:#f5f4f0}.blist tr.a.sel td{background:#e9f1fc}
.via,.own,.tag{display:inline-block;font-size:11px;font-weight:600;padding:1px 6px;border-radius:999px;white-space:nowrap}
.via{background:#eef2fa;color:#1f4f99}.own{background:#f0efec;color:var(--ink-2)}
.tag.bad{background:#fbeeee;color:#a32727}.tag.warn{background:#fdecc4;color:#6b4700}.tag.ok{background:#eef8ee;color:#006300}
.scroll{max-height:460px;overflow:auto}
.issue{border-top:1px solid var(--grid);padding:8px 0;font-size:13px}
.issue .meta,.meta{color:var(--ink-2);font-size:12px}
.note{font-size:12px;color:var(--muted)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
#tip{position:fixed;pointer-events:none;background:#0b0b0b;color:#fff;font-size:12px;padding:6px 8px;border-radius:6px;display:none;z-index:1000;max-width:320px}
.empty{padding:18px;color:var(--muted);text-align:center;font-size:13px}
footer{color:var(--muted);font-size:12px;padding:6px 24px 24px;text-align:center}
.kv{display:flex;justify-content:space-between;gap:8px;font-size:13px;padding:3px 0}
@media(max-width:1100px){.grid{grid-template-columns:1fr}.hero{grid-template-columns:1fr 1fr}}
</style></head><body>
<header>
  <div><h1>FOMO1 · System Readiness Board</h1>
  <div class="sub" id="hdr"></div></div>
  <div class="sub" id="today"></div>
</header>
<div class="controls">
  <span class="sub">Show</span>
  <div class="seg" id="view"><button data-v="all" class="on">All systems</button><button data-v="bad">Not ready only</button></div>
  <input type="search" id="q" placeholder="Search systems…">
</div>
<div class="grid">
  <div class="col">
    <div class="card hero" id="hero"></div>
    <div class="card">
      <h2>Gate matrix · open items per system and gate</h2>
      <table class="matrix" id="matrix"></table>
      <div class="legend">
        <span><span class="sw" style="background:#eef8ee"></span>✓ Gate clear</span>
        <span><span class="sw" style="background:#fdecc4"></span>! Warning (draft, or item you cannot see)</span>
        <span><span class="sw" style="background:#d03b3b"></span>✕ Blocking item open</span>
        <span>Number = open items reached from the system's assets. Click a cell for details, a system name to focus it.</span>
      </div>
    </div>
    <div class="card">
      <h2 id="atitle">Assets</h2>
      <div class="note" id="anote" style="margin-bottom:8px"></div>
      <div class="scroll" style="max-height:380px"><table class="blist" id="alist"></table></div>
    </div>
    <div class="card">
      <h2 id="btitle">Blocking items</h2>
      <div class="note" id="bnote" style="margin-bottom:8px"></div>
      <div class="scroll"><table class="blist" id="blist"></table></div>
    </div>
  </div>
  <div class="col">
    <div class="card"><h2>Systems by verdict</h2><div id="verd"></div></div>
    <div class="card"><h2>Open items on assets · trend</h2><div id="trend"></div><div class="note" id="trendnote"></div></div>
    <div class="card"><h2 id="dtitle">Details</h2><div id="detail" class="note">Click a cell in the matrix, or an asset in the list, to see the items behind it.</div></div>
  </div>
</div>
<footer id="foot"></footer>
<div id="tip"></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const M=D.meta,S=D.summary;
const TODAY=new Date(M.generatedAt.slice(0,10)+'T00:00:00');
const fmt=d=>d.toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'});
const pd=v=>{if(!v)return null;const d=new Date(String(v).slice(0,10)+'T00:00:00');return isNaN(d)?null:d;};
$('hdr').textContent=`${M.projectName} · systems grouped by ${M.groupBy==='category'?'asset category':'"'+M.systemAttribute+'"'} · max depth ${M.maxDepth}`;
$('today').textContent='Refreshed: '+M.generatedAt.replace('T',' ');

/* ---------- model ---------- */
const colOf=r=>r.kind==='form'?'Forms':r.kind==='status'?'Status rule':(r.type?String(r.type).split(' / ')[0]:'Issues');
const SYS=D.systems.map(s=>{
  const assets=s.assetIds.map(i=>D.assets[i]);
  const items=new Map();
  assets.forEach(a=>a.refs.forEach(r=>{
    if(r.state==='ok')return;
    const k=r.kind+'|'+r.id; let it=items.get(k);
    if(!it){it={r,assets:[],col:null};items.set(k,it);}
    it.assets.push({a,path:r.path});
  }));
  const list=[...items.values()];
  const blocking=list.filter(i=>i.r.state==='blocking');
  const warn=list.filter(i=>i.r.state!=='blocking');
  return {name:s.name,assets,assetCount:s.assetCount,readyCount:s.readyCount,items:list,blocking,warn,
    verdict:blocking.length?'nogo':warn.length?'cond':'go'};
});
const typeCount={};
SYS.forEach(s=>s.items.forEach(i=>{if(i.r.kind==='issue'){const c=colOf(i.r);typeCount[c]=(typeCount[c]||0)+1;}}));
const topTypes=Object.entries(typeCount).sort((a,b)=>b[1]-a[1]).map(x=>x[0]);
const issueCols=topTypes.slice(0,5);
const COLS=[...issueCols];
if(topTypes.length>5)COLS.push('Other issues');
if(SYS.some(s=>s.items.some(i=>i.r.kind==='form')))COLS.push('Forms');
if(SYS.some(s=>s.items.some(i=>i.r.kind==='status')))COLS.push('Status rule');
if(!COLS.length)COLS.push('Issues','Forms');
SYS.forEach(s=>s.items.forEach(i=>{const c=colOf(i.r);i.col=(i.r.kind==='issue'&&!issueCols.includes(c))?'Other issues':c;}));
const VR={nogo:0,cond:1,go:2};
const VTXT={go:['go','✓ GO'],cond:['cond','! CONDITIONAL'],nogo:['nogo','✕ NO-GO']};
const ICON={go:'✓',cond:'!',nogo:'✕'};
const COLOR={go:'#0ca30c',cond:'#fab219',nogo:'#d03b3b'};
const sortSys=(a,b)=>VR[a.verdict]-VR[b.verdict]||b.blocking.length-a.blocking.length||a.name.localeCompare(b.name);

let view='all',selSys=null,selCell=null,selAsset=null;
const TIPS=[];
const tip=$('tip');
const showTip=(e,h)=>{tip.innerHTML=h;tip.style.display='block';tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY+12)+'px';};
const hideTip=()=>tip.style.display='none';
const tipIdx=h=>{TIPS.push(h);return TIPS.length-1;};
const link=(r,txt)=>r.url?`<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(txt??r.label)}</a>`:esc(txt??r.label);
const stTag=r=>({blocking:`<span class="tag bad">${esc(r.status||'blocking')}</span>`,warning:`<span class="tag warn">${esc(r.status||'warning')}</span>`,
  unknown:'<span class="tag warn">no access</span>',ok:r.status?`<span class="tag ok">${esc(r.status)}</span>`:''}[r.state]);
const isOverdue=r=>r.kind==='issue'&&r.state==='blocking'&&pd(r.due)&&pd(r.due)<TODAY;
const via=it=>{const p=it.assets[0].path.slice(0,-1);return p.length<=1?'<span class="own">Direct on asset</span>':`<span class="via">${esc(p.slice(1).join(' → '))}</span>`;};

/* ---------- hero ---------- */
function renderHero(){
  const n={go:0,cond:0,nogo:0};SYS.forEach(s=>n[s.verdict]++);
  const total=SYS.length,uniq=new Map();
  SYS.forEach(s=>s.blocking.forEach(i=>uniq.set(i.r.kind+'|'+i.r.id,i)));
  const blockers=[...uniq.values()],overdue=blockers.filter(i=>isOverdue(i.r)).length;
  const allGo=total&&!n.nogo;
  const pct=S.assets?Math.round(S.assetsReady/S.assets*100):100;
  $('hero').innerHTML=`
   <div><div class="lbl">Programme verdict</div><div class="stamp ${total?(allGo?'go':'nogo'):'none'}" style="margin-top:6px">${total?(allGo?'✓ GO':'✕ NO-GO'):'–'}</div></div>
   <div><div class="big">${n.go} / ${total}</div><div class="lbl">systems clear to launch</div></div>
   <div><div class="big">${blockers.length}</div><div class="lbl">blocking items to close (${S.openIssues} issues, ${S.openForms} forms)</div></div>
   <div><div class="big" style="color:${overdue?'#a32727':'inherit'}">${overdue}</div><div class="lbl">blocking issues past due date</div></div>
   <div class="vbar" title="Systems by verdict">${['nogo','cond','go'].map(k=>n[k]?`<i style="width:${n[k]/total*100}%;background:${COLOR[k]}"></i>`:'').join('')}</div>
   <div class="vleg"><span><span class="sw" style="background:#d03b3b"></span>${n.nogo} no-go</span><span><span class="sw" style="background:#fab219"></span>${n.cond} conditional</span><span><span class="sw" style="background:#0ca30c"></span>${n.go} go</span><span>${S.assetsReady.toLocaleString()} of ${S.assets.toLocaleString()} assets clear (${pct}%)</span></div>`;
}

/* ---------- matrix ---------- */
function visibleSys(){
  const q=$('q').value.trim().toLowerCase();
  return SYS.filter(s=>(view==='all'||s.verdict!=='go')&&(!q||s.name.toLowerCase().includes(q))).sort(sortSys);
}
function renderMatrix(){
  const rows=visibleSys();
  if(!selSys||!SYS.find(s=>s.name===selSys))selSys=(rows[0]||SYS.slice().sort(sortSys)[0]||{}).name||null;
  const m=$('matrix');
  m.innerHTML=`<tr><th class="rowh">System</th>${COLS.map(c=>`<th>${esc(c)}</th>`).join('')}<th class="rowh">Verdict</th></tr>`+
   (rows.map(s=>{
     const pct=s.assetCount?Math.round(s.readyCount/s.assetCount*100):100;
     return `<tr><td class="name ${s.name===selSys?'sel':''}" data-n="${esc(s.name)}"><b>${esc(s.name)}</b>
       <div class="meta">${s.assetCount.toLocaleString()} assets · ${s.readyCount.toLocaleString()} clear</div><div class="mini"><i style="width:${pct}%"></i></div></td>`+
      COLS.map(c=>{
        const l=s.items.filter(i=>i.col===c),b=l.filter(i=>i.r.state==='blocking').length,w=l.length-b;
        const k=b?'block':w?'risk':'clear',txt=l.length?l.length:'✓';
        const ti=tipIdx(`<b>${esc(s.name)}</b><br>${esc(c)}: ${b} blocking${w?`, ${w} warning`:''}`);
        const sel=selCell&&selCell[0]===s.name&&selCell[1]===c;
        return `<td class="cell ${k} ${sel?'sel':''}" data-s="${esc(s.name)}" data-c="${esc(c)}" data-t="${ti}">${txt}</td>`;}).join('')+
      `<td class="verdict ${VTXT[s.verdict][0]}">${VTXT[s.verdict][1]}${s.blocking.length?`<div style="font-size:11px;font-weight:600;color:#52514e">${s.blocking.length} blocking${s.warn.length?` · ${s.warn.length} warn`:''}</div>`:''}</td></tr>`;}).join('')
   ||`<tr><td class="name note" colspan="${COLS.length+2}">No systems match.</td></tr>`);
  m.querySelectorAll('td.cell').forEach(td=>{
    td.onmousemove=e=>showTip(e,TIPS[+td.dataset.t]);td.onmouseleave=hideTip;
    td.onclick=()=>{selSys=td.dataset.s;selCell=[td.dataset.s,td.dataset.c];selAsset=null;renderAll();};
  });
  m.querySelectorAll('td.name[data-n]').forEach(td=>td.onclick=()=>{selSys=td.dataset.n;selCell=null;selAsset=null;renderAll();});
}

/* ---------- assets of selected system ---------- */
function renderAssets(){
  const s=SYS.find(x=>x.name===selSys);
  if(!s){$('atitle').textContent='Assets';$('alist').innerHTML='<tr><td class="empty">No system selected.</td></tr>';$('anote').textContent='';return;}
  $('atitle').textContent=`Assets in ${s.name}`;
  const list=s.assets.slice().sort((a,b)=>b.blockers-a.blockers||b.warnings-a.warnings||a.name.localeCompare(b.name));
  const CAP=150,shown=list.slice(0,CAP);
  $('anote').textContent=`${s.assetCount.toLocaleString()} assets, sorted by blockers first${list.length>CAP?` · showing the first ${CAP}`:''}. Click an asset to see everything linked to it.`;
  $('alist').innerHTML=`<tr><th>Asset</th><th>Category</th><th>Status</th><th>Readiness</th><th>Linked</th></tr>`+
   shown.map(a=>{const n=t=>a.refs.filter(r=>r.kind===t).length;
    return `<tr class="a ${a.id===selAsset?'sel':''}" data-id="${esc(a.id)}"><td><b>${esc(a.name)}</b>${a.description?`<div class="meta">${esc(a.description)}</div>`:''}</td>
     <td>${esc(a.category)}</td><td>${esc(a.status||'')}</td>
     <td>${a.ready?'<span class="tag ok">CLEAR</span>':`<span class="tag bad">${a.blockers} BLOCKER${a.blockers>1?'S':''}</span>`} ${a.warnings?`<span class="tag warn">${a.warnings} warn</span>`:''}</td>
     <td class="meta">${n('issue')} issues · ${n('form')} forms · ${n('document')} docs</td></tr>`;}).join('');
  $('alist').querySelectorAll('tr.a').forEach(tr=>tr.onclick=()=>{selAsset=tr.dataset.id;selCell=null;renderAssets();renderDetail();});
}

/* ---------- blocking items ---------- */
function renderBlockers(){
  const focus=selSys?SYS.find(s=>s.name===selSys):null;
  const groups=(focus?[focus]:SYS.slice().sort(sortSys)).filter(s=>s.blocking.length||focus);
  const CAP=250;let rowsShown=0,hidden=0;
  const total=new Set(groups.flatMap(s=>s.blocking.map(i=>i.r.kind+'|'+i.r.id))).size;
  $('btitle').textContent=focus?`Blocking items · ${focus.name}`:'Blocking items · all systems';
  $('bnote').innerHTML=`${total} distinct item${total===1?'':'s'} (open issues and open forms) reached from assets. Click a system row to focus it.`;
  const key=i=>[isOverdue(i.r)?0:1,pd(i.r.due)?pd(i.r.due).getTime():9e15];
  let h=`<tr><th>Item</th><th>Reached via</th><th>Type</th><th>Status</th><th>Date</th></tr>`;
  groups.forEach(s=>{
    h+=`<tr class="grp" data-n="${esc(s.name)}"><td colspan="5">${ICON[s.verdict]} ${esc(s.name)} <span class="meta">· ${s.blocking.length} blocking · ${s.assetCount.toLocaleString()} assets</span></td></tr>`;
    if(!s.blocking.length){h+='<tr><td colspan="5" class="note">✓ Nothing blocks this system.</td></tr>';return;}
    s.blocking.slice().sort((a,b)=>{const x=key(a),y=key(b);return x[0]-y[0]||x[1]-y[1];}).forEach(i=>{
      if(rowsShown>=CAP){hidden++;return;}rowsShown++;
      const r=i.r,d=pd(r.due),od=isOverdue(r);
      h+=`<tr><td><b>${link(r)}</b>${i.assets.length>1?`<div class="meta">on ${i.assets.length} assets</div>`:`<div class="meta">${esc(i.assets[0].a.name)}</div>`}</td>
       <td>${via(i)}</td><td>${esc(r.type||r.kind)}</td><td>${stTag(r)}</td>
       <td style="${od?'color:#a32727;font-weight:600':''}">${d?fmt(d):''}${od?' · overdue':''}</td></tr>`;});
  });
  if(hidden)h+=`<tr><td colspan="5" class="note">… ${hidden} more not shown. Focus a system to see its items.</td></tr>`;
  if(groups.length===0)h+='<tr><td colspan="5" class="empty">✓ No blocking items anywhere.</td></tr>';
  $('blist').innerHTML=h;
  $('blist').querySelectorAll('tr.grp').forEach(tr=>tr.onclick=()=>{selSys=tr.dataset.n;selCell=null;selAsset=null;renderAll();});
}

/* ---------- side cards ---------- */
function renderVerdict(){
  const n={go:0,cond:0,nogo:0};SYS.forEach(s=>n[s.verdict]++);
  const worst=SYS.slice().sort(sortSys).filter(s=>s.blocking.length).slice(0,6);
  const max=Math.max(1,...worst.map(s=>s.blocking.length));
  $('verd').innerHTML=
    `<div class="kv"><span>✕ No-go (blocking items)</span><b>${n.nogo}</b></div><div class="kv"><span>! Conditional (warnings only)</span><b>${n.cond}</b></div><div class="kv"><span>✓ Go</span><b>${n.go}</b></div>`+
    (worst.length?`<div class="note" style="margin:10px 0 4px">Most blocking items</div>`+worst.map(s=>`<div style="display:flex;align-items:center;gap:8px;margin:3px 0;cursor:pointer" data-n="${esc(s.name)}">
      <span style="width:130px;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(s.name)}">${esc(s.name)}</span>
      <span style="flex:1;background:#f0efec;border-radius:3px;height:10px"><i style="display:block;height:100%;width:${s.blocking.length/max*100}%;background:#d03b3b;border-radius:3px"></i></span>
      <b style="font-size:12px;width:28px;text-align:right">${s.blocking.length}</b></div>`).join(''):'');
  $('verd').querySelectorAll('[data-n]').forEach(el=>el.onclick=()=>{selSys=el.dataset.n;selCell=null;selAsset=null;renderAll();});
}
function renderTrend(){
  const h=(D.history||[]).slice(-60).map(r=>({d:String(r.date||'').slice(0,10),i:+r.openIssues||0,f:+r.openForms||0}));
  const el=$('trend');
  if(h.length<2){el.innerHTML='<div class="empty">The trend appears after two or more daily runs.</div>';$('trendnote').textContent='';return;}
  const W=380,H=200,l=34,r=60,t=10,b=24,max=Math.max(4,...h.map(p=>Math.max(p.i,p.f)));
  const X=k=>l+k/(h.length-1)*(W-l-r),Y=n=>t+(1-n/max)*(H-t-b);
  let g='';
  [0,.5,1].forEach(f=>{const v=Math.round(max*f);g+=`<line x1="${l}" x2="${W-r}" y1="${Y(v)}" y2="${Y(v)}" stroke="#e1e0d9"/><text x="${l-6}" y="${Y(v)+4}" text-anchor="end" font-size="11" fill="#898781">${v}</text>`;});
  g+=`<text x="${X(0)}" y="${H-6}" text-anchor="start" font-size="11" fill="#898781">${esc(h[0].d.slice(5))}</text><text x="${X(h.length-1)}" y="${H-6}" text-anchor="end" font-size="11" fill="#898781">Latest</text>`;
  const path=k=>h.map((p,j)=>(j?'L':'M')+X(j).toFixed(1)+','+Y(p[k]).toFixed(1)).join(' ');
  const L=h[h.length-1];
  g+=`<path d="${path('i')}" fill="none" stroke="#d03b3b" stroke-width="2"/><path d="${path('f')}" fill="none" stroke="#2a78d6" stroke-width="2"/>`;
  g+=`<circle cx="${X(h.length-1)}" cy="${Y(L.i)}" r="4" fill="#d03b3b" stroke="#fcfcfb" stroke-width="2"/><text x="${X(h.length-1)+8}" y="${Y(L.i)+(L.i>=L.f?-2:12)}" font-size="11">Issues ${L.i}</text>`;
  g+=`<circle cx="${X(h.length-1)}" cy="${Y(L.f)}" r="4" fill="#2a78d6" stroke="#fcfcfb" stroke-width="2"/><text x="${X(h.length-1)+8}" y="${Y(L.f)+(L.f>L.i?-2:12)}" font-size="11">Forms ${L.f}</text>`;
  g+=`<line id="xh" y1="${t}" y2="${H-b}" stroke="#c3c2b7" style="display:none"/><rect x="${l}" y="0" width="${W-l-r}" height="${H}" fill="transparent" id="hit"/>`;
  el.innerHTML=`<svg id="trendsvg" viewBox="0 0 ${W} ${H}" width="100%">${g}</svg>`;
  const svg=$('trendsvg'),hit=svg.querySelector('#hit'),xh=svg.querySelector('#xh');
  hit.onmousemove=e=>{const bx=svg.getBoundingClientRect(),x=(e.clientX-bx.left)/bx.width*W;
    const k=Math.max(0,Math.min(h.length-1,Math.round((x-l)/(W-l-r)*(h.length-1))));
    xh.setAttribute('x1',X(k));xh.setAttribute('x2',X(k));xh.style.display='';
    showTip(e,`${esc(h[k].d)}<br><span style="color:#f3a0a0">■</span> Open issues: ${h[k].i}<br><span style="color:#86b6ef">■</span> Open forms: ${h[k].f}`);};
  hit.onmouseleave=()=>{xh.style.display='none';hideTip();};
  const d=L.i+L.f-(h[0].i+h[0].f);
  $('trendnote').textContent=`Open issues and forms on assets, one point per run. Since ${h[0].d}: ${d<=0?'down '+(-d):'up '+d}.`;
}
function renderDetail(){
  const d=$('detail');
  const a=selAsset&&D.assets[selAsset],s=selCell&&SYS.find(x=>x.name===selCell[0]);
  if(a){
    const groups=[['status','Status rule'],['issue','Issues'],['form','Forms'],['document','Documents'],['asset','Linked assets'],['rfi','RFIs']];
    const order={blocking:0,unknown:1,warning:2,ok:3};
    $('dtitle').textContent='Asset references';d.className='';
    let h=`<div style="font-size:15px;font-weight:700">${a.url?`<a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.name)}</a>`:esc(a.name)}</div>
     <div class="meta">${esc(a.system)} · ${esc(a.category)} · status: ${esc(a.status||'n/a')} · ${a.ready?'<span class="tag ok">CLEAR</span>':'<span class="tag bad">NOT READY</span>'}</div>`;
    for(const [kind,title] of groups){
      const rs=a.refs.filter(r=>r.kind===kind).sort((x,y)=>order[x.state]-order[y.state]);
      if(!rs.length)continue;
      h+=`<div style="margin:14px 0 2px;font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#52514e">${title} (${rs.length})</div>`+
       rs.map(r=>`<div class="issue"><div style="display:flex;justify-content:space-between;gap:8px"><span>${link(r)}</span>${stTag(r)}</div>
        <div class="meta">${r.path.map((p,i)=>i===r.path.length-1?`<b>${esc(p)}</b>`:esc(p)).join(' → ')}${r.due?` · ${r.kind==='issue'?'due':'dated'} ${esc(String(r.due).slice(0,10))}`:''}${r.type?` · ${esc(r.type)}`:''}</div></div>`).join('');
    }
    if(!a.refs.length)h+='<div class="note" style="margin-top:10px">No linked issues, forms or documents found.</div>';
    d.innerHTML=h;
  }else if(s){
    const l=s.items.filter(i=>i.col===selCell[1]).sort((a,b)=>(a.r.state==='blocking'?0:1)-(b.r.state==='blocking'?0:1));
    $('dtitle').textContent=`${s.name} · ${selCell[1]}`;d.className='';
    d.innerHTML=l.length?l.map(i=>{const r=i.r;return `<div class="issue"><div style="display:flex;justify-content:space-between;gap:8px"><b>${link(r)}</b>${stTag(r)}</div>
      <div class="meta">${esc(r.type||r.kind)}${r.due?` · ${r.kind==='issue'?'due':'dated'} ${esc(String(r.due).slice(0,10))}`:''}${isOverdue(r)?' · <b style="color:#d03b3b">overdue</b>':''}</div>
      <div class="meta">${via(i)} ${i.assets.length>1?`on ${i.assets.length} assets (e.g. ${esc(i.assets[0].a.name)})`:esc(i.assets[0].a.name)}</div></div>`;}).join(''):'<div class="note">✓ No open items on this gate.</div>';
  }else{
    $('dtitle').textContent='Details';d.className='note';
    d.textContent='Click a cell in the matrix, or an asset in the list, to see the items behind it.';
  }
}
function renderAll(){TIPS.length=0;renderHero();renderMatrix();renderAssets();renderBlockers();renderVerdict();renderDetail();}
document.querySelectorAll('#view button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#view button').forEach(x=>x.classList.remove('on'));b.classList.add('on');view=b.dataset.v;selSys=null;selCell=null;selAsset=null;renderAll();});
$('q').oninput=()=>{selSys=null;selCell=null;selAsset=null;renderAll();};
$('foot').textContent=`Read-only snapshot · ${M.apiCalls??'–'} API calls · ${M.durationSec??'–'}s · closed issue statuses: ${M.issueClosed.join(', ')} · open form statuses: ${M.formOpen.join(', ')}`;
renderTrend();renderAll();
</script></body></html>"""


# The React build (../dashboard-ui/dist/index.html) contains <script id="fomo1-data" ...>placeholder</script>;
# we swap the placeholder for the day's snapshot. Matched loosely so Vite's HTML rewriting can't break it.
UI_DATA_RE = re.compile(r'<script\b[^>]*\bid="fomo1-data"[^>]*>.*?</script>', re.S)


def render(snapshot: dict) -> str:
    """Prefer the React + shadcn build; fall back to the plain-HTML board if it hasn't been built."""
    from config import S
    data = json.dumps(snapshot, ensure_ascii=False, default=str).replace("</", "<\\/")
    ui = S.ui_template
    if ui.exists():
        html = ui.read_text(encoding="utf-8")
        if UI_DATA_RE.search(html):
            tag = f'<script id="fomo1-data" type="application/json">{data}</script>'
            return UI_DATA_RE.sub(lambda m: tag, html, count=1)
    return TEMPLATE.replace("__DATA__", data)


def which_template() -> str:
    from config import S
    return f"React build ({S.ui_template})" if S.ui_template.exists() else "plain-HTML fallback (React build not found)"
