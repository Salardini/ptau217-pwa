
// Online/offline badge
const offlineBadge=document.getElementById("offline");
function updateOnline(){ if(!navigator.onLine){ offlineBadge?.classList.add("show"); } else { offlineBadge?.classList.remove("show"); } }
addEventListener("online",updateOnline); addEventListener("offline",updateOnline); updateOnline();

// Utilities
const clamp=(x,lo,hi)=>Math.max(lo,Math.min(hi,x));
const toOdds=p=>p/(1-p), fromOdds=o=>o/(1+o);
// Colour thresholds used for chip buckets (both PET and autopsy layers)
const COLOR_THRESHOLDS = { green:0.90, amber:0.70, grey:0.30, red:0.10 };
function lerp(x,x0,y0,x1,y1){ if(x<=x0)return y0; if(x>=x1)return y1; const t=(x-x0)/(x1-x0); return y0+t*(y1-y0); }
function fmtPct(x){ if(!isFinite(x)) return "—"; const p=x*100; return p<0.1? p.toFixed(2)+"%": p.toFixed(1)+"%"; }

// Tunables
const APOE_OR={"unknown":1.0,"e3e3":1.0,"e2e2":0.6,"e2e3":0.6,"e2e4":2.6,"e3e4":3.5,"e4e4":12.0};
const PRIOR_ANCHORS={"CN":{a50:0.10,a90:0.44},"SCD":{a50:0.12,a90:0.43},"MCI":{a50:0.27,a90:0.71},"DEM":{a50:0.60,a90:0.85}};

// Library (illustrative defaults)



