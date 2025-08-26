import re, time, shutil, os

fn = "app.js"
src = open(fn,"r",encoding="utf-8").read()
bak = f"{fn}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
shutil.copy2(fn,bak)

# Replace TEST_LIBRARY block (or create if missing)
# We try to find: const TEST_LIBRARY = { ... };
m = re.search(r'const\s+TEST_LIBRARY\s*=\s*\{', src)
if m:
    # find the end of the object by brace matching
    i = m.end()-1
    depth = 1
    j = i
    while j < len(src) and depth>0:
        j+=1
        if src[j] == '{': depth+=1
        elif src[j] == '}': depth-=1
    # include trailing semicolon if present
    end = j+1
    if end < len(src) and src[end] == ';':
        end+=1
    prefix = src[:m.start()]
    suffix = src[end:]
else:
    # No TEST_LIBRARY found; insert near top after first line
    prefix = src
    suffix = ""
    
test_lib = r"""
const TEST_LIBRARY = {
  // PET (visual), referenced to autopsy (used for PET rule and PET-layer prior mapping)
  "amyloid_pet": {
    label: "Amyloid PET (visual; ref autopsy)",
    ref: "autopsy",
    se: 0.92, sp: 0.90,
    defaults: { pos: 9.20, indet: 1.00, neg: 0.089 } // LR+≈Se/(1-Sp), LR-≈(1-Se)/Sp
  },

  // CSF assays (referenced to PET)
  "csf_abeta42_40_lumipulse": {
    label: "CSF Aβ42/40 (Lumipulse; ref PET)",
    ref: "PET",
    se: 0.92, sp: 0.93,
    defaults: { pos: 13.14, indet: 1.00, neg: 0.086 } // LR+≈0.92/0.07, LR-≈0.08/0.93
  },
  "csf_ptau181_abeta42_elecsys": {
    label: "CSF p-tau181/Aβ42 (Elecsys; ref PET)",
    ref: "PET",
    se: 0.91, sp: 0.89,
    defaults: { pos: 8.27, indet: 1.00, neg: 0.101 } // LR+≈0.91/0.11, LR-≈0.09/0.89
  },

  // Plasma assays (referenced to PET; tune per specific platform if needed)
  "plasma_abeta42_40_generic": {
    label: "Plasma Aβ42/40 (generic; ref PET)",
    ref: "PET",
    se: 0.85, sp: 0.85,
    defaults: { pos: 5.67, indet: 1.00, neg: 0.176 } // LR+≈0.85/0.15, LR-≈0.15/0.85
  },
  "plasma_ptau217_generic": {
    label: "Plasma p-tau217 (generic; ref PET)",
    ref: "PET",
    se: 0.92, sp: 0.94,
    defaults: { pos: 15.33, indet: 1.00, neg: 0.085 } // illustrative strong defaults (AUC~0.95-0.98 cohorts)
  },
  "plasma_ptau217_abeta42_lumipulse": {
    label: "Plasma p-tau217/Aβ42 (Lumipulse; ref PET/CSF mixed)",
    ref: "mixed",
    // mixed reference in FDA summary; provide conservative defaults
    se: 0.96, sp: 0.92,
    defaults: { pos: 12.00, indet: 1.00, neg: 0.043 }
  }
};
"""

# If TEST_LIBRARY existed, swap it; else append near top
if m:
    new_src = prefix + test_lib + suffix
else:
    new_src = test_lib + "\n" + prefix + suffix

# Ensure UI uses these defaults when a test is selected (apply on A/B changes if not already)
# We gently patch or add an applyDefaults function and wire it to change events.
if "function applyDefaultsFor(prefix)" not in new_src:
    new_src += r"""
// Apply defaults from TEST_LIBRARY into the LR inputs
function applyDefaultsFor(prefix){
  const modSel = document.getElementById(prefix==="A" ? "modA" : "modB");
  const mod = modSel?.value;
  const t = TEST_LIBRARY[mod];
  if(!t) return;
  const p = prefix;
  const pos = document.getElementById(p==="A" ? "lrA_pos" : "lrB_pos");
  const ind = document.getElementById(p==="A" ? "lrA_indet" : "lrB_indet");
  const neg = document.getElementById(p==="A" ? "lrA_neg" : "lrB_neg");
  if(pos) pos.value = (t.defaults?.pos ?? pos.value);
  if(ind) ind.value = (t.defaults?.indet ?? ind.value);
  if(neg) neg.value = (t.defaults?.neg ?? neg.value);
  // annotate reference under the selector if there is a spot
  const tag = document.getElementById(p==="A" ? "modA_ref" : "modB_ref");
  if(tag) tag.textContent = t.ref ? `ref: ${t.ref}` : "";
}

// Hook up change listeners if present elements exist
window.addEventListener("load", ()=>{
  const a = document.getElementById("modA");
  const b = document.getElementById("modB");
  if(a){ a.addEventListener("change", ()=>applyDefaultsFor("A")); applyDefaultsFor("A"); }
  if(b){ b.addEventListener("change", ()=>applyDefaultsFor("B")); }
});
"""

open(fn,"w",encoding="utf-8").write(new_src)
print(f"Patched TEST_LIBRARY defaults and added applyDefaultsFor() if missing (backup: {bak})")
