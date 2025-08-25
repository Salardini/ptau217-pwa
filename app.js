
// Online/offline badge
const offlineBadge=document.getElementById("offline");
function updateOnline(){ if(!navigator.onLine){ offlineBadge?.classList.add("show"); } else { offlineBadge?.classList.remove("show"); } }
addEventListener("online",updateOnline); addEventListener("offline",updateOnline); updateOnline();

// Utilities
const clamp=(x,lo,hi)=>Math.max(lo,Math.min(hi,x));
const toOdds=p=>p/(1-p), fromOdds=o=>o/(1+o);
function lerp(x,x0,y0,x1,y1){ if(x<=x0)return y0; if(x>=x1)return y1; const t=(x-x0)/(x1-x0); return y0+t*(y1-y0); }
function fmtPct(x){ if(!isFinite(x)) return "—"; const p=x*100; return p<0.1? p.toFixed(2)+"%": p.toFixed(1)+"%"; }

// Tunables
const APOE_OR={"unknown":1.0,"e3e3":1.0,"e2e2":0.6,"e2e3":0.6,"e2e4":2.6,"e3e4":3.5,"e4e4":12.0};
const PRIOR_ANCHORS={"CN":{a50:0.10,a90:0.44},"SCD":{a50:0.12,a90:0.43},"MCI":{a50:0.27,a90:0.71},"DEM":{a50:0.60,a90:0.85}};

// Library of modalities (defaults are illustrative; LR indeterminate ~1)
const TEST_LIBRARY = {
  lumipulse_ratio: {label:"Plasma pTau217/Aβ42 (Lumipulse tri-band; ref PET/CSF)", defaults:{pos:14.51, indet:0.75, neg:0.07}},
  ptau217_plasma: {label:"Plasma pTau217 (single marker; ref PET)",               defaults:{pos:5.9,   indet:1.0,  neg:0.21}},
  abeta4240_plasma:{label:"Plasma Aβ42/Aβ40 (ref PET)",                           defaults:{pos:4.0,   indet:1.0,  neg:0.25}},
  csf_ptau181_a42:{label:"CSF pTau181/Aβ42 (ref PET)",                             defaults:{pos:3.9,   indet:1.0,  neg:0.14}},
  amyloid_pet:    {label:"Amyloid PET (visual; ref autopsy)",                      defaults:{pos:7.0,   indet:1.0,  neg:0.12}},
  custom:         {label:"Custom (enter your own)",                                defaults:{pos:6.0,   indet:1.0,  neg:0.20}},
};

// Fill modality dropdowns
function fillMods(sel){
  sel.innerHTML="";
  Object.entries(TEST_LIBRARY).forEach(([k,v])=>{
    const o=document.createElement("option"); o.value=k; o.textContent=v.label; sel.appendChild(o);
  });
}
fillMods(document.getElementById("modA"));
fillMods(document.getElementById("modB"));

function setDefaults(which){
  const modSel = document.getElementById(which==="A"?"modA":"modB");
  const lib = TEST_LIBRARY[modSel.value].defaults;
  document.getElementById(`lr${which}_pos`).value = lib.pos;
  document.getElementById(`lr${which}_indet`).value = lib.indet;
  document.getElementById(`lr${which}_neg`).value = lib.neg;
}
document.getElementById("defaultsA").addEventListener("click",()=>setDefaults("A"));
document.getElementById("defaultsB").addEventListener("click",()=>setDefaults("B"));
document.getElementById("modA").addEventListener("change",()=>setDefaults("A"));
document.getElementById("modB").addEventListener("change",()=>setDefaults("B"));
setDefaults("A"); setDefaults("B");

// Toggle B panel
document.getElementById("useB").addEventListener("change",(e)=>{
  const on = e.target.value==="yes";
  document.getElementById("panelB").style.display = on ? "block" : "none";
  document.getElementById("comboBlock").style.display = on ? "block" : "none";
});

// Prior
function priorFromAgeStage(age,stage){ const a=PRIOR_ANCHORS[stage]||PRIOR_ANCHORS["MCI"]; return clamp(lerp(age,50,a.a50,90,a.a90),0.01,0.99); }
function applyAPOEonOdds(p,apoe){ const or=APOE_OR[apoe]??1.0; const o=toOdds(clamp(p,1e-6,1-1e-6)); return clamp(fromOdds(o*or),1e-6,1-1e-6); }
function updateAutoPrior(){
  const age=Number(document.getElementById("age").value||70);
  const stage=document.getElementById("stage").value;
  const apoe=document.getElementById("apoe").value;
  let p=priorFromAgeStage(age,stage); p=applyAPOEonOdds(p,apoe);
  const el = document.getElementById("auto_prior"); if(el) el.value=(Math.round(p*1000)/1000).toFixed(3);
  return p;
}
["age","stage","apoe"].forEach(id=>document.getElementById(id).addEventListener("input",updateAutoPrior));

