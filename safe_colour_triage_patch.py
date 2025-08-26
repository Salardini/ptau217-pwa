import os, re, time, shutil
TS=time.strftime('%Y%m%d-%H%M%S')
def bk(p): 
    if os.path.exists(p): shutil.copy2(p, f"{p}.bak-{TS}")

app="app.js"; idx="index.html"; sw="sw.js"
for p in (app, idx, sw): bk(p)

# ---------- index.html: add triage controls under Compute button (id=calc_dx) ----------
html=open(idx,'r',encoding='utf-8').read()
if 'id="triage_thresh"' not in html:
    html = re.sub(
        r'(id=["\']calc_dx["\'][^>]*>.*?</button>\s*</div>)',
        r"""\1
<div class="row small" id="triage_controls" style="gap:10px;margin-top:6px">
  <label class="small" for="triage_thresh" style="margin:0">Therapy triage cut-off (P(PET+))</label>
  <input type="number" id="triage_thresh" value="0.80" min="0" max="1" step="0.01" style="width:110px">
  <button class="btn secondary" id="triage_quick90" type="button" title="Set to 0.90">Quick: 0.90</button>
</div>
""", html, flags=re.S)
    open(idx,'w',encoding='utf-8').write(html)
    print("index.html: triage controls added.")
else:
    print("index.html: triage controls already present.")

# ---------- app.js: thresholds + triage (non-invasive) ----------
s=open(app,'r',encoding='utf-8').read()

# 1) Ensure thresholds constant exists
if 'const COLOR_THRESHOLDS' not in s:
    s = s.replace(
        "const toOdds=p=>p/(1-p), fromOdds=o=>o/(1+o);",
        "const toOdds=p=>p/(1-p), fromOdds=o=>o/(1+o);\n"
        "const COLOR_THRESHOLDS = { green:0.90, amber:0.70, grey:0.30, red:0.10 };"
    )

# 2) Replace interpretP body to use your bins (labels remain PET-layer here)
m = re.search(r'function\s+interpretP\s*\(', s)
if not m:
    raise SystemExit("interpretP() not found in app.js")
lb = s.find("{", m.end()-1); depth=1; i=lb+1
while i<len(s) and depth>0:
    if s[i]=="{": depth+=1
    elif s[i]=="}": depth-=1
    i+=1
interp = r"""
function interpretP(p){
  if(!isFinite(p)) return ["muted","—"];
  const T = COLOR_THRESHOLDS;
  if(p >= T.green) return ["good","High likelihood of PET positivity"];
  if(p >= T.amber) return ["warn","Likely PET positivity"];
  if(p <= T.red)   return ["bad","Low likelihood of PET positivity"];
  if(p <= T.grey)  return ["warn","Likely PET negative"];
  return ["muted","Indeterminate"];
}
"""
s = s[:m.start()] + interp + s[i:]

# 3) Add triage helpers that DO NOT modify computeDiagnostic; they read numbers from the DOM
if "function getTriageCutoff(" not in s:
    s += r"""
// --- Therapy triage (non-invasive) ---
function getTriageCutoff(){
  const el = document.getElementById("triage_thresh");
  let v = el ? Number(el.value) : 0.80;
  if(!isFinite(v) || v<=0 || v>=1) v = 0.80;
  return v;
}
function parsePETProb(elId){ // reads "P(PET+) = 93.1%"
  const el = document.getElementById(elId); if(!el) return NaN;
  const m = (el.textContent||"").match(/([\d.]+)\s*%/);
  return m ? (parseFloat(m[1])/100) : NaN;
}
function ensureTriagePill(id, detailsId){
  let pill = document.getElementById(id);
  const details = document.getElementById(detailsId);
  if(!pill && details){
    pill = document.createElement("span");
    pill.id = id; pill.className="pill"; pill.style.marginLeft="8px";
    details.appendChild(pill);
  }
  return pill;
}
function updateTriagePills(){
  const thr = getTriageCutoff();
  // PET layer A
  const p1 = parsePETProb("post_p1");
  const pill1 = ensureTriagePill("triage_flag1","post_details1");
  if(pill1 && isFinite(p1)){
    pill1.textContent = (p1>=thr) ? `Meets therapy triage (≥ ${Math.round(thr*100)}%)`
                                  : `Below triage (${Math.round(thr*100)}% cut-off)`;
  }
  // PET layer A→B (if present)
  const el2 = document.getElementById("post_p2");
  if(el2){
    const p2 = parsePETProb("post_p2");
    const pill2 = ensureTriagePill("triage_flag2","post_details2");
    if(pill2 && isFinite(p2)){
      pill2.textContent = (p2>=thr) ? `Meets therapy triage (≥ ${Math.round(thr*100)}%)`
                                    : `Below triage (${Math.round(thr*100)}% cut-off)`;
    }
  }
}
window.addEventListener("load", ()=>{
  // quick set to 0.90
  const btn90 = document.getElementById("triage_quick90");
  if(btn90){
    btn90.addEventListener("click", ()=>{
      const el = document.getElementById("triage_thresh");
      if(el) el.value = "0.90";
      setTimeout(updateTriagePills, 0);
    });
  }
  // recalc triage on interactions
  const ids = ["calc_dx","age","stage","apoe","modA","catA","lrA_pos","lrA_neg","useB","modB","catB","lrB_pos","lrB_neg"];
  ids.forEach(id=>{
    const el = document.getElementById(id);
    if(el){
      el.addEventListener("click", ()=>setTimeout(updateTriagePills,0));
      el.addEventListener("change", ()=>setTimeout(updateTriagePills,0));
      el.addEventListener("input", ()=>setTimeout(updateTriagePills,0));
    }
  });
  // initial pass
  setTimeout(updateTriagePills, 200);
});
"""

open(app,'w',encoding='utf-8').write(s)
print("app.js: thresholds + non-invasive triage wired.")

# ---------- bump SW cache so browsers fetch fresh files ----------
swc=open(sw,'r',encoding='utf-8').read()
swc2, n = re.subn(r'amyloid-helper-v\d+', 'amyloid-helper-v107', swc)
if n==0:
    swc2 = re.sub(r'(const\s+CACHE\s*=\s*[\'"])[^\'"]+([\'"])', r'\1amyloid-helper-v107\2', swc, count=1)
open(sw,'w',encoding='utf-8').write(swc2)
print("sw.js: cache bumped to amyloid-helper-v107")
