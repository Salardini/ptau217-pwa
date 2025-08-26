import os, re, time, shutil
TS=time.strftime('%Y%m%d-%H%M%S')
def backup(p): 
    if os.path.exists(p): shutil.copy2(p, f"{p}.bak-"+TS)

app="app.js"; idx="index.html"; sw="sw.js"
for p in (app, idx, sw): backup(p)

# ---- 1) index.html: add triage controls under the Compute button (if missing) ----
html=open(idx,'r',encoding='utf-8').read()
orig_html=html

if 'id="triage_thresh"' not in html:
    # Insert a small row with the cut-off control right after the Compute button row
    html = re.sub(
        r'(id=["\']calc_dx["\'][^>]*>.*?</button>\s*</div>)',
        r"""\1
<div class="row small" id="triage_controls" style="gap:10px;margin-top:6px">
  <label class="small" for="triage_thresh" style="margin:0">Therapy triage cut-off (P(PET+))</label>
  <input type="number" id="triage_thresh" value="0.80" min="0" max="1" step="0.01" style="width:110px">
  <button class="btn secondary" id="triage_quick90" type="button" title="Set to 0.90">Quick: 0.90</button>
</div>
""",
        html, flags=re.S
    )

if html != orig_html:
    open(idx,'w',encoding='utf-8').write(html)
    print("index.html: added triage control (cut-off + quick 0.90).")
else:
    print("index.html: triage control already present; no change.")

# ---- 2) app.js: set colour thresholds and triage flagging ----
s=open(app,'r',encoding='utf-8').read()
orig_js=s

# (a) Ensure global thresholds exist once
if 'const COLOR_THRESHOLDS' not in s:
    s = s.replace(
        "const toOdds=p=>p/(1-p), fromOdds=o=>o/(1+o);",
        "const toOdds=p=>p/(1-p), fromOdds=o=>o/(1+o);\n"
        "// Colour thresholds used for chip buckets (both PET and autopsy layers)\n"
        "const COLOR_THRESHOLDS = { green:0.90, amber:0.70, grey:0.30, red:0.10 };"
    )

# (b) Replace interpretP() to use your thresholds; keep bucket classes stable
def patch_interpret(js):
    m = re.search(r'function\s+interpretP\s*\(', js)
    if not m: return js, False
    # find block
    lb = js.find("{", m.end()-1); depth=1; i=lb+1
    while i < len(js) and depth>0:
        if js[i]=="{": depth+=1
        elif js[i]=="}": depth-=1
        i+=1
    body = r"""
function interpretP(p){
  if(!isFinite(p)) return ["muted","—"];
  const T = COLOR_THRESHOLDS;
  // Map our logical bins to existing chip classes: green->"good", amber->"warn", red->"bad", grey->"muted"
  if(p >= T.green) return ["good","High likelihood of PET positivity"];
  if(p >= T.amber) return ["warn","Likely PET positivity"];
  if(p <= T.red)   return ["bad","Low likelihood of PET positivity"];
  if(p <= T.grey)  return ["warn","Likely PET negative"];
  return ["muted","Indeterminate"];
}
"""
    return js[:m.start()] + body + js[i:], True

s, changed_interp = patch_interpret(s)

# (c) Add triage helpers + hook into computeDiagnostic()
if "function triageFlag(" not in s:
    s += r"""
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
"""

# Hook into computeDiagnostic() result display to call showTriage
def inject_triage_calls(js):
    m = re.search(r'function\s+computeDiagnostic\s*\(', js)
    if not m: return js, False
    lb = js.find("{", m.end()-1); depth=1; i=lb+1
    while i<len(js) and depth>0:
        if js[i]=="{": depth+=1
        elif js[i]=="}": depth-=1
        i+=1
    fn = js[m.start():i]
    # after we populate post_details1, add showTriage('triage_flag1', qA)
    fn = re.sub(
        r'(document\.getElementById\("post_details1"\)[^\n;]+;)',
        r'\1\n  showTriage("triage_flag1", qA);',
        fn
    )
    # after we populate post_details2 inside the useB branch, add showTriage('triage_flag2', qAB)
    fn = re.sub(
        r'(document\.getElementById\("post_details2"\)[^\n;]+;)',
        r'\1\n    showTriage("triage_flag2", qAB);',
        fn
    )
    return js[:m.start()] + fn + js[i:], True

s, changed_triage = inject_triage_calls(s)

if s != orig_js:
    open(app,'w',encoding='utf-8').write(s)
    print("app.js: colour thresholds + triage helpers wired; interpretP updated.")
else:
    print("app.js: no changes (already patched).")

# ---- 3) bump Service Worker cache so browsers reload ----
if os.path.exists(sw):
    swc=open(sw,'r',encoding='utf-8').read()
    swc2, n = re.subn(r'amyloid-helper-v\d+', 'amyloid-helper-v106', swc)
    if n==0:
        swc2 = re.sub(r'(const\s+CACHE\s*=\s*[\'"])[^\'"]+([\'"])', r'\1amyloid-helper-v106\2', swc, count=1)
    open(sw,'w',encoding='utf-8').write(swc2)
    print("sw.js: cache bumped to amyloid-helper-v106")