// Helpers
function lrForCategory(cat,vals){ return cat==="pos"?vals.pos : (cat==="indet"?vals.indet : vals.neg); }
function interpretP(p){ if(p>=0.90) return ["high","High probability of Aβ positivity"]; if(p>=0.70) return ["likely","Likely Aβ positivity"]; if(p>0.30) return ["mid","Indeterminate range"]; if(p>0.10) return ["low","Likely Aβ negative"]; return ["low","Low probability"]; }
function setChip(elId, bucket, label){ const el=document.getElementById(elId); if(!el) return; el.className="chip " + bucket; el.textContent = label; }

// Diagnostic calculation + PPV/NPV
function computeDiagnostic(){
  const p_auto = updateAutoPrior();
  const prior_override = document.getElementById("prior_override").value;
  const prior0 = prior_override ? clamp(Number(prior_override), 1e-6, 1-1e-6) : p_auto;

  // Test A
  const catA = document.getElementById("catA").value;
  const lrA_pos = Number(document.getElementById("lrA_pos").value||1);
  const lrA_ind = Number(document.getElementById("lrA_indet").value||1);
  const lrA_neg = Number(document.getElementById("lrA_neg").value||1);
  const LR_A = lrForCategory(catA, {pos:lrA_pos, indet:lrA_ind, neg:lrA_neg});

  const showUncert = document.getElementById("uncert").checked;
  let ciA = null;
  if(showUncert){
    // crude generic CIs around defaults
    const modA = document.getElementById("modA").value;
    const lib = TEST_LIBRARY[modA].defaults;
    ciA = {pos:[lib.pos*0.65, lib.pos*1.55], indet:[0.8,1.25], neg:[lib.neg*0.5, lib.neg*1.5]}[catA];
  }

  const o0 = toOdds(prior0);
  const p1 = fromOdds(o0 * LR_A);
  const p1lo = ciA ? fromOdds(o0 * ciA[0]) : null;
  const p1hi = ciA ? fromOdds(o0 * ciA[1]) : null;

  const [b1,lab1] = interpretP(p1);
  document.getElementById("post_p1").textContent = ciA ? `Posterior P(A+) = ${fmtPct(p1)}  (≈ ${fmtPct(p1lo)} to ${fmtPct(p1hi)})` : `Posterior P(A+) = ${fmtPct(p1)}`;
  document.getElementById("post_details1").innerHTML = `Prior = ${fmtPct(prior0)} · LR<sub>A</sub> = ${LR_A.toFixed(2)} → Bayes on odds.`;

  // PPV/NPV at this prior (binary extremes)
  const ppvA = fromOdds(o0 * lrA_pos);
  const npvA = 1 - fromOdds(o0 * lrA_neg);
  document.getElementById("post_details1").innerHTML += `<br/><span class="muted">At prior ${fmtPct(prior0)} → PPV_A (if A+) = ${fmtPct(ppvA)} · NPV_A (if A−) = ${fmtPct(npvA)}</span>`;
  setChip("chip1", b1, lab1);

  // Test B (optional)
  const useB = document.getElementById("useB").value==="yes";
  document.getElementById("comboBlock").style.display = useB ? "block" : "none";
  if(useB){
    const catB = document.getElementById("catB").value;
    const lrB_pos = Number(document.getElementById("lrB_pos").value||1);
    const lrB_ind = Number(document.getElementById("lrB_indet").value||1);
    const lrB_neg = Number(document.getElementById("lrB_neg").value||1);
    const LR_B = lrForCategory(catB, {pos:lrB_pos, indet:lrB_ind, neg:lrB_neg});

    const o1 = toOdds(p1);
    const p2 = fromOdds(o1 * LR_B);
    const [b2,lab2] = interpretP(p2);
    document.getElementById("post_p2").textContent = `Posterior P(A+) = ${fmtPct(p2)}`;
    document.getElementById("post_details2").innerHTML = `Posterior after A (${fmtPct(p1)}) becomes prior for B · LR<sub>B</sub> = ${LR_B.toFixed(2)}.`;

    const ppvB = fromOdds(o1 * lrB_pos);
    const npvB = 1 - fromOdds(o1 * lrB_neg);
    document.getElementById("post_details2").innerHTML += `<br/><span class="muted">At prior ${fmtPct(p1)} (after A) → PPV_B (if B+) = ${fmtPct(ppvB)} · NPV_B (if B−) = ${fmtPct(npvB)}</span>`;

    setChip("chip2", b2, lab2);
    window.__POSTERIOR__ = p2;
  } else {
    document.getElementById("post_details2").innerHTML = "";
    window.__POSTERIOR__ = p1;
  }
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

  const chip = document.getElementById("risk_chip");
  chip.className = "chip " + (risk_mix>=0.40?"high":risk_mix>=0.20?"likely":risk_mix>=0.10?"mid":"low");
  chip.textContent = risk_mix>=0.40?"High projected risk":risk_mix>=0.20?"Moderate projected risk":risk_mix>=0.10?"Low–moderate projected risk":"Low projected risk";

  document.getElementById("prog_details").innerHTML =
    `Mixture model: P(t)=P(A+)×[1−(1−h_A+)^t] + (1−P(A+))×[1−(1−h_A−)^t].`;
}

