const $ = (id) => document.getElementById(id);

function fillExample(type){
  const examples={
    garbage:'Garbage has not been collected from our lane for several days. Waste is accumulating near the houses and there is a bad smell.',
    water:'Our area has had irregular drinking water supply since yesterday. Several houses are affected.',
    road:'There is a large pothole on the road near the main bus stop. It is difficult for two-wheelers to pass safely.',
    tree:'A large tree has fallen across the road after heavy rain and is blocking traffic. Vehicles cannot pass through the road.'
  };
  $('message').value=examples[type];
}

function previewImage(event){
  const file=event.target.files?.[0];
  const box=$('preview');
  if(!file){box.classList.add('hidden');box.innerHTML='';return}
  if(file.size>5*1024*1024){
    alert('Please choose an image under 5 MB.');
    event.target.value='';
    box.classList.add('hidden');
    return;
  }
  const url=URL.createObjectURL(file);
  box.classList.remove('hidden');
  box.innerHTML=`<img src="${url}" alt="Selected civic issue photo"><div><b>${esc(file.name)}</b><small>${(file.size/1024/1024).toFixed(2)} MB · ${esc(file.type)}</small></div><button class="remove-photo" onclick="clearImage()">Remove</button>`;
}

function clearImage(){
  $('image').value='';
  $('preview').classList.add('hidden');
  $('preview').innerHTML='';
}

async function analyze(){
  const btn=$('analyzeBtn'), msg=$('message').value.trim();
  if(!msg){alert('Please describe your issue first.');return}
  btn.disabled=true;btn.innerHTML='Analyzing…';
  $('output').innerHTML='<div class="empty"><div class="orb">◌</div><h2>Understanding your request…</h2><p>Extracting intent, service category and useful next steps. If a photo is attached, JanSetu is also checking visible civic evidence.</p></div>';

  const form=new FormData();
  form.append('message',msg);
  form.append('language',$('language').value);
  form.append('location',$('location').value.trim());
  const image=$('image').files?.[0];
  if(image) form.append('image',image);

  try{
    const r=await fetch('/api/analyze',{method:'POST',body:form});
    const d=await r.json();
    if(!r.ok) throw new Error(d.error||'Request failed');
    render(d);
  }catch(e){
    $('output').innerHTML='<div class="empty"><div class="orb">!</div><h2>Something went wrong</h2><p>'+esc(e.message)+'</p></div>'
  }finally{
    btn.disabled=false;btn.innerHTML='Analyze with JanSetu AI <span>→</span>'
  }
}

function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}

function render(d){
  const sourceLabel=d.source==='Gemini Vision'?'Gemini Vision':d.source;
  const photoBlock=d.photo_attached ? `<div class="photo-badge">📷 Photo evidence analyzed${d.photo_name?` · ${esc(d.photo_name)}`:''}</div>` : '';
  const observations=(d.visual_observations||[]).length
    ? `<div class="chips">${d.visual_observations.map(x=>`<span class="chip evidence-chip">${esc(x)}</span>`).join('')}</div>`
    : '<span class="chip">No visual observations</span>';

  $('output').innerHTML=`<div class="result"><div class="section-head"><div><span class="number">02</span><h2>AI action plan</h2></div><span class="tag">${esc(sourceLabel)}</span></div>
  ${photoBlock}
  <div class="metrics"><div class="metric"><small>Intent</small><b>${esc(d.intent)}</b></div><div class="metric"><small>Suggested department</small><b>${esc(d.department)}</b></div><div class="metric"><small>Category</small><b>${esc(d.category)}</b></div><div class="metric"><small>Urgency</small><b class="urgency">${esc(d.urgency)}</b></div></div>
  <div class="block"><h3>Plain-language summary</h3><div class="draft">${esc(d.summary)}</div></div>
  <div class="block"><h3>Visual evidence</h3>${observations}<p class="evidence-note">${esc(d.evidence_note)}</p></div>
  <div class="block"><h3>Information still useful</h3><div class="chips">${(d.missing_information||[]).length?(d.missing_information.map(x=>`<span class="chip">${esc(x)}</span>`).join('')):'<span class="chip">No major missing information detected</span>'}</div></div>
  <div class="block"><h3>Suggested next steps</h3><div class="chips">${(d.suggested_actions||[]).map(x=>`<span class="chip">${esc(x)}</span>`).join('')}</div></div>
  <div class="block"><h3>Editable request draft</h3><div class="draft" id="draft">${esc(d.complaint_draft)}</div><div class="actions"><button class="secondary" onclick="copyDraft()">Copy draft</button><button class="secondary" onclick="simulateTrack('${esc(d.reference_id)}')">Simulate tracking</button></div></div>
  <div class="status" id="status"><b>Reference ${esc(d.reference_id)}</b><br><span>${esc(d.disclaimer)}</span></div></div>`;
}

function copyDraft(){
  navigator.clipboard?.writeText($('draft').innerText);
  alert('Draft copied.');
}

function simulateTrack(id){
  $('status').innerHTML='<b>'+esc(id)+'</b><br>Prototype lifecycle: <strong>Draft → Submitted (simulated) → Under Review → Resolved</strong><br><span>This status is simulated for the hackathon demo.</span>';
}
