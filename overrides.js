
(function(){
  // Colour thresholds
  window.COLOR_THRESHOLDS = { green:0.90, amber:0.70, grey:0.30, red:0.10 };

  // Override interpretP safely (keeps chip classes used by your CSS)
  window.interpretP = function(p){
    if(!isFinite(p)) return ["muted","—"];
    const T = window.COLOR_THRESHOLDS;
    if(p >= T.green) return ["good","High likelihood of PET positivity"];
    if(p >= T.amber) return ["warn","Likely PET positivity"];
    if(p <= T.red)   return ["bad","Low likelihood of PET positivity"];
    if(p <= T.grey)  return ["warn","Likely PET negative"];
    return ["muted","Indeterminate"];
  };

  // Map PET wording -> autopsy wording for Autopsy chips only
  function mapAutopsyLabel(label){
    if(/High.*PET positivity/i.test(label))   return "High probability of autopsy A+";
    if(/Likely PET positivity/i.test(label))  return "Likely autopsy A+";
    if(/Likely PET negative/i.test(label))    return "Likely autopsy A−";
    if(/Low.*PET positivity/i.test(label))    return "Low probability of autopsy A+";
    return label;
  }
  const _setChip = window.setChip;
  window.setChip = function(id, bucket, label){
    if(id && /^chip_aut/.test(id)) label = mapAutopsyLabel(label);
    return _setChip ? _setChip(id, bucket, label) : null;
  };

  // --- Triage helpers (no edits to your compute): read current PET numbers from DOM
  function getTriageCutoff(){
    const el = document.getElementById("triage_thresh");
    let v = el ? Number(el.value) : 0.80;
    if(!isFinite(v) || v<=0 || v>=1) v = 0.80;
    return v;
  }
  function ensurePill(id, detailsId){
    let pill = document.getElementById(id);
    const details = document.getElementById(detailsId);
    if(!pill && details){
      pill = document.createElement("span");
      pill.id = id; pill.className = "pill"; pill.style.marginLeft = "8px";
      details.appendChild(pill);
    }
    return pill;
  }
  function parsePctFrom(elId){
    const el = document.getElementById(elId); if(!el) return NaN;
    const m = (el.textContent||"").match(/([\d.]+)\s*%/);
    return m ? parseFloat(m[1])/100 : NaN;
  }
  function updateTriage(){
    const thr = getTriageCutoff();
    const p1 = parsePctFrom("post_p1");
    const pill1 = ensurePill("triage_flag1","post_details1");
    if(pill1 && isFinite(p1)){
      pill1.textContent = (p1>=thr) ? `Meets therapy triage (≥ ${Math.round(thr*100)}%)`
                                    : `Below triage (${Math.round(thr*100)}% cut-off)`;
    }
    const el2 = document.getElementById("post_p2");
    if(el2){
      const p2 = parsePctFrom("post_p2");
      const pill2 = ensurePill("triage_flag2","post_details2");
      if(pill2 && isFinite(p2)){
        pill2.textContent = (p2>=thr) ? `Meets therapy triage (≥ ${Math.round(thr*100)}%)`
                                      : `Below triage (${Math.round(thr*100)}% cut-off)`;
      }
    }
  }

  // Inject triage controls if missing (keeps this overlay self-contained)
  function ensureTriageControls(){
    if(document.getElementById("triage_controls")) return;
    const btn = document.getElementById("calc_dx"); if(!btn) return;
    const row = btn.closest(".row") || btn.parentElement;
    const div = document.createElement("div");
    div.className = "row small"; div.id = "triage_controls";
    div.style.gap = "10px"; div.style.marginTop = "6px";
    div.innerHTML = '<label class="small" for="triage_thresh" style="margin:0">Therapy triage cut-off (P(PET+))</label>'
      + '<input type="number" id="triage_thresh" value="0.80" min="0" max="1" step="0.01" style="width:110px">'
      + '<button class="btn secondary" id="triage_quick90" type="button" title="Set to 0.90">Quick: 0.90</button>';
    row.after(div);
  }

  function wire(){
    // Mutation observers to refresh triage when PET cards update
    ["post_p1","post_p2"].forEach(id=>{
      const el = document.getElementById(id); if(!el) return;
      new MutationObserver(()=>updateTriage()).observe(el, {childList:true,subtree:true,characterData:true});
    });
    const btn90 = document.getElementById("triage_quick90");
    if(btn90){
      btn90.addEventListener("click", ()=>{ const el = document.getElementById("triage_thresh"); if(el) el.value="0.90"; updateTriage(); });
    }
    ["triage_thresh"].forEach(id=>{
      const el = document.getElementById(id); if(el) el.addEventListener("input", updateTriage);
    });
    updateTriage();
  }

  window.addEventListener("load", ()=>{
    try{ ensureTriageControls(); }catch(e){}
    try{ wire(); }catch(e){}
  });
})();
