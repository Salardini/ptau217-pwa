import re, time, shutil, os
fn = "app.js"
src = open(fn, "r", encoding="utf-8").read()
bak = f"{fn}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
shutil.copy2(fn, bak)

pat = r'function\s+computeAutopsyPosteriors\s*\(\s*prior0\s*,\s*Avals\s*,\s*useB\s*\)\s*\{'
m = re.search(pat, src)
if not m: raise SystemExit("Didn't find computeAutopsyPosteriors(...) start")

# find matching brace
i = m.end()
depth = 1
while i < len(src) and depth > 0:
    if src[i] == '{': depth += 1
    elif src[i] == '}': depth -= 1
    i += 1
if depth != 0: raise SystemExit("Brace match failed")

new_fn = r"""
function computeAutopsyPosteriors(prior0, Avals, useB){
  const seP = Number(document.getElementById("pet_se_dx").value||0.92);
  const spP = Number(document.getElementById("pet_sp_dx").value||0.90);
  const prev= Number(document.getElementById("pet_prev_dx").value||0.50);

  const modA = document.getElementById("modA").value;
  const modB = document.getElementById("modB").value;

  const ppv = petPPV(seP, spP, prior0);
  const npv = petNPV(seP, spP, prior0);

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

  // If Test A is PET itself, autopsy posterior collapses to PET's PPV / (1−NPV)
  if (modA === "amyloid_pet") {
    const pA = Avals.catA==="pos" ? ppv : (Avals.catA==="neg" ? (1-npv) : prior0);
    renderA(pA, `PET observed. By definition: PET+ → PPV=${fmtPct(ppv)}, PET− → 1−NPV=${fmtPct(1-npv)} at prior ${fmtPct(prior0)}.`);
    if (useB) {
      // Once PET is known, PET-referenced tests can't move the autopsy posterior unless they have direct autopsy anchoring.
      const msg = `PET already observed; additional PET-referenced tests do not change the autopsy posterior.`;
      renderAB(pA, msg);
    } else {
      document.getElementById("post_aut_details2").innerHTML = "";
    }
    return;
  }

  // Otherwise, A is PET-referenced → use PET-mixture identity
  const resA = autopsyPosteriorFromB(prior0, seP, spP, Avals.lrA_pos, Avals.lrA_neg, Avals.catA);
  renderA(resA.p,
    `Mixture: P(PET+|A)×PPV + (1−P(PET+|A))×(1−NPV). Here P(PET+|A)=${(resA.q*100).toFixed(1)}%, PPV=${fmtPct(resA.ppv)}, NPV=${fmtPct(resA.npv)}.`);

  if (useB) {
    const catB = document.getElementById("catB").value;

    if (modB === "amyloid_pet") {
      // If B is PET, the chain collapses to PET PPV / (1−NPV)
      const pAB = catB==="pos" ? ppv : (catB==="neg" ? (1-npv) : resA.p);
      renderAB(pAB, `Second test is PET. Autopsy posterior collapses to PET: PET+ → PPV=${fmtPct(ppv)}, PET− → 1−NPV=${fmtPct(1-npv)}.`);
    } else {
      const lrB_pos = Number(document.getElementById("lrB_pos").value||1);
      const lrB_neg = Number(document.getElementById("lrB_neg").value||1);
      const A = { LRpos:Avals.lrA_pos, LRneg:Avals.lrA_neg, cat:Avals.catA };
      const B = { LRpos:lrB_pos,       LRneg:lrB_neg,       cat:catB       };
      const resAB = autopsyPosteriorFromAthenB(prior0, seP, spP, A, B);
      renderAB(resAB.p, `After A→B: PET mixture bounded to [${fmtPct(resAB.envelope[0])}, ${fmtPct(resAB.envelope[1])}] at prior ${fmtPct(prior0)}.`);
    }
  } else {
    document.getElementById("post_aut_details2").innerHTML = "";
  }
}
""".strip()+"\n"

new_src = src[:m.start()] + new_fn + src[i:]
open(fn, "w", encoding="utf-8").write(new_src)
print(f"Patched computeAutopsyPosteriors() (backup: {bak})")

# bump SW cache so browsers reload
if os.path.exists("sw.js"):
    sw = open("sw.js","r",encoding="utf-8").read()
    sw2, n = re.subn(r'amyloid-helper-v\d+', 'amyloid-helper-v7', sw)
    if n==0:
        sw2 = re.sub(r"(const CACHE=)['\"][^'\"]+(['\"])", r"\1amyloid-helper-v7\2", sw, count=1)
    open("sw.js","w",encoding="utf-8").write(sw2)
    print("Bumped SW cache to amyloid-helper-v7")
