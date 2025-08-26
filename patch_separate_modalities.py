import re, time, shutil, os

TS = time.strftime('%Y%m%d-%H%M%S')

def backup(p):
    if os.path.exists(p):
        shutil.copy2(p, f"{p}.bak-{TS}")

def replace_test_library(js):
    # Find existing TEST_LIBRARY object (if any) and replace it wholesale
    m = re.search(r'const\s+TEST_LIBRARY\s*=\s*\{', js)
    if not m:
        # insert near top if missing
        insert_at = 0
        prefix, suffix = js[:insert_at], js[insert_at:]
    else:
        i = m.end()-1
        depth = 1
        j = i
        while j < len(js) and depth > 0:
            j += 1
            if js[j] == '{': depth += 1
            elif js[j] == '}': depth -= 1
        end = j+1
        if end < len(js) and js[end] == ';': end += 1
        prefix, suffix = js[:m.start()], js[end:]

    test_lib = r"""
const TEST_LIBRARY = {
  // Imaging
  "amyloid_pet": {
    label: "Amyloid PET (visual; ref autopsy)",
    ref: "autopsy",
    se: 0.92, sp: 0.90,
    defaults: { pos: 9.20, indet: 1.00, neg: 0.089 }
  },

  // CSF (PET-referenced)
  "csf_abeta42_40_lumipulse": {
    label: "CSF Aβ42/40 (Lumipulse; ref PET)",
    ref: "PET",
    se: 0.92, sp: 0.93,
    defaults: { pos: 13.14, indet: 1.00, neg: 0.086 }
  },
  "csf_ptau181_abeta42_elecsys": {
    label: "CSF p-tau181/Aβ42 (Elecsys; ref PET)",
    ref: "PET",
    se: 0.91, sp: 0.89,
    defaults: { pos: 8.27, indet: 1.00, neg: 0.101 }
  },

  // Plasma (PET-referenced)
  "plasma_abeta42_40_generic": {
    label: "Plasma Aβ42/40 (generic; ref PET)",
    ref: "PET",
    se: 0.85, sp: 0.85,
    defaults: { pos: 5.67, indet: 1.00, neg: 0.176 }
  },
  "plasma_ptau217_generic": {
    label: "Plasma p-tau217 (generic; ref PET)",
    ref: "PET",
    se: 0.92, sp: 0.94,
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
    js2 = prefix + test_lib + suffix

    # Ensure defaults are applied when a modality is selected
    if "function applyDefaultsFor(prefix)" not in js2:
        js2 += r"""
// Apply library defaults into LR inputs when modality changes
function applyDefaultsFor(prefix){
  const modSel = document.getElementById(prefix==="A" ? "modA" : "modB");
  const mod = modSel?.value;
  const t = TEST_LIBRARY[mod];
  if(!t) return;
  const pos = document.getElementById(prefix==="A" ? "lrA_pos" : "lrB_pos");
  const ind = document.getElementById(prefix==="A" ? "lrA_indet" : "lrB_indet");
  const neg = document.getElementById(prefix==="A" ? "lrA_neg" : "lrB_neg");
  if(pos && t.defaults?.pos != null) pos.value = t.defaults.pos;
  if(ind && t.defaults?.indet != null) ind.value = t.defaults.indet;
  if(neg && t.defaults?.neg != null) neg.value = t.defaults.neg;
  const tag = document.getElementById(prefix==="A" ? "modA_ref" : "modB_ref");
  if(tag) tag.textContent = t.ref ? `ref: ${t.ref}` : "";
}
window.addEventListener("load", ()=>{
  const a = document.getElementById("modA");
  const b = document.getElementById("modB");
  if(a){ a.addEventListener("change", ()=>applyDefaultsFor("A")); applyDefaultsFor("A"); }
  if(b){ b.addEventListener("change", ()=>applyDefaultsFor("B")); }
});
"""
    return js2

def replace_select_block(html, select_id):
    # Replace the inner options of <select id="...">...</select> with grouped options
    m = re.search(rf'(<select[^>]*\bid="{re.escape(select_id)}"[^>]*>)', html)
    if not m: return html, False
    start_tag_end = html.find('>', m.start()) + 1
    end_sel = html.find('</select>', start_tag_end)
    if end_sel == -1: return html, False
    new_inner = """
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
    html2 = html[:start_tag_end] + "\n" + new_inner + "\n" + html[end_sel:]
    return html2, True

# Paths
app = "app.js"
idx = "index.html"
sw  = "sw.js"

# Backups
for p in (app, idx, sw):
    if os.path.exists(p): backup(p)

# Patch app.js
with open(app, "r", encoding="utf-8") as f:
    js = f.read()
js2 = replace_test_library(js)
with open(app, "w", encoding="utf-8") as f:
    f.write(js2)
print("Patched app.js TEST_LIBRARY (separate CSF vs Plasma modalities).")

# Patch index.html selects for modA / modB
if os.path.exists(idx):
    with open(idx, "r", encoding="utf-8") as f:
        html = f.read()
    changed_any = False
    for sel in ("modA", "modB"):
        html, changed = replace_select_block(html, sel)
        changed_any = changed_any or changed
    if changed_any:
        with open(idx, "w", encoding="utf-8") as f:
            f.write(html)
        print("Updated index.html selects with Imaging/CSF/Plasma groups.")
    else:
        print("Note: Could not find <select id=\"modA/modB\"> blocks; UI menu not changed.")
else:
    print("index.html not found; skipping menu update.")

# Bump Service Worker cache so browsers reload
if os.path.exists(sw):
    swc = open(sw, "r", encoding="utf-8").read()
    swc2, n = re.subn(r'amyloid-helper-v\d+', 'amyloid-helper-v12', swc)
    if n == 0:
        swc2 = re.sub(r"(const CACHE=)['\"][^'\"]+(['\"])", r"\\1amyloid-helper-v12\\2", swc, count=1)
    open(sw, "w", encoding="utf-8").write(swc2)
    print("Bumped Service Worker cache to amyloid-helper-v12.")
else:
    print("sw.js not found; skipped SW bump.")