const TEST_LIBRARY = {
  // Imaging (ref autopsy)
  "amyloid_pet": {
    label: "Amyloid PET (visual; ref autopsy)",
    ref: "autopsy",
    se: 0.92, sp: 0.90,
    // LR+ = Se/(1-Sp) = 0.92/0.10 = 9.20; LR- = (1-Se)/Sp = 0.08/0.90 = 0.089
    defaults: { pos: 9.20, indet: 1.00, neg: 0.089 }
  },

  // CSF (ref PET)
  "csf_abeta42_40_lumipulse": {
    label: "CSF Aβ42/40 (Lumipulse; ref PET)",
    ref: "PET",
    se: 0.92, sp: 0.93,
    // LR+ = 0.92/0.07 = 13.14; LR- = 0.08/0.93 = 0.086
    defaults: { pos: 13.14, indet: 1.00, neg: 0.086 }
  },
  "csf_ptau181_abeta42_elecsys": {
    label: "CSF p-tau181/Aβ42 (Elecsys; ref PET)",
    ref: "PET",
    se: 0.91, sp: 0.89,
    // LR+ = 0.91/0.11 = 8.27; LR- = 0.09/0.89 = 0.101
    defaults: { pos: 8.27, indet: 1.00, neg: 0.101 }
  },

  // Plasma (ref PET)
  "plasma_abeta42_40_generic": {
    label: "Plasma Aβ42/40 (generic; ref PET)",
    ref: "PET",
    se: 0.85, sp: 0.85,
    // LR+ = 0.85/0.15 = 5.67; LR- = 0.15/0.85 = 0.176
    defaults: { pos: 5.67, indet: 1.00, neg: 0.176 }
  },
  "plasma_ptau217_generic": {
    label: "Plasma p-tau217 (generic; ref PET)",
    ref: "PET",
    se: 0.92, sp: 0.94,
    // illustrative strong defaults
    defaults: { pos: 15.33, indet: 1.00, neg: 0.085 }
  },
  "plasma_ptau217_abeta42_lumipulse": {
    label: "Plasma p-tau217/Aβ42 (Lumipulse; mixed PET/CSF ref)",
    ref: "mixed",
    se: 0.96, sp: 0.92,
    defaults: { pos: 12.00, indet: 1.00, neg: 0.043 }
  }
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

// Toggle B panel (mirror for autopsy blocks too)
document.getElementById("useB").addEventListener("change",(e)=>{
  const on = e.target.value==="yes";
  document.getElementById("panelB").style.display = on ? "block" : "none";
  document.getElementById("comboBlock").style.display = on ? "block" : "none";
  document.getElementById("comboAutBlock").style.display = on ? "block" : "none";
});

// Prior helpers
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

// As-entered Diagnostic calc + PPV/NPV
function lrForCategory(cat,vals){ return cat==="pos"?vals.pos : (cat==="indet"?vals.indet : vals.neg); }

// Autopsy-specific chip labels
function labelAutopsy(p){
  // label text only (chip color still driven by bucket from interpretP)
  if (!isFinite(p)) return "—";
  if (p >= 0.90) return "High probability of autopsy A+";
  if (p >= 0.70) return "Likely autopsy A+";
  if (p <= 0.10) return "Low probability of autopsy A+";
  if (p <= 0.30) return "Likely autopsy A−";
  return "Indeterminate on autopsy scale";
}


function interpretP(p){
  if(!isFinite(p)) return ["muted","—"];
  const T = COLOR_THRESHOLDS;
  if(p >= T.green) return ["good","High likelihood of PET positivity"];
  if(p >= T.amber) return ["warn","Likely PET positivity"];
  if(p <= T.red)   return ["bad","Low likelihood of PET positivity"];
  if(p <= T.grey)  return ["warn","Likely PET negative"];
  return ["muted","Indeterminate"];
}


function setChip(elId, bucket, label){ const el=document.getElementById(elId); if(!el) return; el.className="chip " + bucket; el.textContent = label; }


function computeDiagnostic(){
  // Clinical prior (autopsy prevalence proxy used for PET PPV/NPV too)
  const p_auto = updateAutoPrior();
  const prior_override = document.getElementById("prior_override").value;
  const prior0 = prior_override ? clamp(Number(prior_override), 1e-6, 1-1e-6) : p_auto;

  // PET Se/Sp used for PET-layer and autopsy layer
  const seP = Number(document.getElementById("pet_se_dx")?.value || 0.92);
  const spP = Number(document.getElementById("pet_sp_dx")?.value || 0.90);

  // Test A
  const modA   = document.getElementById("modA").value;
  const catA   = document.getElementById("catA").value;
  const lrApos = Number(document.getElementById("lrA_pos").value||1);
  const lrAind = Number(document.getElementById("lrA_indet").value||1);
  const lrAneg = Number(document.getElementById("lrA_neg").value||1);
  const LR_A   = (catA==="pos")?lrApos : (catA==="neg")?lrAneg : 1.0;

  // PET prior at this clinical prevalence: P(PET+)
  const pP0 = seP*prior0 + (1-spP)*(1-prior0);

  // PET layer after Test A
  let qA;
  if (modA === "amyloid_pet") {
    qA = (catA === "pos") ? 1.0 : (catA === "neg") ? 0.0 : pP0; // PET observed → 100%/0%
  } else {
    const oP0 = toOdds(pP0);
    qA = fromOdds(oP0 * LR_A); // blood/CSF vs PET
  }

  // TOP CARD: PET layer
  document.getElementById("post_p1").textContent = `P(PET+) = ${fmtPct(qA)}`;
  document.getElementById("post_details1").innerHTML =
    (modA==="amyloid_pet")
      ? `PET observed → P(PET+)=${fmtPct(qA)} by definition.`
      : `Updated PET layer: prior P(PET+)=${fmtPct(pP0)}, LR_A=${LR_A.toFixed(2)} → P(PET+|A)=${fmtPct(qA)}.`;
  const [b1,lab1] = interpretP(qA); setChip("chip1", b1, lab1);

  // Optional Test B
  const useB = document.getElementById("useB").value==="yes";
  document.getElementById("comboBlock").style.display   = useB ? "block" : "none";
  document.getElementById("comboAutBlock").style.display= useB ? "block" : "none";

  let qAB = qA;
  if (useB){
    const modB   = document.getElementById("modB").value;
    const catB   = document.getElementById("catB").value;
    const lrBpos = Number(document.getElementById("lrB_pos").value||1);
    const lrBind = Number(document.getElementById("lrB_indet").value||1);
    const lrBneg = Number(document.getElementById("lrB_neg").value||1);
    const LR_B   = (catB==="pos")?lrBpos : (catB==="neg")?lrBneg : 1.0;

    if (modB === "amyloid_pet") {
      qAB = (catB === "pos") ? 1.0 : (catB === "neg") ? 0.0 : qA; // PET observed
    } else {
      const oQ = toOdds(qA);
      qAB = fromOdds(oQ * LR_B); // sequential PET-layer update
    }

    document.getElementById("post_p2").textContent = `P(PET+) = ${fmtPct(qAB)}`;
    document.getElementById("post_details2").innerHTML =
      (modB==="amyloid_pet")
        ? `Second test PET observed → P(PET+)=${fmtPct(qAB)} by definition.`
        : `Updated PET layer after B: prior P(PET+)=${fmtPct(qA)}, LR_B=${LR_B.toFixed(2)} → P(PET+|A,B)=${fmtPct(qAB)}.`;
    const [b2,lab2] = interpretP(qAB); setChip("chip2", b2, lab2);
  } else {
    document.getElementById("post_details2").innerHTML = "";
    showTriage("triage_flag2", qAB);
  }

  // Keep PET layer for reference
  window.__POSTERIOR__ = qAB;

  // Compute the autopsy layer (PPV/1−NPV when PET observed; mixture otherwise)
  computeAutopsyPosteriors(prior0, {catA, lrA_pos:lrApos, lrA_ind:lrAind, lrA_neg:lrAneg}, useB);
}



// Prognostic (prefer autopsy posterior if available)
function computePrognostic(){
  const preferAutopsy = document.getElementById("prefer_autopsy").value === "yes";
  const usePosterior = document.getElementById("use_posterior").value === "yes";
  let pa = 0.5;
  if(usePosterior){
    pa = (preferAutopsy && typeof window.__POSTERIOR_AUTOPSY__ === "number")
       ? window.__POSTERIOR_AUTOPSY__
       : (typeof window.__POSTERIOR__ === "number" ? window.__POSTERIOR__ : 0.5);
  } else {
    pa = Number(document.getElementById("manual_pa").value || 0.5);
  }

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

/* ---------- Autopsy harmonization core (MIXTURE method; bounded) ---------- */
// PET PPV/NPV at given prevalence (derived from PET Se/Sp vs autopsy and clinical prevalence)
function petPPV(se, sp, prev){ return (se*prev) / (se*prev + (1-sp)*(1-prev)); }
function petNPV(se, sp, prev){ return (sp*(1-prev)) / ((1-se)*prev + sp*(1-prev)); }

// Clinical PET prior at autopsy prevalence
function priorPETfromD(pD, seP, spP){ return seP*pD + (1-spP)*(1-pD); }

// Update PET probability with a blood LR (blood is referenced to PET)
function posteriorPETprobGivenB(pP, LR){ const o = toOdds(pP); return fromOdds(o * LR); }

// Autopsy posterior given ONE blood test (A) using the PET-mixture identity
// Inputs: priorD = clinical prior for autopsy; seP,spP = PET vs autopsy; LRpos/LRneg = blood vs PET; cat ∈ {"pos","indet","neg"}
function autopsyPosteriorFromB(priorD, seP, spP, LRpos, LRneg, cat){
  const LR = cat==="pos" ? LRpos : (cat==="neg" ? LRneg : 1.0);

  // 1) PET prior at the autopsy prevalence
  const pP = priorPETfromD(priorD, seP, spP);

  // 2) Blood→PET: q = P(PET+ | Blood)
  const q = posteriorPETprobGivenB(pP, LR);

  // 3) PET→Autopsy mixture (bounded by [1−NPV, PPV])
  const ppv = petPPV(seP, spP, priorD);
  const npv = petNPV(seP, spP, priorD);
  const lo = 1 - npv, hi = ppv;
  const p  = Math.max(lo, Math.min(hi, q*ppv + (1-q)*lo));

  return { p, q, ppv, npv, envelope:[lo,hi], LR_used:LR };
}

// TWO blood tests A→B: update PET odds sequentially, then do the same PET mixture once
// A and B are objects like: { LRpos, LRneg, cat }
function autopsyPosteriorFromAthenB(priorD, seP, spP, A, B){
  const LR_A = A.cat==="pos" ? A.LRpos : (A.cat==="neg" ? A.LRneg : 1.0);
  const LR_B = B.cat==="pos" ? B.LRpos : (B.cat==="neg" ? B.LRneg : 1.0);

  const pP0 = priorPETfromD(priorD, seP, spP);
  const q1  = posteriorPETprobGivenB(pP0, LR_A);    // P(P+ | A)
  const q2  = posteriorPETprobGivenB(q1,  LR_B);    // P(P+ | A,B)

  const ppv = petPPV(seP, spP, priorD);
  const npv = petNPV(seP, spP, priorD);
  const lo = 1 - npv, hi = ppv;
  const p  = Math.max(lo, Math.min(hi, q2*ppv + (1-q2)*lo));

  return { p, q2, ppv, npv, envelope:[lo,hi] };
}

// Replace the old autopsy computation used on the Diagnostic page

function computeAutopsyPosteriors(prior0, Avals, useB){
  // PET Se/Sp and derived PPV/NPV at this prior
  const seP = Number(document.getElementById("pet_se_dx")?.value || 0.92);
  const spP = Number(document.getElementById("pet_sp_dx")?.value || 0.90);
  const ppv = (seP*prior0) / (seP*prior0 + (1-spP)*(1-prior0));
  const npv = (spP*(1-prior0)) / ((1-seP)*prior0 + spP*(1-prior0));
  const lo  = 1 - npv, hi = ppv;

  const modA = document.getElementById("modA").value;
  const catA = Avals.catA;

  function renderA(p,msg){
    document.getElementById("post_aut_p1").textContent = `Posterior P(A+) = ${fmtPct(p)}`;
    document.getElementById("post_aut_details1").innerHTML = msg;
    setAutopsyChip("chip_aut1", p);
    window.__POSTERIOR_AUTOPSY__ = p;
  }
  function renderAB(p,msg){
    document.getElementById("post_aut_p2").textContent = `Posterior P(A+) = ${fmtPct(p)}`;
    document.getElementById("post_aut_details2").innerHTML = msg;
    setAutopsyChip("chip_aut2", p);
    window.__POSTERIOR_AUTOPSY__ = p;
  }

  // If A is PET, collapse directly to PPV / (1−NPV)
  if (modA === "amyloid_pet") {
    const pA = (catA==="pos") ? hi : (catA==="neg") ? lo : prior0;
    renderA(pA, `PET observed. By definition: PET+ → PPV=${fmtPct(hi)}, PET− → 1−NPV=${fmtPct(lo)} at prior ${fmtPct(prior0)}.`);
    if (useB) {
      // Once PET known, PET-referenced tests cannot change the autopsy posterior
      renderAB(pA, `PET already observed; additional PET-referenced tests do not change the autopsy posterior.`);
    } else {
      document.getElementById("post_aut_details2").innerHTML = "";
    }
    return;
  }

  // Otherwise A is PET-referenced → use PET mixture to autopsy
  // Step 1: PET prior at this prior0
  const pP0 = seP*prior0 + (1-spP)*(1-prior0);
  // Step 2: P(PET+ | A)
  const LR_A = (catA==="pos") ? Avals.lrA_pos : (catA==="neg") ? Avals.lrA_neg : 1.0;
  const qA = fromOdds(toOdds(pP0) * LR_A);
  // Step 3: mixture bounded to [1−NPV, PPV]
  const pA_auto = Math.max(lo, Math.min(hi, qA*hi + (1-qA)*lo));
  renderA(pA_auto, `Mixture: P(PET+|A)×PPV + (1−P(PET+|A))×(1−NPV). Here P(PET+|A)=${fmtPct(qA)}, PPV=${fmtPct(hi)}, NPV=${fmtPct(npv)}.`);

  if (useB){
    const modB = document.getElementById("modB").value;
    const catB = document.getElementById("catB").value;
    if (modB === "amyloid_pet") {
      const pAB = (catB==="pos") ? hi : (catB==="neg") ? lo : pA_auto;
      renderAB(pAB, `Second test is PET → autopsy posterior collapses to PET: PET+ → PPV=${fmtPct(hi)}, PET− → 1−NPV=${fmtPct(lo)}.`);
    } else {
      const lrB_pos = Number(document.getElementById("lrB_pos").value||1);
      const lrB_neg = Number(document.getElementById("lrB_neg").value||1);
      const LR_B = (catB==="pos")?lrB_pos : (catB==="neg")?lrB_neg : 1.0;
      const qAB = fromOdds(toOdds(qA) * LR_B);
      const pAB_auto = Math.max(lo, Math.min(hi, qAB*hi + (1-qAB)*lo));
      renderAB(pAB_auto, `After A→B: mixture bounded to [${fmtPct(lo)}, ${fmtPct(hi)}] at prior ${fmtPct(prior0)}.`);
    }
  } else {
    document.getElementById("post_aut_details2").innerHTML = "";
  }
}



/* (Legacy helpers retained; Harmonize tab removed) */


// Bridge tab utilities (optional)
function doBridge(which){
  const seP = Number(document.getElementById("pet_se").value||0.92);
  const spP = Number(document.getElementById("pet_sp").value||0.90);
  const prev = Number(document.getElementById("pet_prev").value||0.5);
  const inpLRp = Number(document.getElementById(which+"_lrp").value||NaN);
  const inpLRn = Number(document.getElementById(which+"_lrn").value||NaN);
  const out = bridgeToAutopsy_fromLR(inpLRp, inpLRn, seP, spP, prev);
  const outEl = document.getElementById(which+"_out");
  if (out.error){ outEl.textContent = "Error: "+out.error; return; }
  outEl.innerHTML = `Autopsy-anchored: Se=${(out.se).toFixed(3)}, Sp=${(out.sp).toFixed(3)} · LR+=${out.lrpos.toFixed(2)}, LR−=${out.lrneg.toFixed(3)} `+(out.warn?" (clamped)":"");
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

// Wire up
document.getElementById("calc_dx").addEventListener("click", computeDiagnostic);
["age","stage","apoe"].forEach(id => document.getElementById(id).addEventListener("input", updateAutoPrior));
document.getElementById("calc_prog").addEventListener("click", computePrognostic);


updateAutoPrior(); computeDiagnostic();

// Force cache update check
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then(function(registrations) {
    for(let registration of registrations) {
      registration.update();
    }
  });
}

// Add version check for debugging
console.log('Bayesian Amyloid Helper v213 loaded');

// Mode toggle functionality
document.getElementById("advancedMode").addEventListener("change", function(e) {
  if (e.target.checked) {
    document.body.classList.add("advanced-mode");
    localStorage.setItem("advancedMode", "true");
  } else {
    document.body.classList.remove("advanced-mode");
    localStorage.setItem("advancedMode", "false");
  }
});

// Restore mode preference
if (localStorage.getItem("advancedMode") === "true") {
  document.getElementById("advancedMode").checked = true;
  document.body.classList.add("advanced-mode");
}

// Enhanced result display with plain language
function generatePlainLanguage(probability, isAutopsy = false) {
  if (!isFinite(probability)) return "";
  
  const percent = Math.round(probability * 100);
  const substrate = isAutopsy ? "autopsy-confirmed amyloid pathology" : "PET-positive amyloid";
  
  if (probability >= 0.90) {
    return `There is a very high probability (${percent}%) that this patient has ${substrate}. Consider proceeding with amyloid-targeted interventions if clinically appropriate.`;
  } else if (probability >= 0.70) {
    return `There is a high probability (${percent}%) that this patient has ${substrate}. Additional clinical correlation may be helpful.`;
  } else if (probability >= 0.30) {
    return `The probability of ${substrate} is intermediate (${percent}%). Consider additional testing or clinical follow-up.`;
  } else if (probability >= 0.10) {
    return `There is a low probability (${percent}%) that this patient has ${substrate}. Amyloid pathology is unlikely but not ruled out.`;
  } else {
    return `There is a very low probability (${percent}%) that this patient has ${substrate}. Amyloid pathology is very unlikely.`;
  }
}

// Enhanced setChip function with plain language
const originalSetChip = window.setChip;
window.setChip = function(elId, bucket, label) {
  originalSetChip(elId, bucket, label);
  
  // Add plain language interpretation
  const chipNum = elId.match(/\d+/)?.[0] || "";
  const isAutopsy = elId.includes("aut");
  const plainLangId = isAutopsy ? `plain_language_aut${chipNum}` : `plain_language${chipNum}`;
  const plainLangEl = document.getElementById(plainLangId);
  
  if (plainLangEl) {
    const probability = isAutopsy ? window.__POSTERIOR_AUTOPSY__ : window.__POSTERIOR__;
    if (typeof probability === "number") {
      plainLangEl.textContent = generatePlainLanguage(probability, isAutopsy);
    }
  }
};

// PDF Export functionality
function generatePDF() {
  const results = {
    age: document.getElementById("age").value,
    stage: document.getElementById("stage").value,
    apoe: document.getElementById("apoe").value,
    testA: document.getElementById("modA").options[document.getElementById("modA").selectedIndex].text,
    catA: document.getElementById("catA").value,
    testB: document.getElementById("useB").value === "yes" ? document.getElementById("modB").options[document.getElementById("modB").selectedIndex].text : null,
    catB: document.getElementById("useB").value === "yes" ? document.getElementById("catB").value : null,
    petPosterior: window.__POSTERIOR__,
    autopsyPosterior: window.__POSTERIOR_AUTOPSY__,
    timestamp: new Date().toISOString()
  };
  
  // Create PDF content
  const content = `
BAYESIAN AMYLOID HELPER - RESULTS REPORT
Generated: ${new Date().toLocaleString()}

PATIENT CONTEXT:
Age: ${results.age} years
Cognitive Stage: ${results.stage}
APOE Genotype: ${results.apoe || 'Unknown'}

TEST RESULTS:
Primary Test: ${results.testA} - ${results.catA}
${results.testB ? `Secondary Test: ${results.testB} - ${results.catB}` : 'No secondary test'}

PROBABILITY ESTIMATES:
PET-Referenced Posterior: ${results.petPosterior ? (results.petPosterior * 100).toFixed(1) + '%' : 'Not calculated'}
Autopsy-Anchored Posterior: ${results.autopsyPosterior ? (results.autopsyPosterior * 100).toFixed(1) + '%' : 'Not calculated'}

CLINICAL INTERPRETATION:
${results.autopsyPosterior ? generatePlainLanguage(results.autopsyPosterior, true) : generatePlainLanguage(results.petPosterior, false)}

DISCLAIMER:
This tool is for educational purposes only. Results should not be used for clinical decision-making without proper medical supervision and interpretation.
  `.trim();
  
  // Create downloadable text file (simple PDF alternative)
  const blob = new Blob([content], { type: 'text/plain' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `amyloid-calculation-${new Date().toISOString().slice(0,10)}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

document.getElementById("export_pdf").addEventListener("click", generatePDF);

// Show action buttons after calculation
const originalComputeDiagnostic = computeDiagnostic;
window.computeDiagnostic = function() {
  originalComputeDiagnostic();
  document.getElementById("export_pdf").style.display = "inline-block";
  document.getElementById("save_case").style.display = "inline-block";
  document.getElementById("what_if").style.display = "inline-block";
  
  // Show smart suggestions and risk visualization
  generateSmartSuggestions();
  updateRiskVisualization();
};

// Phase 2: Guided Wizard System
const wizardSteps = [
  {
    title: "Welcome to Bayesian Amyloid Helper",
    text: "This tool calculates the probability of amyloid pathology using Bayesian statistics. We'll guide you through a typical calculation step by step.",
    target: null,
    action: null
  },
  {
    title: "Step 1: Clinical Context",
    text: "First, let's set up the patient's clinical context. Age and cognitive stage are the most important factors for determining baseline risk. Click here to enter the patient's age.",
    target: "#age",
    action: () => {
      document.getElementById("age").value = "73";
      updateAutoPrior();
    }
  },
  {
    title: "Step 2: Cognitive Stage", 
    text: "Now select the patient's cognitive stage. This affects the baseline probability of amyloid pathology.",
    target: "#stage",
    action: () => {
      document.getElementById("stage").value = "MCI";
      updateAutoPrior();
    }
  },
  {
    title: "Step 3: Select Test",
    text: "Choose the biomarker test that was performed. Each test has different performance characteristics for detecting amyloid pathology.",
    target: "#modA",
    action: () => {
      document.getElementById("modA").value = "plasma_ptau217_generic";
      setDefaults("A");
    }
  },
  {
    title: "Step 4: Test Result",
    text: "Select whether the test result was positive, negative, or indeterminate. This determines which likelihood ratio will be used.",
    target: "#catA",
    action: () => {
      document.getElementById("catA").value = "pos";
    }
  },
  {
    title: "Step 5: Calculate",
    text: "Now click to compute the probability! The tool will show both PET-referenced and autopsy-anchored estimates with clinical interpretation.",
    target: "#calc_dx",
    action: () => {
      // Will be executed when user clicks the button
    }
  }
];

let currentWizardStep = 0;
let wizardHighlightElement = null;

function startWizard() {
  // Switch to diagnostic tab if not already there
  showTab('dx');
  
  document.getElementById("wizard-overlay").style.display = "flex";
  currentWizardStep = 0;
  updateWizardStep();
  
  // Track wizard completion
  localStorage.setItem("wizardCompleted", "true");
}

function updateWizardStep() {
  const step = wizardSteps[currentWizardStep];
  const progress = ((currentWizardStep + 1) / wizardSteps.length) * 100;
  
  document.getElementById("wizard-text").textContent = step.text;
  document.getElementById("wizard-progress").style.width = progress + "%";
  document.getElementById("wizard-counter").textContent = `Step ${currentWizardStep + 1} of ${wizardSteps.length}`;
  
  // Update button states
  document.getElementById("wizard-prev").disabled = currentWizardStep === 0;
  document.getElementById("wizard-next").textContent = 
    currentWizardStep === wizardSteps.length - 1 ? "Finish" : "Next";
  
  // Remove previous highlight
  if (wizardHighlightElement) {
    wizardHighlightElement.classList.remove("wizard-highlight-active");
    wizardHighlightElement = null;
  }
  
  // Add highlight to target element
  if (step.target) {
    const targetEl = document.querySelector(step.target);
    if (targetEl) {
      targetEl.classList.add("wizard-highlight-active");
      wizardHighlightElement = targetEl;
      
      // Scroll target into view
      targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      
      // Focus the element if it's an input
      if (targetEl.tagName === 'INPUT' || targetEl.tagName === 'SELECT' || targetEl.tagName === 'BUTTON') {
        setTimeout(() => targetEl.focus(), 500);
      }
    }
  }
  
  // Execute step action for the last step or when there's no target interaction needed
  if (step.action && (currentWizardStep < wizardSteps.length - 1)) {
    setTimeout(step.action, 800);
  }
}

function nextWizardStep() {
  if (currentWizardStep < wizardSteps.length - 1) {
    currentWizardStep++;
    updateWizardStep();
  } else {
    closeWizard();
  }
}

function prevWizardStep() {
  if (currentWizardStep > 0) {
    currentWizardStep--;
    updateWizardStep();
  }
}

function closeWizard() {
  document.getElementById("wizard-overlay").style.display = "none";
  
  // Remove any remaining highlights
  if (wizardHighlightElement) {
    wizardHighlightElement.classList.remove("wizard-highlight-active");
    wizardHighlightElement = null;
  }
  
  // Special handling for final step - trigger calculation
  if (currentWizardStep === wizardSteps.length - 1) {
    setTimeout(() => {
      computeDiagnostic();
    }, 500);
  }
}

// Smart Suggestions System
function generateSmartSuggestions() {
  const age = Number(document.getElementById("age").value || 70);
  const stage = document.getElementById("stage").value;
  const apoe = document.getElementById("apoe").value;
  const probability = window.__POSTERIOR_AUTOPSY__ || window.__POSTERIOR__;
  
  if (!isFinite(probability)) return;
  
  const suggestions = [];
  
  // Age-based suggestions
  if (age > 80 && probability > 0.7) {
    suggestions.push("Consider amyloid-targeting therapies may have different risk/benefit profiles in patients over 80");
  }
  
  // Stage-based suggestions
  if (stage === "CN" && probability > 0.8) {
    suggestions.push("Preclinical amyloid positivity - consider research participation or monitoring protocols");
  } else if (stage === "MCI" && probability > 0.7) {
    suggestions.push("MCI with high amyloid probability suggests Alzheimer's pathophysiology - consider comprehensive workup");
  }
  
  // APOE-based suggestions
  if (apoe.includes("e4") && probability > 0.6) {
    suggestions.push("APOE ε4 carriers may have faster progression - consider more frequent monitoring");
  }
  
  // Test-specific suggestions
  const testA = document.getElementById("modA").value;
  if (testA.includes("plasma") && probability > 0.8) {
    suggestions.push("High plasma biomarker result - consider confirming with CSF or PET if clinically indicated");
  }
  
  // Risk-based suggestions
  if (probability > 0.9) {
    suggestions.push("Very high probability - discuss implications for treatment planning and family counseling");
  } else if (probability < 0.3) {
    suggestions.push("Low amyloid probability - consider alternative diagnostic pathways");
  }
  
  // Display suggestions
  const suggestionEl = document.getElementById("suggestions1");
  const listEl = document.getElementById("suggestion-list1");
  
  if (suggestions.length > 0) {
    listEl.innerHTML = suggestions.map(s => `<li>${s}</li>`).join("");
    suggestionEl.style.display = "block";
  } else {
    suggestionEl.style.display = "none";
  }
}

// Risk Stratification Visualization
function updateRiskVisualization() {
  const probability = window.__POSTERIOR_AUTOPSY__ || window.__POSTERIOR__;
  
  if (!isFinite(probability)) return;
  
  const riskEl = document.getElementById("risk-viz1");
  const indicatorEl = document.getElementById("risk-position1");
  
  if (riskEl && indicatorEl) {
    const position = Math.min(95, Math.max(5, probability * 100));
    indicatorEl.style.left = position + "%";
    riskEl.style.display = "block";
  }
}

// Case Management System
function saveCaseData() {
  const caseData = {
    id: Date.now().toString(),
    name: document.getElementById("case-name").value || `Case ${new Date().toLocaleDateString()}`,
    notes: document.getElementById("case-notes").value || "",
    timestamp: new Date().toISOString(),
    data: {
      age: document.getElementById("age").value,
      stage: document.getElementById("stage").value,
      apoe: document.getElementById("apoe").value,
      modA: document.getElementById("modA").value,
      catA: document.getElementById("catA").value,
      useB: document.getElementById("useB").value,
      modB: document.getElementById("modB").value,
      catB: document.getElementById("catB").value,
      petPosterior: window.__POSTERIOR__,
      autopsyPosterior: window.__POSTERIOR_AUTOPSY__
    }
  };
  
  const savedCases = JSON.parse(localStorage.getItem("savedCases") || "[]");
  savedCases.push(caseData);
  localStorage.setItem("savedCases", JSON.stringify(savedCases));
  
  updateSavedCasesList();
  
  // Clear case metadata
  document.getElementById("case-name").value = "";
  document.getElementById("case-notes").value = "";
  
  alert("Case saved successfully!");
}

function downloadCase() {
  const caseId = document.getElementById("saved-cases-list").value;
  if (!caseId) {
    alert("Please select a case to download.");
    return;
  }
  
  const savedCases = JSON.parse(localStorage.getItem("savedCases") || "[]");
  const caseData = savedCases.find(c => c.id === caseId);
  if (!caseData) {
    alert("Case not found.");
    return;
  }
  
  // Create downloadable JSON file
  const dataStr = JSON.stringify(caseData, null, 2);
  const blob = new Blob([dataStr], { type: 'application/json' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${caseData.name.replace(/[^a-z0-9]/gi, '_')}_${caseData.id}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

function importCase() {
  document.getElementById("case-file-input").click();
}

function handleCaseFileImport(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = function(e) {
    try {
      const caseData = JSON.parse(e.target.result);
      
      // Validate case data structure
      if (!caseData.data || !caseData.name || !caseData.timestamp) {
        throw new Error("Invalid case file format");
      }
      
      // Generate new ID to avoid conflicts
      caseData.id = Date.now().toString();
      caseData.name = caseData.name + " (Imported)";
      
      // Add to saved cases
      const savedCases = JSON.parse(localStorage.getItem("savedCases") || "[]");
      savedCases.push(caseData);
      localStorage.setItem("savedCases", JSON.stringify(savedCases));
      
      updateSavedCasesList();
      alert("Case imported successfully!");
      
    } catch (error) {
      alert("Error importing case: " + error.message);
    }
    
    // Clear the file input
    event.target.value = "";
  };
  reader.readAsText(file);
}

function deleteCase() {
  const caseId = document.getElementById("saved-cases-list").value;
  if (!caseId) {
    alert("Please select a case to delete.");
    return;
  }
  
  if (!confirm("Are you sure you want to delete this case?")) {
    return;
  }
  
  const savedCases = JSON.parse(localStorage.getItem("savedCases") || "[]");
  const filteredCases = savedCases.filter(c => c.id !== caseId);
  localStorage.setItem("savedCases", JSON.stringify(filteredCases));
  
  updateSavedCasesList();
  alert("Case deleted successfully!");
}

function updateSavedCasesList() {
  const savedCases = JSON.parse(localStorage.getItem("savedCases") || "[]");
  const select = document.getElementById("saved-cases-list");
  
  select.innerHTML = '<option value="">Select a saved case...</option>';
  savedCases.forEach(case_item => {
    const option = document.createElement("option");
    option.value = case_item.id;
    option.textContent = `${case_item.name} (${new Date(case_item.timestamp).toLocaleDateString()})`;
    select.appendChild(option);
  });
  
  // Show case management panel in advanced mode
  if (savedCases.length > 0 && document.body.classList.contains("advanced-mode")) {
    document.getElementById("case-management").style.display = "block";
  }
}

// What-If Sensitivity Analysis
function openWhatIfAnalysis() {
  document.getElementById("what-if-panel").style.display = "block";
  updateSensitivityAnalysis();
}

function updateSensitivityAnalysis() {
  const baseAge = Number(document.getElementById("age").value || 70);
  const ageVar = Number(document.getElementById("age-sensitivity").value);
  const lrVar = Number(document.getElementById("lr-sensitivity").value);
  const baseProbability = window.__POSTERIOR_AUTOPSY__ || window.__POSTERIOR__;
  
  if (!isFinite(baseProbability)) return;
  
  // Calculate probability range with variations
  const ageLow = Math.max(18, baseAge - ageVar);
  const ageHigh = Math.min(100, baseAge + ageVar);
  const lrMultLow = (100 - lrVar) / 100;
  const lrMultHigh = (100 + lrVar) / 100;
  
  // Simplified sensitivity calculation (would be more complex in reality)
  const probLow = Math.max(0, baseProbability * 0.8 * lrMultLow);
  const probHigh = Math.min(1, baseProbability * 1.2 * lrMultHigh);
  
  const rangePct = (probHigh - probLow) * 100;
  const rangeText = `${(probLow * 100).toFixed(0)}% - ${(probHigh * 100).toFixed(0)}%`;
  
  document.getElementById("sensitivity-text").textContent = rangeText;
  document.getElementById("sensitivity-range").style.width = `${rangePct * 2}%`;
  document.getElementById("age-range").textContent = `±${ageVar} years`;
  document.getElementById("lr-range").textContent = `±${lrVar}%`;
}

// Load example case
function loadExampleCase() {
  // Load a realistic example
  document.getElementById("age").value = "73";
  document.getElementById("stage").value = "MCI";
  document.getElementById("apoe").value = "e3e4";
  document.getElementById("modA").value = "plasma_ptau217_generic";
  document.getElementById("catA").value = "pos";
  setDefaults("A");
  updateAutoPrior();
  
  setTimeout(() => {
    computeDiagnostic();
  }, 500);
}

// Event Listeners for Phase 2 features
document.addEventListener("DOMContentLoaded", function() {
  // Wizard controls
  document.getElementById("start-wizard").addEventListener("click", startWizard);
  document.getElementById("wizard-close").addEventListener("click", closeWizard);
  document.getElementById("wizard-next").addEventListener("click", nextWizardStep);
  document.getElementById("wizard-prev").addEventListener("click", prevWizardStep);
  document.getElementById("wizard-skip").addEventListener("click", closeWizard);
  document.getElementById("example-case").addEventListener("click", loadExampleCase);
  
  // Case management
  document.getElementById("save_case").addEventListener("click", saveCaseData);
  document.getElementById("load-case").addEventListener("click", function() {
    const caseId = document.getElementById("saved-cases-list").value;
    if (!caseId) {
      alert("Please select a case to load.");
      return;
    }
    
    const savedCases = JSON.parse(localStorage.getItem("savedCases") || "[]");
    const case_item = savedCases.find(c => c.id === caseId);
    if (!case_item) {
      alert("Case not found.");
      return;
    }
    
    // Load case data
    Object.keys(case_item.data).forEach(key => {
      const el = document.getElementById(key);
      if (el && case_item.data[key] !== undefined) {
        el.value = case_item.data[key];
      }
    });
    
    updateAutoPrior();
    computeDiagnostic();
    alert("Case loaded successfully!");
  });
  
  // File-based case management
  document.getElementById("export-case").addEventListener("click", downloadCase);
  document.getElementById("import-case").addEventListener("click", importCase);
  document.getElementById("delete-case").addEventListener("click", deleteCase);
  document.getElementById("case-file-input").addEventListener("change", handleCaseFileImport);
  
  // What-if analysis
  document.getElementById("what_if").addEventListener("click", openWhatIfAnalysis);
  document.getElementById("close-what-if").addEventListener("click", function() {
    document.getElementById("what-if-panel").style.display = "none";
  });
  
  // Sensitivity sliders
  document.getElementById("age-sensitivity").addEventListener("input", updateSensitivityAnalysis);
  document.getElementById("lr-sensitivity").addEventListener("input", updateSensitivityAnalysis);
  
  // Initialize case management
  updateSavedCasesList();
  
  // Show wizard for first-time users
  if (!localStorage.getItem("wizardCompleted")) {
    setTimeout(() => {
      if (confirm("Would you like a guided tutorial on using this tool?")) {
        startWizard();
      } else {
        localStorage.setItem("wizardCompleted", "true");
      }
    }, 2000);
  }
});

// Apply defaults from TEST_LIBRARY into the LR inputs
function applyDefaultsFor(prefix){
  const modSel = document.getElementById(prefix==="A" ? "modA" : "modB");
  const mod = modSel?.value;
  const t = TEST_LIBRARY[mod];
  if(!t) return;
  const p = prefix;
  const pos = document.getElementById(p==="A" ? "lrA_pos" : "lrB_pos");
  const ind = document.getElementById(p==="A" ? "lrA_indet" : "lrB_indet");
  const neg = document.getElementById(p==="A" ? "lrA_neg" : "lrB_neg");
  if(pos) pos.value = (t.defaults?.pos ?? pos.value);
  if(ind) ind.value = (t.defaults?.indet ?? ind.value);
  if(neg) neg.value = (t.defaults?.neg ?? neg.value);
  // annotate reference under the selector if there is a spot
  const tag = document.getElementById(p==="A" ? "modA_ref" : "modB_ref");
  if(tag) tag.textContent = t.ref ? `ref: ${t.ref}` : "";
}

// Hook up change listeners if present elements exist
window.addEventListener("load", ()=>{
  const a = document.getElementById("modA");
  const b = document.getElementById("modB");
  if(a){ a.addEventListener("change", ()=>applyDefaultsFor("A")); applyDefaultsFor("A"); }
  if(b){ b.addEventListener("change", ()=>applyDefaultsFor("B")); }
});

function setAutopsyChip(id, p){
  const [bucket, _] = interpretP(p);
  const lab = labelAutopsy(p);
  setChip(id, bucket, lab);
}

// --- Therapy triage helpers ---
function getTriageCutoff(){
  const el = document.getElementById("triage_thresh");
  let v = el ? Number(el.value) : 0.80;
  if(!isFinite(v) || v<=0 || v>=1) v = 0.80;
  return v;
}
function triageFlag(prob){
  const thr = getTriageCutoff();
  return { meets: prob >= thr, thr };
}
function showTriage(id, prob){
  const spanId = id; // use a pill appended to the details line
  const thr = getTriageCutoff();
  // ensure a span exists right after the details node
  const details = document.getElementById(id.replace("triage_flag","post_details"));
  let pill = document.getElementById(spanId);
  if(!pill){
    pill = document.createElement("span");
    pill.id = spanId;
    pill.className = "pill";
    pill.style.marginLeft = "8px";
    if(details) details.appendChild(pill);
  }
  if(prob >= thr){
    pill.textContent = `Meets therapy triage (≥ ${Math.round(thr*100)}%)`;
  } else {
    pill.textContent = `Below triage (${Math.round(thr*100)}% cut-off)`;
  }
}
window.addEventListener("load", ()=>{
  const btn90 = document.getElementById("triage_quick90");
  if(btn90){
    btn90.addEventListener("click", ()=>{
      const el = document.getElementById("triage_thresh");
      if(el){ el.value = "0.90"; }
      // recompute if possible
      try{ computeDiagnostic(); }catch(e){}
    });
  }
});
