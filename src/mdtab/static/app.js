const $=s=>document.querySelector(s);
const qs=new URLSearchParams(location.search);
let cur={file:null,dir:null,mtime:null}, root=null;
const enc=p=>encodeURIComponent(p);
const api=(u,p)=>fetch(`${u}?path=${enc(p)}`).then(r=>r.json());

async function loadTree(dir, ul, isRoot){
  const t=await api('/api/tree',dir); if(t.error) return;
  if(isRoot){root=t; $('#crumb').innerHTML=crumb(t.display||t.dir); $('#up').disabled=!t.parent;}
  ul.innerHTML='';
  for(const it of t.items){
    const li=document.createElement('li'); li.className=it.dir?'dir':(it.md?'md':'other');
    const row=document.createElement('div');
    row.innerHTML=`<span class="ic">${it.dir?'▸':(it.md?'▤':'·')}</span><span>${esc(it.name)}</span>`;
    li.appendChild(row);
    if(it.dir){ const sub=document.createElement('ul'); sub.hidden=true; li.appendChild(sub);
      row.onclick=async()=>{ if(sub.hidden){ await loadTree(it.path,sub,false); sub.hidden=false; row.firstChild.textContent='▾'; }
                             else { sub.hidden=true; row.firstChild.textContent='▸'; } }; }
    else { row.onclick=()=>openFile(it.path); row.dataset.path=it.path; }
    ul.appendChild(li);
  }
  mark();
}
function crumb(d){ const parts=d.split('/').filter(Boolean);
  return parts.map((p,i)=>i===parts.length-1?`<b>${esc(p)}</b>`:esc(p)).join(' / '); }
function mark(){ document.querySelectorAll('#tree div[data-path]').forEach(e=>e.classList.toggle('sel',e.dataset.path===cur.file)); }
async function openFile(p, push=true){
  const f=await api('/api/file',p); if(f.error){ $('#doc').innerHTML=`<p class="hint">Cannot open: ${esc(p)}</p>`; return; }
  cur={file:f.path,dir:f.dir,mtime:f.mtime}; document.title=f.name;
  $('#doc').innerHTML=f.html; $('#main').scrollTop=0; mark();
  if(push) history.replaceState(null,'',`/view?path=${enc(f.path)}`);
}
$('#up').onclick=()=>{ if(root?.parent) loadTree(root.parent,$('#tree'),true); };
$('#reveal').onclick=()=>{ if(cur.file) api('/api/reveal',cur.file); };
setInterval(async()=>{ if(!cur.file) return; const m=await api('/api/mtime',cur.file);
  if(m.mtime && cur.mtime && m.mtime>cur.mtime){ const y=$('#main').scrollTop; await openFile(cur.file,false); $('#main').scrollTop=y; } },2000);
// sidebar resize
let drag=false; $('#gutter').onmousedown=()=>drag=true; window.onmouseup=()=>drag=false;
window.onmousemove=e=>{ if(drag) $('#side').style.width=Math.max(160,e.clientX)+'px'; };
function esc(s){ return s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
(async()=>{ const p=qs.get('path'); if(!p){ await loadTree(root?.dir||'~',$('#tree'),true); return; }
  const f=await api('/api/file',p); const dir=f.dir||p; await loadTree(dir,$('#tree'),true); if(!f.error) openFile(p,false); })();
