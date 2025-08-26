import re, time, shutil, os
fn = "app.js"
src = open(fn, "r", encoding="utf-8").read()
bak = f"{fn}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
shutil.copy2(fn, bak)

# Replace entire computeDiagnostic() with a version that overrides the centered display for PET
pat = r'function\s+computeDiagnostic\s*\(\s*\)\s*\{'
m = re.search(pat, src)
if not m: raise SystemExit("Didn't find computeDiagnostic() start")

# find matching brace
i = m.end()
depth = 1
while i < len(src) and depth > 0:
    if src[i] == '{': depth += 1
    elif src[i] == '}': depth -= 1
    i += 1
if depth != 0: raise SystemExit("Brace match failed for computeDiagnostic()")

new_fn = r"""
function computeDiagnostic(){
  const p_auto = updateAutoPrior();
  const prior_override = document.getElementById("prior_override").value;
  const prior0 = prior_override ? clamp(Number(prior_override), 1e-6, 1-1e-6) : p_auto;

  // Test A
  const modA = document.getElementById("modA").value;
  const catA = document.getElementById("catA").value;
  const lrA_pos = Number(document.getElementById("lrA_pos").value||1);
  const lrA_ind = Number(document.getElementById("lrA_indet").value||1);
  const lrA_neg = Number(document.getElementById("lrA_neg").value||1);
  const LR_A = lrForCategory(catA, {pos:lrA_pos, indet:lrA_ind, neg:lrA_neg});

  const showUncert = document.getElementById("uncert").checked;
  let ciA = null;
  if(showUncert){
    const lib = TEST_LIBRARY[modA].defaults;
    ciA = {pos:[lib.pos*0.65, lib.pos*1.55], indet:[0.8,1.25], neg:[lib.neg*0.5, lib.neg*1.5]}[catA];
  }

  const o0 = toOdds(prior0);
  const p1 = fromOdds(o0 * LR_A);
  const p1lo = ciA ? fromOdds(o0 * ciA[0]) : null;
  const p1hi = ciA ? fromOdds(o0 * ciA[1]) : null;

  // Default "as-entered" display (P(A+))
  const [b1,lab1] = interpretP(p1);
  document.getElementById("post_p1").textContent = ciA ?
    `Posterior P(A+) = ${fmtPct(p1)}  (≈ ${fmtPct(p1lo)} to ${fmtPct(p1hi)})` :
    `Posterior P(A+) = ${fmtPct(p1)}`;
  document.getElementById("post_details1").innerHTML =
    `Prior = ${fmtPct(prior0)} · LR<sub>A</sub> = ${LR_A.toFixed(2)} → Bayes on odds.`;

  // PPV/NPV *for Test A at this prior*
  const ppvA = fromOdds(o0 * lrA_pos);
  const npvA = 1 - fromOdds(o0 * lrA_neg);
  document.getElementById("post_details1").innerHTML +=
    `<br/><span class="muted">At prior ${fmtPct(prior0)} → PPV_A = ${fmtPct(ppvA)} · NPV_A = ${fmtPct(npvA)}</span>`;
  setChip("chip1", b1, lab1);

  // If A is PET, override the centered display to show P(PET+)=100%/0%
  if (modA === "amyloid_pet") {
    if (catA === "pos") {
      document.getElementById("post_p1").textContent = `P(PET+) = 100.0%`;
      document.getElementById("post_details1").innerHTML += `<br/><span class="muted">PET observed positive → P(PET+)=100% by definition; autopsy-anchored posterior is shown in the PET panel below.</span>`;
    } else if (catA === "neg") {
      document.getElementById("post_p1").textContent = `P(PET+) = 0.0%`;
      document.getElementById("post_details1").innerHTML += `<br/><span class="muted">PET observed negative → P(PET+)=0% by definition; autopsy-anchored posterior is shown in the PET panel below.</span>`;
    } else {
      // Indeterminate PET (rare UI case) — leave the default P(A+) line
    }
  }

  // Optional Test B
  const useB = document.getElementById("useB").value==="yes";
  document.getElementById("comboBlock").style.display = useB ? "block" : "none";
  document.getElementById("comboAutBlock").style.display = useB ? "block" : "none";
  if(useB){
    const modB   = document.getElementById("modB").value;
    const catB   = document.getElementById("catB").value;
    const lrB_pos = Number(document.getElementById("lrB_pos").value||1);
    const lrB_ind = Number(document.getElementById("lrB_indet").value||1);
    const lrB_neg = Number(document.getElementById("lrB_neg").value||1);
    const LR_B = lrForCategory(catB, {pos:lrB_pos, indet:lrB_ind, neg:lrB_neg});

    const o1 = toOdds(p1);
    const p2 = fromOdds(o1 * LR_B);
    const [b2,lab2] = interpretP(p2);
    document.getElementById("post_p2").textContent = `Posterior P(A+) = ${fmtPct(p2)}`;
    document.getElementById("post_details2").innerHTML =
      `Prior (after A) = ${fmtPct(p1)} · LR<sub>B</sub> = ${LR_B.toFixed(2)}.`;

    const ppvB = fromOdds(o1 * lrB_pos);
    const npvB = 1 - fromOdds(o1 * lrB_neg);
    document.getElementById("post_details2").innerHTML +=
      `<br/><span class="muted">At prior ${fmtPct(p1)} → PPV_B = ${fmtPct(ppvB)} · NPV_B = ${fmtPct(npvB)}</span>`;
    setChip("chip2", b2, lab2);
    window.__POSTERIOR__ = p2;

    // If B is PET, override the centered A→B display to show PET certainty
    if (modB === "amyloid_pet") {
      if (catB === "pos") {
        document.getElementById("post_p2").textContent = `P(PET+) = 100.0%`;
        document.getElementById("post_details2").innerHTML += `<br/><span class="muted">PET observed positive → P(PET+)=100% by definition; autopsy-anchored posterior is in the PET panel below.</span>`;
      } else if (catB === "neg") {
        document.getElementById("post_p2").textContent = `P(PET+) = 0.0%`;
        document.getElementById("post_details2").innerHTML += `<br/><span class="muted">PET observed negative → P(PET+)=0% by definition; autopsy-anchored posterior is in the PET panel below.</span>`;
      }
    }
  } else {
    document.getElementById("post_details2").innerHTML = "";
    window.__POSTERIOR__ = p1;
  }

  // Compute autopsy-anchored posteriors (PET mixture logic / PET rule)
  computeAutopsyPosteriors(prior0, {catA, lrA_pos, lrA_ind, lrA_neg}, useB);
}
""".strip()+"\n"

new_src = src[:m.start()] + new_fn + src[i:]
open(fn, "w", encoding="utf-8").write(new_src)
print(f"Patched computeDiagnostic() (backup: {bak})")

# bump SW cache so clients reload
if os.path.exists("sw.js"):
    sw = open("sw.js","r",encoding="utf-8").read()
    sw2, n = re.subn(r'amyloid-helper-v\d+', 'amyloid-helper-v8', sw)
    if n==0:
        sw2 = re.sub(r"(const CACHE=)['\"][^'\"]+(['\"])", r"\1amyloid-helper-v8\2", sw, count=1)
    open("sw.js","w",encoding="utf-8").write(sw2)
    print("Bumped SW cache to amyloid-helper-v8")
