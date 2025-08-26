import re, time, shutil, os
fn="app.js"
src=open(fn,"r",encoding="utf-8").read()
bak=f"{fn}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
shutil.copy2(fn,bak)

# 1) Ensure autopsy-specific label helper exists
if "function labelAutopsy(" not in src:
    src = src.replace("function interpretP(", 
r"""function interpretP("""
) + r"""
// Autopsy-specific chip labels (histopathology wording)
function labelAutopsy(p){
  if(!isFinite(p)) return "—";
  if(p>=0.90) return "High probability of autopsy A+";
  if(p>=0.70) return "Likely autopsy A+";
  if(p<=0.10) return "Low probability of autopsy A+";
  if(p<=0.30) return "Likely autopsy A−";
  return "Indeterminate on autopsy scale";
}
"""

# 2) Add a small wrapper that sets autopsy chip text using labelAutopsy
if "function setAutopsyChip(" not in src:
    src += r"""
function setAutopsyChip(id, p){
  const [bucket, _] = interpretP(p);
  const lab = labelAutopsy(p);
  setChip(id, bucket, lab);
}
"""

# 3) Rewrite computeAutopsyPosteriors to call setAutopsyChip(...)
m=re.search(r'function\s+computeAutopsyPosteriors\s*\(', src)
if not m:
    raise SystemExit("Couldn't find computeAutopsyPosteriors()")
# find block end
lb = src.find("{", m.end()-1)
depth=1; i=lb+1
while i<len(src) and depth>0:
    if src[i]=="{": depth+=1
    elif src[i]=="}": depth-=1
    i+=1
body = src[m.start():i]

# replace any setChip('chip_aut1/2', ...) calls with setAutopsyChip using the corresponding p
body = re.sub(r'setChip\(\s*"chip_aut1"\s*,[^;]*;', '/* replaced */', body)
body = re.sub(r'setChip\(\s*"chip_aut2"\s*,[^;]*;', '/* replaced */', body)
# ensure render helpers use setAutopsyChip with the p they render
body = re.sub(
    r'function\s+renderA\s*\(\s*p\s*,\s*msg\s*\)\s*\{[^}]*?\}',
    r"""function renderA(p,msg){
  document.getElementById("post_aut_p1").textContent = `Posterior P(A+) = ${fmtPct(p)}`;
  document.getElementById("post_aut_details1").innerHTML = msg;
  setAutopsyChip("chip_aut1", p);
  window.__POSTERIOR_AUTOPSY__ = p;
}""",
    body, flags=re.S
)
body = re.sub(
    r'function\s+renderAB\s*\(\s*p\s*,\s*msg\s*\)\s*\{[^}]*?\}',
    r"""function renderAB(p,msg){
  document.getElementById("post_aut_p2").textContent = `Posterior P(A+) = ${fmtPct(p)}`;
  document.getElementById("post_aut_details2").innerHTML = msg;
  setAutopsyChip("chip_aut2", p);
  window.__POSTERIOR_AUTOPSY__ = p;
}""",
    body, flags=re.S
)

src = src[:m.start()] + body + src[i:]

open(fn,"w",encoding="utf-8").write(src)
print(f"Patched autopsy chip labels (backup: {bak})")

# bump service worker so browsers reload
sw="sw.js"
if os.path.exists(sw):
    swc=open(sw,"r",encoding="utf-8").read()
    swc = re.sub(r'amyloid-helper-v\d+','amyloid-helper-v104',swc)
    if "amyloid-helper-v104" not in swc:
        swc = re.sub(r'(const CACHE=)[\'"][^\'"]+[\'"]', r"\1'amyloid-helper-v104'", swc, count=1)
    open(sw,"w",encoding="utf-8").write(swc)
    print("Bumped SW cache to amyloid-helper-v104")