// ---------------- Harmonize to Autopsy (bridge) ----------------
function petPPV(se, sp, prev){ return (se*prev) / (se*prev + (1-sp)*(1-prev)); }
function petNPV(se, sp, prev){ return (sp*(1-prev)) / ((1-se)*prev + sp*(1-prev)); }
// Convert LR+ and LR− (binary) into Se/Sp (assumes LR+=Se/(1-Sp), LR-=(1-Se)/Sp)
function seSpFromLR(LRp, LRn){
  const den = (LRn - LRp);
  if (Math.abs(den) < 1e-9) return {error:"Invalid LRs (den≈0)"};
  let sp = (1 - LRp) / den;
  let se = 1 - LRn * sp;
  return {se, sp};
}
// Bridge B vs PET → B vs autopsy
function bridgeToAutopsy_fromLR(LRp, LRn, seP, spP, prev){
  const m = seSpFromLR(LRp, LRn);
  if (m.error) return {error:m.error};
  const a = clamp(m.se, 0, 1), b = clamp(m.sp, 0, 1); // a=Se_{B|P}, b=Sp_{B|P}
  const u = petPPV(seP, spP, prev), v = petNPV(seP, spP, prev);
  const det = u + v - 1;
  if (det <= 0) return {error:"Invalid PET inputs at this prevalence (u+v-1 ≤ 0)"};
  const A = a - 1 + u, B = b - 1 + v;
  let se = (A*v + (1-u)*B) / det;
  let sp = (u*B + (1-v)*A) / det;
  let warn=false;
  if (se<0 || se>1 || sp<0 || sp>1){ warn=true; }
  se = clamp(se, 1e-3, 0.999); sp = clamp(sp, 1e-3, 0.999);
  const lrpos = se / (1 - sp);
  const lrneg = (1 - se) / sp;
  return {se, sp, lrpos, lrneg, ppvPET:u, npvPET:v, warn};
}

function doBridge(which){
  const seP = Number(document.getElementById("pet_se").value||0.92);
  const spP = Number(document.getElementById("pet_sp").value||0.90);
  const prev = Number(document.getElementById("pet_prev").value||0.5);
  const inpLRp = Number(document.getElementById(which+"_lrp").value||NaN);
  const inpLRn = Number(document.getElementById(which+"_lrn").value||NaN);
  const out = bridgeToAutopsy_fromLR(inpLRp, inpLRn, seP, spP, prev);
  const outEl = document.getElementById(which+"_out");
  if (out.error){ outEl.textContent = "Error: "+out.error; return; }
  outEl.innerHTML = `Autopsy-anchored: Se=${(out.se).toFixed(3)}, Sp=${(out.sp).toFixed(3)} · LR+=${out.lrpos.toFixed(2)}, LR−=${out.lrneg.toFixed(3)} `+(out.warn?" (inputs inconsistent; clamped)":"");
  // Fill corresponding test fields (indet ~ 1)
  if (which.startsWith("bridgeA")) {
    document.getElementById("lrA_pos").value = out.lrpos.toFixed(2);
    document.getElementById("lrA_neg").value = out.lrneg.toFixed(3);
    document.getElementById("lrA_indet").value = 1.0;
  } else {
    document.getElementById("lrB_pos").value = out.lrpos.toFixed(2);
    document.getElementById("lrB_neg").value = out.lrneg.toFixed(3);
    document.getElementById("lrB_indet").value = 1.0;
  }
}

document.getElementById("bridgeA").addEventListener("click",()=>doBridge("bridgeA"));
document.getElementById("bridgeB").addEventListener("click",()=>doBridge("bridgeB"));
document.getElementById("bridgeBoth").addEventListener("click",()=>{ doBridge("bridgeA"); doBridge("bridgeB"); });

// Wire up main actions
document.getElementById("calc_dx").addEventListener("click", computeDiagnostic);
["age","stage","apoe"].forEach(id => document.getElementById(id).addEventListener("input", updateAutoPrior));
document.getElementById("calc_prog").addEventListener("click", computePrognostic);
updateAutoPrior(); computeDiagnostic();
