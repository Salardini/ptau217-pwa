
#!/usr/bin/env python3
"""
patch_ptau217_app_v2.py

Adds three robust changes:
  (A) Service Worker: safe fetch handler + install/activate with skipWaiting/clients.claim
      and forces a unique CACHE name suffix to bust the cache.
  (B) Injects an "Autopsy-Anchored Methods & Sources" HTML section.
  (C) Bumps the on-page "Version:" text to 2025-08-25-v742 (if present).

Usage:
  python patch_ptau217_app_v2.py --root /path/to/repo
"""
import argparse, re, sys, time
from pathlib import Path

CACHE_SUFFIX = "20250825201742"
SW_PROLOGUE = """
// ===== BEGIN: SW lifecycle helpers (injected) =====
self.addEventListener('install', (event) => {{
  try {{ self.skipWaiting(); }} catch(e) {{ /* noop */ }}
}});
self.addEventListener('activate', (event) => {{
  try {{ event.waitUntil((async () => {{ await self.clients.claim(); }})()); }} catch(e) {{ /* noop */ }}
}});
// ===== END: SW lifecycle helpers (injected) =====
"""

SW_FETCH = """
// ===== BEGIN: Safe fetch handler (injected) =====
const __CACHE_SUFFIX = '20250825201742';
const __CACHE_FALLBACK = 'ptau217-cache-v1-' + __CACHE_SUFFIX;
self.addEventListener('fetch', function(event) {{
  try {{
    const url = new URL(event.request.url);
    const isHTTP = (url.protocol === 'http:' || url.protocol === 'https:');
    const sameOrigin = (url.origin === self.origin || url.origin === self.location.origin);
    if (event.request.method !== 'GET' || !isHTTP || !sameOrigin) {{
      return; // avoid chrome-extension:// and cross-origin
    }}
    event.respondWith(
      caches.match(event.request).then(function(resp) {{
        if (resp) return resp;
        return fetch(event.request).then(function(networkResp) {{
          try {{
            const copy = networkResp.clone();
            const CACHE_NAME = (typeof CACHE !== 'undefined' && CACHE) ? (CACHE + '-' + __CACHE_SUFFIX) : __CACHE_FALLBACK;
            caches.open(CACHE_NAME).then(function(cache) {{ cache.put(event.request, copy); }});
          }} catch (e) {{ /* noop */ }}
          return networkResp;
        }});
      }})
    );
  }} catch (e) {{ /* noop */ }}
}});
// ===== END: Safe fetch handler (injected) =====
"""

SECTION_HTML = r"""
<!-- ===== BEGIN: Autopsy-Anchored Methods & Sources (injected) ===== -->
<section id="autopsy-anchored-sources" style="margin:2rem 0; padding:1rem; border:1px solid #ddd; border-radius:12px;">
  <h2 style="margin-top:0;">Autopsy‑Anchored Posterior: Methods & Sources</h2>
  <details open>
    <summary><strong>Method note (click to toggle)</strong></summary>
    <p style="margin-top:0.5rem;">
      We compute post‑test probabilities via Bayes in odds form using clinical priors (age, stage, ± APOE) and biomarker‑specific likelihood ratios (LRs) typically reported against in‑life references (Aβ‑PET or CSF). We then recalibrate from PET/CSF‑referenced log‑odds to an <em>autopsy‑anchored</em> posterior probability using published PET⇄autopsy performance (sensitivity/specificity) as a bridging step. 
      <br><em>Assumption:</em> conditional independence of the Test and PET given autopsy status. When biomarkers are correlated, reduce the LR magnitude accordingly or use dependence‑aware fusion.
    </p>
  </details>
  <details>
    <summary><strong>Key sources (click to toggle)</strong></summary>
    <ul style="line-height:1.4; margin-top:0.5rem;">
      <li><strong>PET vs autopsy (ground truth):</strong>
        <ul>
          <li>Clark CM, et al. <em>Lancet Neurol</em>. 2012;11(8):669‑678. (Florbetapir vs autopsy)</li>
          <li>Clark CM, et al. <em>JAMA</em>. 2011;305(3):275‑283. (Use of florbetapir PET)</li>
          <li>Sabri O, et al. <em>Alzheimer’s Dement</em>. 2015;11(8):964‑974. (Florbetaben Phase 3)</li>
        </ul>
      </li>
      <li><strong>CSF biomarkers vs PET (cross‑platform):</strong>
        <ul>
          <li>Leuzy A, et al. <em>Alzheimer’s Dement</em>. 2023.</li>
          <li>Keshavan A, et al. <em>Alz Res Ther</em>. 2020;12:170.</li>
          <li>Elecsys p‑tau181/Aβ42 ratio — 2025 report.</li>
        </ul>
      </li>
      <li><strong>Plasma Aβ42/40 vs PET:</strong>
        <ul>
          <li>Doecke JD, et al. <em>Neurology</em>. 2020;94(24):e2402‑e2412.</li>
          <li>Schindler SE, et al. <em>Neurology</em>. 2019;93(17):e1647‑e1659.</li>
          <li>Cheng L, et al. <em>Front Aging Neurosci</em>. 2022.</li>
          <li>Figdore DJ, et al. 2024.</li>
        </ul>
      </li>
      <li><strong>Plasma p‑tau (p‑tau217 / p‑tau181) vs PET/tau‑PET:</strong>
        <ul>
          <li>Palmqvist S, et al. <em>JAMA</em>. 2020;324(8):772‑781.</li>
          <li>Ashton NJ, et al. <em>JAMA Neurol</em>. 2024.</li>
          <li>Barthélemy NR, et al. <em>Nat Med</em>. 2024.</li>
        </ul>
      </li>
      <li><strong>Commercial panels (APS / PrecivityAD):</strong>
        <ul>
          <li>Kirmess KM, et al. <em>Diagnostics</em>. 2021;11(6):1021.</li>
          <li>Meyer MR, et al. <em>Alzheimer’s Dement</em>. 2024;20(5):3179‑3192.</li>
        </ul>
      </li>
    </ul>
    <p style="font-size:0.95em;color:#555;">Defaults are illustrative; edit LR/priors per your lab/platform.</p>
  </details>
</section>
<!-- ===== END: Autopsy-Anchored Methods & Sources (injected) ===== -->
"""

