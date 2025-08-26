import os, re, time, shutil

TS = time.strftime('%Y%m%d-%H%M%S')

def backup(p):
    if os.path.exists(p):
        shutil.copy2(p, f"{p}.bak-{TS}")

def replace_function(js_text, func_name, new_src):
    pat = re.compile(rf'function\s+{func_name}\s*\(', re.M)
    m = pat.search(js_text)
    if not m:
        raise RuntimeError(f"Could not find function {func_name} in app.js")
    # find function block by counting braces
    i = m.start()
    # move to first "{"
    lb = js_text.find("{", m.end()-1)
    if lb < 0: raise RuntimeError(f"Malformed function {func_name}: no opening brace")
    depth, j = 1, lb+1
    while j < len(js_text) and depth>0:
        if js_text[j] == "{": depth += 1
        elif js_text[j] == "}": depth -= 1
        j += 1
    if depth != 0: raise RuntimeError(f"Brace matching failed for {func_name}")
    return js_text[:i] + new_src + js_text[j:]

# --- Files ---
app = "app.js"
idx = "index.html"
sw  = "sw.js"

for p in (app, idx, sw):
    if os.path.exists(p): backup(p)

# --- Load app.js ---
with open(app, "r", encoding="utf-8") as f:
    js = f.read()

# --- New computeDiagnostic(): TOP = PET layer with PET=100%/0% rule ---
computeDiagnostic_src = r"""
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
  }

  // Keep PET layer for reference
  window.__POSTERIOR__ = qAB;

  // Compute the autopsy layer (PPV/1−NPV when PET observed; mixture otherwise)
  computeAutopsyPosteriors(prior0, {catA, lrA_pos:lrApos, lrA_ind:lrAind, lrA_neg:lrAneg}, useB);
}
"""

# --- New computeAutopsyPosteriors(): PET rule + mixture when PET not observed ---
computeAutopsyPosteriors_src = r"""
function computeAutopsyPosteriors(prior0, Avals, useB){
  // PET Se/Sp and derived PPV/NPV at this prior
  const seP = Number(document.getElementById("pet_se_dx")?.value || 0.92);
  const spP = Number(document.getElementById("pet_sp_dx")?.value || 0.90);
  const ppv = (seP*prior0) / (seP*prior0 + (1-spP)*(1-prior0));
  const npv = (spP*(1-prior0)) / ((1-seP)*prior0 + spP*(1-prior0));
  const lo  = 1 - npv, hi = ppv;

  const modA = document.getElementById("modA").value;
  const catA = Avals.catA;

  function renderA(p, msg){
    document.getElementById("post_aut_p1").textContent = `Posterior P(A+) = ${fmtPct(p)}`;
    document.getElementById("post_aut_details1").innerHTML = msg;
    const [b,l] = interpretP(p); setChip("chip_aut1", b, l);
    window.__POSTERIOR_AUTOPSY__ = p;
  }
  function renderAB(p, msg){
    document.getElementById("post_aut_p2").textContent = `Posterior P(A+) = ${fmtPct(p)}`;
    document.getElementById("post_aut_details2").innerHTML = msg;
    const [b,l] = interpretP(p); setChip("chip_aut2", b, l);
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
"""

# Replace both functions
js = replace_function(js, "computeDiagnostic", computeDiagnostic_src)
js = replace_function(js, "computeAutopsyPosteriors", computeAutopsyPosteriors_src)

with open(app, "w", encoding="utf-8") as f:
    f.write(js)
print("Patched app.js: computeDiagnostic() and computeAutopsyPosteriors().")

# --- index.html: make the layer labels explicit ---
if os.path.exists(idx):
    with open(idx, "r", encoding="utf-8") as f:
        html = f.read()
    # Rename headings (robust to spacing)
    html = re.sub(r'(<h3 class="h">)\s*Posterior after Test A\s*\(as-entered\)\s*(</h3>)',
                  r'\1PET layer after Test A — P(PET+)\2', html, flags=re.M)
    html = re.sub(r'(<h3 class="h">)\s*Posterior after Test A → Test B\s*\(as-entered\)\s*(</h3>)',
                  r'\1PET layer after Test A → Test B — P(PET+)\2', html, flags=re.M)
    html = re.sub(r'(<h3 class="h">)\s*Autopsy-anchored posterior after Test A\s*(</h3>)',
                  r'\1Autopsy layer after Test A — Posterior P(autopsy A+)\2', html, flags=re.M)
    html = re.sub(r'(<h3 class="h">)\s*Autopsy-anchored posterior after Test A → Test B\s*(</h3>)',
                  r'\1Autopsy layer after Test A → Test B — Posterior P(autopsy A+)\2', html, flags=re.M)
    with open(idx, "w", encoding="utf-8") as f:
        f.write(html)
    print("Patched index.html headings.")

# --- bump SW cache so clients reload ---
if os.path.exists(sw):
    with open(sw, "r", encoding="utf-8") as f:
        swc = f.read()
    swc2, n = re.subn(r'amyloid-helper-v\d+', 'amyloid-helper-v11', swc)
    if n == 0:
        swc2 = re.sub(r"(const CACHE=)['\"][^'\"]+(['\"])", r"\1amyloid-helper-v11\2", swc, count=1)
    with open(sw, "w", encoding="utf-8") as f:
        f.write(swc2)
    print("Bumped Service Worker cache to amyloid-helper-v11.")
else:
    print("Note: sw.js not found; skipped SW bump.")
