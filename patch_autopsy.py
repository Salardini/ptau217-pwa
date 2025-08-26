import os, re, time, shutil

repo = os.getcwd()
app = os.path.join(repo, "app.js")
sw  = os.path.join(repo, "sw.js")

ts = time.strftime("%Y%m%d-%H%M%S")

def backup(path):
    if os.path.exists(path):
        shutil.copy2(path, f"{path}.bak-{ts}")

if not os.path.exists(app):
    raise SystemExit(f"ERROR: app.js not found at {app}")

backup(app); backup(sw)

with open(app, "r", encoding="utf-8") as f:
    content = f.read()

start_marker = "/* ---------- Autopsy harmonization core"
end_regex = re.compile(r'^[ \t]*//[ \t]*Bridge tab utilities', re.M)

start_idx = content.find(start_marker)
if start_idx < 0:
    raise SystemExit("ERROR: Could not find start marker in app.js")

m = end_regex.search(content, pos=start_idx)
if not m:
    raise SystemExit("ERROR: Could not find end marker line starting with // Bridge tab utilities")

prefix = content[:start_idx]
suffix = content[m.start():]

patch = r"""/* ---------- Autopsy harmonization core (MIXTURE method; bounded) ---------- */
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
  const seP = Number(document.getElementById("pet_se_dx").value||0.92);
  const spP = Number(document.getElementById("pet_sp_dx").value||0.90);
  const prev= Number(document.getElementById("pet_prev_dx").value||0.50); // kept for display consistency

  // A as-entered LRs (vs PET)
  const resA = autopsyPosteriorFromB(prior0, seP, spP, Avals.lrA_pos, Avals.lrA_neg, Avals.catA);

  // Render A autopsy posterior
  document.getElementById("post_aut_p1").textContent = `Posterior P(A+) = ${fmtPct(resA.p)}`;
  document.getElementById("post_aut_details1").innerHTML =
    `Mixture: P(PET+|B)×PPV + (1−P(PET+|B))×(1−NPV). ` +
    `Here P(PET+|B)=${(resA.q*100).toFixed(1)}%, PPV=${fmtPct(resA.ppv)}, ` +
    `NPV=${fmtPct(resA.npv)}; bounded to [${fmtPct(resA.envelope[0])}, ${fmtPct(resA.envelope[1])}].`;
  const [bucketA,labelA] = interpretP(resA.p);
  setChip("chip_aut1", bucketA, labelA);

  // Optional B
  if(useB){
    const lrB_pos = Number(document.getElementById("lrB_pos").value||1);
    const lrB_neg = Number(document.getElementById("lrB_neg").value||1);
    const catB    = document.getElementById("catB").value;
    const A = { LRpos:Avals.lrA_pos, LRneg:Avals.lrA_neg, cat:Avals.catA };
    const B = { LRpos:lrB_pos,       LRneg:lrB_neg,       cat:catB       };

    const resAB = autopsyPosteriorFromAthenB(prior0, seP, spP, A, B);
    document.getElementById("post_aut_p2").textContent = `Posterior P(A+) = ${fmtPct(resAB.p)}`;
    document.getElementById("post_aut_details2").innerHTML =
      `After A: update PET with B then mix with PET PPV/NPV at prior ${fmtPct(prior0)}; ` +
      `bounded to [${fmtPct(resAB.envelope[0])}, ${fmtPct(resAB.envelope[1])}].`;
    const [bucketB,labelB] = interpretP(resAB.p);
    setChip("chip_aut2", bucketB, labelB);
    window.__POSTERIOR_AUTOPSY__ = resAB.p;
  } else {
    document.getElementById("post_aut_details2").innerHTML = "";
    window.__POSTERIOR_AUTOPSY__ = resA.p;
  }
}

/* --- Legacy helpers kept for the Harmonize Tools tab (do not use on Diagnostic) --- */
function seSpFromLR(LRp, LRn){
  const den = (LRn - LRp);
  if (Math.abs(den) < 1e-9) return {error:"Invalid LRs (den≈0)"};
  let sp = (1 - LRp) / den;
  let se = 1 - LRn * sp;
  return {se, sp};
}
function bridgeToAutopsy_fromLR(LRp, LRn, seP, spP, prev){
  const m = seSpFromLR(LRp, LRn);
  if (m.error) return {error:m.error};
  const a = Math.max(0, Math.min(1, m.se));
  const b = Math.max(0, Math.min(1, m.sp));
  const u = petPPV(seP, spP, prev), v = petNPV(seP, spP, prev);
  const det = u + v - 1; if (det <= 0) return {error:"Invalid PET inputs (u+v-1 ≤ 0)"};
  const A = a - 1 + u, B = b - 1 + v;
  let se = (A*v + (1-u)*B) / det, sp = (u*B + (1-v)*A) / det;
  let warn=false; if (se<0||se>1||sp<0||sp>1){ warn=true; }
  se = Math.max(1e-3, Math.min(0.999, se));
  sp = Math.max(1e-3, Math.min(0.999, sp));
  return { se, sp, lrpos: se/(1-sp), lrneg:(1-se)/sp, warn };
}
"""

new_content = prefix + patch + suffix
with open(app, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Patched app.js (backup: app.js.bak-{ts})")

# Bump Service Worker cache version
if os.path.exists(sw):
    with open(sw, "r", encoding="utf-8") as f:
        swc = f.read()
    swc2, n = re.subn(r'amyloid-helper-v\d+', 'amyloid-helper-v6', swc)
    if n == 0:
        swc2 = re.sub(r"(const CACHE=)['\"][^'\"]+(['\"])", r"\1amyloid-helper-v6\2", swc, count=1)
    with open(sw, "w", encoding="utf-8") as f:
        f.write(swc2)
    print(f"Bumped Service Worker cache to amyloid-helper-v6 (backup: sw.js.bak-{ts})")
else:
    print("Note: sw.js not found; skipped SW bump.")
