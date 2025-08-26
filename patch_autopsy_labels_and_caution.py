import os, re, time, shutil
TS=time.strftime('%Y%m%d-%H%M%S')

def backup(p):
    if os.path.exists(p): shutil.copy2(p, f"{p}.bak-"+TS)

app="app.js"; idx="index.html"; sw="sw.js"
for p in (app, idx, sw): backup(p)

# ---------- app.js: add autopsy-specific chip labels and use them ----------
s=open(app,'r',encoding='utf-8').read()
orig=s

# 1) Insert a helper to label autopsy probability (robust insertion)
if "function labelAutopsy(" not in s:
    # try to insert after interpretP if present, else at top
    m=re.search(r'function\s+interpretP\s*\(', s)
    insert_at = m.start() if m else 0
    helper = r"""
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
"""
    s = s[:insert_at] + helper + s[insert_at:]

# 2) In computeAutopsyPosteriors(), override the chip text with autopsy wording
def repl_aut_chip(block):
    # replace setChip(... labelA) with setChip(... labelAutopsy(p))
    block = re.sub(
        r'const\s*\[\s*bucketA\s*,\s*labelA\s*\]\s*=\s*interpretP\s*\(\s*([^)]+)\s*\)\s*;',
        r'const [ bucketA, _labelA ] = interpretP(\1);\n  const labelA = labelAutopsy(\1);',
        block
    )
    block = re.sub(
        r'setChip\(\s*"chip_aut1"\s*,\s*bucketA\s*,\s*labelA\s*\)\s*;',
        r'setChip("chip_aut1", bucketA, labelA);',
        block
    )
    block = re.sub(
        r'const\s*\[\s*bucketB\s*,\s*labelB\s*\]\s*=\s*interpretP\s*\(\s*([^)]+)\s*\)\s*;',
        r'const [ bucketB, _labelB ] = interpretP(\1);\n    const labelB = labelAutopsy(\1);',
        block
    )
    block = re.sub(
        r'setChip\(\s*"chip_aut2"\s*,\s*bucketB\s*,\s*labelB\s*\)\s*;',
        r'setChip("chip_aut2", bucketB, labelB);',
        block
    )
    return block

m = re.search(r'function\s+computeAutopsyPosteriors\s*\(', s)
if m:
    # find end of function block by brace matching
    lb = s.find("{", m.end()-1)
    depth=1; i=lb+1
    while i < len(s) and depth>0:
        if s[i] == "{": depth += 1
        elif s[i] == "}": depth -= 1
        i += 1
    func = s[m.start():i]
    s = s[:m.start()] + repl_aut_chip(func) + s[i:]
else:
    print("WARN: computeAutopsyPosteriors() not found; chip text not changed.")

if s != orig:
    open(app,'w',encoding='utf-8').write(s)
    print("app.js: autopsy chip labels added and applied.")
else:
    print("app.js: no changes (already patched?).")

# ---------- index.html: add/ensure a combination caution callout ----------
html=open(idx,'r',encoding='utf-8').read()
h_orig=html

callout = """
<div id="combo_caution" class="callout small">
  <strong>Combining two tests:</strong> Bayes multiplication assumes the tests are
  <em>conditionally independent given disease</em>. Many pairs are correlated (e.g., two amyloid assays,
  two plasma tests, or PET plus a PET-referenced fluid test), which can overstate the evidence.
  Prefer mixing <em>different axes or matrices</em> (e.g., plasma tau + CSF amyloid). If two tests are likely correlated,
  consider <em>down-weighting</em> the second test (e.g., use an LR<sup>α</sup> with α≈0.6–0.8). Once PET is observed,
  the PET layer is 100%/0% and the autopsy panel collapses to PET’s PPV/1−NPV; additional PET-referenced tests will not
  change the autopsy posterior.
</div>
""".strip()

if 'id="combo_caution"' not in html:
    # Try to insert just after the compute button row on Diagnostic panel
    # anchor by the compute button id (calc_dx) if present
    if re.search(r'id=["\']calc_dx["\']', html):
        html = re.sub(r'(id=["\']calc_dx["\'][^>]*>.*?</button>\s*</div>)',
                      r'\1\n' + callout, html, flags=re.S)
        placed=True
    else:
        # fallback: inject near the end of Diagnostic section
        html = re.sub(r'(<section[^>]*id=["\']panel-dx["\'][^>]*>)(.*?)(</section>)',
                      lambda m: m.group(1) + m.group(2) + "\n" + callout + "\n" + m.group(3),
                      html, flags=re.S)
        placed=True
    print("index.html: combination caution inserted.")
else:
    print("index.html: combination caution already present.")

if html != h_orig:
    open(idx,'w',encoding='utf-8').write(html)

# ---------- bump SW cache so clients fetch fresh files ----------
if os.path.exists(sw):
    swc=open(sw,'r',encoding='utf-8').read()
    swc2, n = re.subn(r'amyloid-helper-v\d+', 'amyloid-helper-v103', swc)
    if n==0:
        swc2 = re.sub(r'(const\s+CACHE\s*=\s*[\'"])[^\'"]+([\'"])',
                      r'\1amyloid-helper-v103\2', swc, count=1)
    open(sw,'w',encoding='utf-8').write(swc2)
    print("sw.js: cache bumped to amyloid-helper-v103")