def backup_file(path: Path):
  bak = path.with_suffix(path.suffix + ".bak." + str(int(time.time())))
  bak.write_bytes(path.read_bytes())
  return str(bak)

def patch_sw(sw_path: Path):
  txt = sw_path.read_text(encoding='utf-8', errors='ignore')
  backed = False
  if "SW lifecycle helpers (injected)" not in txt:
    if not backed: backup_file(sw_path); backed=True
    txt += "\\n" + SW_PROLOGUE
  import re
  pattern = re.compile(r"(self\\.addEventListener\\(['\\\"]fetch['\\\"].*?\\}\\);)", re.S)
  if pattern.search(txt):
    if not backed: backup_file(sw_path); backed=True
    txt = pattern.sub(SW_FETCH, txt, count=1)
  else:
    if not backed: backup_file(sw_path); backed=True
    txt += "\\n" + SW_FETCH
  sw_path.write_text(txt, encoding='utf-8')
  return f"Patched SW: {{sw_path}}" 

def inject_html(html_path: Path):
  h = html_path.read_text(encoding='utf-8', errors='ignore')
  if 'id="autopsy-anchored-sources"' in h:
    return f"Section already present in {{html_path.name}}"
  lo = h.lower()
  idx = lo.rfind("</body>")
  bak = backup_file(html_path)
  if idx != -1:
    new = h[:idx] + SECTION_HTML + h[idx:]
  else:
    new = h + "\\n" + SECTION_HTML
  html_path.write_text(new, encoding='utf-8')
  return f"Injected Methods & Sources into {{html_path.name}} (backup: {{bak}})"

def bump_version_any_html(root: Path):
  hits = 0
  for p in list(root.rglob("*.html")) + list(root.rglob("*.md")) + list(root.rglob("*.txt")):
    t = p.read_text(encoding='utf-8', errors='ignore')
    new = re.sub(r"(Version:\\s*)([^<\\n]+)", r"\\12025-08-25-v742", t, flags=re.I)
    if new != t:
      backup_file(p)
      p.write_text(new, encoding='utf-8')
      hits += 1
  return f"Bumped Version: {{hits}} file(s) updated."

def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--root", type=str, default=".", help="repo root")
  args = ap.parse_args()
  root = Path(args.root).resolve()
  logs = []
  # SW files
  sws = [p for p in root.rglob("sw.js")] + [p for p in root.rglob("service-worker.js")]
  if not sws:
    logs.append("No service worker found.")
  else:
    for sw in sws[:2]:
      logs.append(patch_sw(sw))
  # HTML
  htmls = [root / "index.html", root / "public/index.html", root / "src/index.html", root / "www/index.html"]
  htmls = [p for p in htmls if p.exists()] or [p for p in root.rglob("*.html")[:1]]
  if htmls:
    logs.append(inject_html(htmls[0]))
  else:
    logs.append("No HTML to inject section.")
  # Version bump
  logs.append(bump_version_any_html(root))
  print("\\n".join(logs))

if __name__ == "__main__":
  main()
