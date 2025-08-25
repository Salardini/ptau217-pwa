
// Online/offline badge (for localhost it will usually be 'online')
const offlineBadge=document.getElementById("offline");
function updateOnline(){ if(!navigator.onLine){ offlineBadge?.classList.add("show"); } else { offlineBadge?.classList.remove("show"); } }
window.addEventListener("online",updateOnline); window.addEventListener("offline",updateOnline); updateOnline();

// Utilities
const clamp=(x,lo,hi)=>Math.max(lo,Math.min(hi,x));
const toOdds=p=>p/(1-p), fromOdds=o=>o/(1+o);
function lerp(x,x0,y0,x1,y1){ if(x<=x0)return y0; if(x>=x1)return y1; const t=(x-x0)/(x1-x0); return y0+t*(y1-y0); }

// Tunables
const APOE_OR={"unknown":1.0,"e3e3":1.0,"e2e2":0.6,"e2e3":0.6,"e2e4":2.6,"e3e4":3.5,"e4e4":12.0};
const PRIOR_ANCHORS={"CN":{a50:0.10,a90:0.44},"SCD":{a50:0.12,a90:0.43},"MCI":{a50:0.27,a90:0.71},"DEM":{a50:0.60,a90:0.85}};

// Helpers
function priorFromAgeStage(age,stage){ const a=PRIOR_ANCHORS[stage]||PRIOR_ANCHORS["MCI"]; return clamp(lerp(age,50,a.a50,90,a.a90),0.01,0.99); }
function applyAPOEonOdds(p,apoe){ const or=APOE_OR[apoe]??1.0; const o=toOdds(clamp(p,1e-6,1-1e-6)); return clamp(fromOdds(o*or),1e-6,1-1e-6); }
function lrForCategory(cat,lp,li,ln){ return cat==="pos"?lp:(cat==="indet"?li:ln); }
function computePosterior(prior_p,lr,lo=null,hi=null){ const o0=toOdds(clamp(prior_p,1e-9,1-1e-9)); const p=fromOdds(o0*lr); if(lo!=null&&hi!=null){ return {p,plo:fromOdds(o0*lo),phi:fromOdds(o0*hi)}; } return {p}; }
function fmtPct(x){ if(!isFinite(x)) return "—"; const p=x*100; return p<0.1? p.toFixed(2)+"%": p.toFixed(1)+"%"; }

// Chips
function setChip(elId, bucket, label){
  const el=document.getElementById(elId); if(!el) return;
  el.className="chip " + bucket; el.textContent = label;
}
function interpretPosterior(p){
  if(p>=0.90) return ["high","High probability of Aβ positivity"];
  if(p>=0.70) return ["likely","Likely Aβ positivity"];
  if(p>0.30)  return ["mid","Indeterminate range"];
  if(p>0.10)  return ["low","Likely Aβ negative"];
  return ["low","Low probability of Aβ positivity"];
}
function interpretRisk(r){
  if(r>=0.40) return ["high","High projected conversion risk"];
  if(r>=0.20) return ["likely","Moderate projected risk"];
  if(r>=0.10) return ["mid","Low–moderate projected risk"];
  return ["low","Low projected risk"];
}

// Auto prior
function updateAutoPrior(){
  const age=Number(document.getElementById("age").value||70);
  const stage=document.getElementById("stage").value;
  const apoe=document.getElementById("apoe").value;
  let p=priorFromAgeStage(age,stage); p=applyAPOEonOdds(p,apoe);
  const el = document.getElementById("auto_prior");
  if(el) el.value=(Math.round(p*1000)/1000).toFixed(3);
  return p;
}

// Diagnostic
function computeDiagnostic(){
  const p_auto = updateAutoPrior();
  const prior_override = document.getElementById("prior_override").value;
  const prior = prior_override ? clamp(Number(prior_override), 1e-6, 1-1e-6) : p_auto;

  const lr_pos = Number(document.getElementById("lr_pos").value);
  const lr_ind = Number(document.getElementById("lr_indet").value);
  const lr_neg = Number(document.getElementById("lr_neg").value);
  const cat = document.getElementById("testcat").value;
  const showUncert = document.getElementById("uncert").checked;

  const LR = lrForCategory(cat, lr_pos, lr_ind, lr_neg);
  let res;
  if (showUncert){
    const CI = {pos:[6.90,16.79], indet:[0.67,1.36], neg:[0.01,0.06]}[cat];
    res = computePosterior(prior, LR, CI[0], CI[1]);
  } else {
    res = computePosterior(prior, LR);
  }

  const out = document.getElementById("post_p");
  out.textContent = res.plo!==undefined
    ? `Posterior P(A+) = ${fmtPct(res.p)}  (≈ ${fmtPct(res.plo)} to ${fmtPct(res.phi)} via LR CI)`
    : `Posterior P(A+) = ${fmtPct(res.p)}`;

  const [bucket, label] = interpretPosterior(res.p);
  setChip("post_chip", bucket, label);

  document.getElementById("post_details").innerHTML =
    `Prior P(A+) = ${fmtPct(prior)} · LR = ${LR.toFixed(2)} → Bayes on odds. ` +
    (prior_override ? `<span class="muted">Using prior override.</span>` : `<span class="muted">Auto prior.</span>`);

  window.__POSTERIOR__ = res.p;
}

// Prognostic
function computePrognostic(){
  const usePosterior = document.getElementById("use_posterior").value === "yes";
  const pa = usePosterior ? (window.__POSTERIOR__ ?? 0.5) : Number(document.getElementById("manual_pa").value || 0.5);
  const stage = document.getElementById("stage_prog").value;
  const t = Number(document.getElementById("t_years").value || 3);

  const h_cn_pos = Number(document.getElementById("h_cn_pos").value);
  const h_cn_neg = Number(document.getElementById("h_cn_neg").value);
  const h_mci_pos = Number(document.getElementById("h_mci_pos").value);
  const h_mci_neg = Number(document.getElementById("h_mci_neg").value);

  const h_pos = stage === "CN" ? h_cn_pos : h_mci_pos;
  const h_neg = stage === "CN" ? h_cn_neg : h_mci_neg;

  const risk_pos = 1 - Math.pow(1 - h_pos, t);
  const risk_neg = 1 - Math.pow(1 - h_neg, t);
  const risk_mix = clamp(pa * risk_pos + (1 - pa) * risk_neg, 0, 0.999);

  document.getElementById("risk_out").textContent =
    `Projected ${t}-year conversion risk = ${fmtPct(risk_mix)}  (A+: ${fmtPct(risk_pos)}, A−: ${fmtPct(risk_neg)}, P(A+)=${fmtPct(pa)})`;

  const [bucket, label] = interpretRisk(risk_mix);
  setChip("risk_chip", bucket, label);

  document.getElementById("prog_details").innerHTML =
    `Mixture model: P(t)=P(A+)×[1−(1−h_A+)^t] + (1−P(A+))×[1−(1−h_A−)^t].`;
}

// Wiring
["age","stage","apoe"].forEach(id => document.getElementById(id).addEventListener("input", updateAutoPrior));
document.getElementById("calc_dx").addEventListener("click", computeDiagnostic);
document.getElementById("calc_prog").addEventListener("click", computePrognostic);
updateAutoPrior(); computeDiagnostic();
