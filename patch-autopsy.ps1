param(
  # Path to your repo folder (where app.js and sw.js live)
  [string]$Repo = "$HOME\ptau217-pwa",
  # If provided, will git add/commit/push after patching
  [switch]$Commit
)

Write-Host "Repo: $Repo" -ForegroundColor Cyan
$AppJs = Join-Path $Repo 'app.js'
$SwJs  = Join-Path $Repo 'sw.js'

if (!(Test-Path $AppJs)) { throw "app.js not found at $AppJs" }
if (!(Test-Path $SwJs))  { throw "sw.js not found at  $SwJs"  }

# --- Backups ---
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
Copy-Item $AppJs "$AppJs.bak.$ts"
Copy-Item $SwJs  "$SwJs.bak.$ts"
Write-Host "Backed up app.js and sw.js" -ForegroundColor DarkGray

# --- New JS block (PET-mixture autopsy math + legacy helpers kept for Tools tab) ---
$NewBlock = @'
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
  const p  = clamp(q*ppv + (1-q)*lo, lo, hi);

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
  const p  = clamp(q2*ppv + (1-q2)*lo, lo, hi);

  return { p, q2, ppv, npv, envelope:[lo,hi] };
}

// Replace the old autopsy computation used on the Diagnostic page
function computeAutopsyPosteriors(prior0, Avals, useB){
  const seP = Number(document.getElementById("pet_se_dx").value||0.92);
  const spP = Number(document.getElementById("pet_sp_dx").value||0.90);
  const prev= Number(document.getElementById("pet_prev_dx").value||0.50);

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

/* --- (optional) Keep these legacy bridge helpers ONLY for the Harmonize Tools tab --- */
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
  const a = clamp(m.se, 0, 1), b = clamp(m.sp, 0, 1); // a=Se_{B|P}, b=Sp_{B|P}
  const u = petPPV(seP, spP, prev), v = petNPV(seP, spP, prev);
  const det = u + v - 1; if (det <= 0) return {error:"Invalid PET inputs (u+v-1 ≤ 0)"};
  const A = a - 1 + u, B = b - 1 + v;
  let se = (A*v + (1-u)*B) / det, sp = (u*B + (1-v)*A) / det;
  let warn=false; if (se<0||se>1||sp<0||sp>1){ warn=true; }
  se = clamp(se, 1e-3, 0.999); sp = clamp(sp, 1e-3, 0.999);
  return { se, sp, lrpos: se/(1-sp), lrneg:(1-se)/sp, warn };
}
'@

# --- Patch app.js: replace from the old core block up to (but not including) the Bridge tab utilities anchor ---
$js = Get-Content -Path $AppJs -Raw -Encoding UTF8

$pattern = '(?s)/\* ---------- Autopsy harmonization core.*?// Bridge tab utilities'
if ($js -notmatch $pattern) {
  throw "Could not find the Autopsy block markers in app.js. Aborting (file layout differs)."
}

$jsPatched = [regex]::Replace($js, $pattern, ($NewBlock + "`r`n// Bridge tab utilities"))
if ($jsPatched -eq $js) { throw "No change applied to app.js (regex matched nothing)." }

Set-Content -Path $AppJs -Value $jsPatched -Encoding UTF8
Write-Host "Patched app.js with PET-mixture autopsy math." -ForegroundColor Green

# --- Bump SW cache to v5 (any prior vN → v5) ---
$sw = Get-Content -Path $SwJs -Raw -Encoding UTF8
$sw2 = [regex]::Replace($sw, 'amyloid-helper-v\d+', 'amyloid-helper-v5')
if ($sw2 -ne $sw) {
  Set-Content -Path $SwJs -Value $sw2 -Encoding UTF8
  Write-Host "Bumped Service Worker cache → amyloid-helper-v5" -ForegroundColor Green
} else {
  Write-Host "Note: did not find amyloid-helper-vN in sw.js; please bump cache name manually." -ForegroundColor Yellow
}

# --- Optional: git commit & push ---
if ($Commit) {
  if (Test-Path (Join-Path $Repo '.git')) {
    Write-Host "Committing and pushing..." -ForegroundColor Cyan
    git -C $Repo add app.js sw.js
    git -C $Repo commit -m "Autopsy posterior: switch to PET-mixture identity (bounded); bump SW cache v5"
    git -C $Repo push
  } else {
    Write-Host "Skipping git: $Repo is not a git repo." -ForegroundColor Yellow
  }
}

Write-Host "Done. Hard-refresh your site to pick up the new SW, or reinstall the PWA on iOS." -ForegroundColor Cyan
