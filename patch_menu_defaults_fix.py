import os, re, time, shutil

TS = time.strftime('%Y%m%d-%H%M%S')
def backup(p): 
    if os.path.exists(p): shutil.copy2(p, f"{p}.bak-{TS}")

app = "app.js"
idx = "index.html"
sw  = "sw.js"

for p in (app, idx, sw):
    if os.path.exists(p): backup(p)

# --- Patch app.js TEST_LIBRARY with distinct CSF vs Plasma entries and sane defaults ---
js = open(app, "r", encoding="utf-8").read()

m = re.search(r'const\s+TEST_LIBRARY\s*=\s*\{', js)
if m:
    # replace whole object
    i = m.end()-1; depth=1; j=i
    while j < len(js) and depth>0:
        j+=1
        if js[j] == '{': depth+=1
        elif js[j] == '}': depth-=1
    end = j+1
    if end < len(js) and js[end] == ';': end += 1
    prefix, suffix = js[:m.start()], js[end:]
else:
    prefix, suffix = js, ""

test_lib = r"""
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
"""

new_js = prefix + test_lib + suffix

# ensure defaults get applied on change + on load
if "function applyDefaultsFor(prefix)" not in new_js:
    new_js += r"""
function applyDefaultsFor(prefix){
  const sel = document.getElementById(prefix==="A" ? "modA" : "modB");
  const mod = sel?.value;
  const t = TEST_LIBRARY[mod];
  if(!t) return;
  const pos = document.getElementById(prefix==="A" ? "lrA_pos" : "lrB_pos");
  const ind = document.getElementById(prefix==="A" ? "lrA_indet" : "lrB_indet");
  const neg = document.getElementById(prefix==="A" ? "lrA_neg" : "lrB_neg");
  if(pos && t.defaults?.pos!=null) pos.value = t.defaults.pos;
  if(ind && t.defaults?.indet!=null) ind.value = t.defaults.indet;
  if(neg && t.defaults?.neg!=null) neg.value = t.defaults.neg;
}
window.addEventListener("load", ()=>{
  const a = document.getElementById("modA");
  const b = document.getElementById("modB");
  if(a){ a.addEventListener("change", ()=>applyDefaultsFor("A")); applyDefaultsFor("A"); }
  if(b){ b.addEventListener("change", ()=>applyDefaultsFor("B")); }
});
"""
open(app, "w", encoding="utf-8").write(new_js)
print("Patched app.js TEST_LIBRARY and default-applier.")

# --- Patch index.html selects to include distinct CSF and Plasma options ---
if os.path.exists(idx):
    html = open(idx,"r",encoding="utf-8").read()
    def replace_select(html, sel_id):
        m = re.search(rf'(<select[^>]*\bid="{re.escape(sel_id)}"[^>]*>)', html)
        if not m: return html, False
        start = html.find('>', m.start()) + 1
        end = html.find('</select>', start)
        if end == -1: return html, False
        inner = """
      <optgroup label="Imaging">
        <option value="amyloid_pet">Amyloid PET (visual; ref autopsy)</option>
      </optgroup>
      <optgroup label="CSF">
        <option value="csf_abeta42_40_lumipulse">CSF Aβ42/40 (Lumipulse; ref PET)</option>
        <option value="csf_ptau181_abeta42_elecsys">CSF p-tau181/Aβ42 (Elecsys; ref PET)</option>
      </optgroup>
      <optgroup label="Plasma">
        <option value="plasma_abeta42_40_generic">Plasma Aβ42/40 (generic; ref PET)</option>
        <option value="plasma_ptau217_generic">Plasma p-tau217 (generic; ref PET)</option>
        <option value="plasma_ptau217_abeta42_lumipulse">Plasma p-tau217/Aβ42 (Lumipulse; mixed ref)</option>
      </optgroup>
        """.strip()
        return html[:start] + "\n" + inner + "\n" + html[end:], True

    changed = False
    for sel_id in ("modA","modB"):
        html, ch = replace_select(html, sel_id); changed = changed or ch
    if changed:
        open(idx,"w",encoding="utf-8").write(html)
        print("Updated index.html: modA/modB menus now include distinct CSF & Plasma groups.")
    else:
        print("Warning: could not patch select menus (modA/modB not found).")

# --- bump SW so browsers reload ---
if os.path.exists(sw):
    swc = open(sw,"r",encoding="utf-8").read()
    swc2, n = re.subn(r'amyloid-helper-v\d+', 'amyloid-helper-v13', swc)
    if n == 0:
        swc2 = re.sub(r"(const CACHE=)['\"][^'\"]+(['\"])", r"\1amyloid-helper-v13\2", swc, count=1)
    open(sw,"w",encoding="utf-8").write(swc2)
    print("Bumped Service Worker cache to amyloid-helper-v13.")
