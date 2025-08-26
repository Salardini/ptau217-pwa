
#!/usr/bin/env python3
"""
patch_ptau217_app.py

Purpose:
  Apply "best-effort" patches to a pTau217 PWA-style project:
    1) Service Worker fetch() handler: guard against caching non-http(s) and cross-origin requests
       to avoid "Request scheme 'chrome-extension' is unsupported" errors.
    2) Inject an "Autopsy-Anchored Methods & Sources" <section> near </body> in index.html
       with a succinct method note and a reference list provided by the user.

Usage:
  python patch_ptau217_app.py --root /path/to/your/project

Notes:
  - Backups are created as *.bak.<timestamp> before modifying files.
  - This script aims to be tolerant of different file names and layouts.
  - If it cannot find target patterns, it will append safe defaults instead.
"""

import argparse
import re
import sys
import time
from pathlib import Path

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
          <li>Leuzy A, et al. <em>Alzheimer’s Dement</em>. 2023. (Aβ42/40; Aβ42/p‑tau181 cut‑offs vs PET & ADNC)</li>
          <li>Keshavan A, et al. <em>Alz Res Ther</em>. 2020;12:170. (Lumipulse vs established immunoassays; PET prediction)</li>
          <li>Elecsys p‑tau181/Aβ42 ratio — routine use & PET association (2025 report).</li>
        </ul>
      </li>
      <li><strong>Plasma Aβ42/40 vs PET:</strong>
        <ul>
          <li>Doecke JD, et al. <em>Neurology</em>. 2020;94(24):e2402‑e2412.</li>
          <li>Schindler SE, et al. <em>Neurology</em>. 2019;93(17):e1647‑e1659.</li>
          <li>Cheng L, et al. <em>Front Aging Neurosci</em>. 2022. (Systematic evidence)</li>
          <li>Figdore DJ, et al. 2024. (Lumipulse plasma Aβ42/40 with CSF/PET comparators)</li>
        </ul>
      </li>
      <li><strong>Plasma p‑tau (p‑tau217 / p‑tau181) vs PET/tau‑PET:</strong>
        <ul>
          <li>Palmqvist S, et al. <em>JAMA</em>. 2020;324(8):772‑781.</li>
          <li>Ashton NJ, et al. <em>JAMA Neurol</em>. 2024. (Multicenter)</li>
          <li>Barthélemy NR, et al. <em>Nat Med</em>. 2024. (Head‑to‑head with CSF)</li>
        </ul>
      </li>
      <li><strong>Commercial panels (APS / PrecivityAD):</strong>
        <ul>
          <li>Kirmess KM, et al. <em>Diagnostics</em>. 2021;11(6):1021. (LC‑MS/MS; APS derivation)</li>
          <li>Meyer MR, et al. <em>Alzheimer’s Dement</em>. 2024;20(5):3179‑3192. (PrecivityAD2 validation vs PET)</li>
        </ul>
      </li>
    </ul>
    <p style="font-size:0.95em;color:#555;">Defaults are illustrative; edit LR/priors per your lab/platform.</p>
  </details>
</section>
<!-- ===== END: Autopsy-Anchored Methods & Sources (injected) ===== -->
"""

SW_SAFE_FETCH = r"""
// ===== BEGIN: Safe fetch handler (injected) =====
self.addEventListener('fetch', function(event) {
  try {
    const url = new URL(event.request.url);
    const isHTTP = (url.protocol === 'http:' || url.protocol === 'https:');
    const sameOrigin = (url.origin === self.origin || url.origin === self.location.origin);
    if (event.request.method !== 'GET' || !isHTTP || !sameOrigin) {
      return; // Don't intercept non-GET, non-http(s), or cross-origin (e.g., chrome-extension://)
    }
    event.respondWith(
      caches.match(event.request).then(function(resp) {
        if (resp) return resp;
        return fetch(event.request).then(function(networkResp) {
          try {
            const copy = networkResp.clone();
            // Try to detect an existing cache name; fallback if undefined.
            const CACHE_NAME = (typeof CACHE !== 'undefined' && CACHE) ? CACHE : 'ptau217-cache-v1';
            caches.open(CACHE_NAME).then(function(cache) { cache.put(event.request, copy); });
          } catch (e) {
            // swallow
          }
          return networkResp;
        });
      })
    );
  } catch (e) {
    // noop
  }
});
// ===== END: Safe fetch handler (injected) =====
"""

def backup_file(path: Path):
  ts = time.strftime("%Y%m%d%H%M%S")
  bak = path.with_suffix(path.suffix + f".bak.{ts}")
  bak.write_bytes(path.read_bytes())
  return bak

def patch_service_worker(sw_path: Path) -> str:
  content = sw_path.read_text(encoding='utf-8', errors='ignore')
  report = []
  if re.search(r"addEventListener\(['\"]fetch['\"]", content):
    # Replace any existing fetch listener block heuristically
    # Try to replace from "addEventListener('fetch'" to the matching "});"
    # If multiple, append our safe handler instead.
    try:
      pattern = re.compile(r"(self\.addEventListener\(['\"]fetch['\"].*?\}\);\s*)", re.S)
      if pattern.search(content):
        content_new = pattern.sub(SW_SAFE_FETCH.strip() + "\n", content, count=1)
        if content_new != content:
          backup_file(sw_path)
          sw_path.write_text(content_new, encoding='utf-8')
          report.append(f"Replaced existing fetch handler in {sw_path.name}.")
          return "\n".join(report)
    except re.error:
      pass
    # If replacement failed, append our handler safely
    backup_file(sw_path)
    sw_path.write_text(content + "\n" + SW_SAFE_FETCH, encoding='utf-8')
    report.append(f"Appended safe fetch handler to {sw_path.name} (kept existing code).")
  else:
    # No fetch handler found; append our safe one
    backup_file(sw_path)
    sw_path.write_text(content + "\n" + SW_SAFE_FETCH, encoding='utf-8')
    report.append(f"Added new fetch handler to {sw_path.name}.")
  return "\n".join(report)

def inject_section_into_html(html_path: Path) -> str:
  html = html_path.read_text(encoding='utf-8', errors='ignore')
  report = []
  # Don't double-inject
  if "id=\"autopsy-anchored-sources\"" in html:
    return f"Skipped {html_path.name}: section already present."
  # Try to insert before </body>
  idx = html.lower().rfind("</body>")
  if idx != -1:
    new_html = html[:idx] + SECTION_HTML + html[idx:]
    backup_file(html_path)
    html_path.write_text(new_html, encoding='utf-8')
    report.append(f"Injected Methods & Sources section into {html_path.name}.")
  else:
    # Fallback: append at end
    backup_file(html_path)
    html_path.write_text(html + "\n" + SECTION_HTML, encoding='utf-8')
    report.append(f"Appended Methods & Sources section to {html_path.name} (</body> not found).")
  return "\n".join(report)

def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--root", type=str, default=".", help="Project root containing sw.js/service-worker.js and index.html")
  args = ap.parse_args()
  root = Path(args.root).resolve()
  if not root.exists():
    print(f"Root path not found: {root}", file=sys.stderr)
    sys.exit(2)

  changes = []

  # 1) Patch service worker(s)
  sw_candidates = [
    root / "sw.js",
    root / "service-worker.js",
    root / "public" / "sw.js",
    root / "public" / "service-worker.js",
    root / "src" / "sw.js",
    root / "src" / "service-worker.js",
  ]
  sw_found = [p for p in sw_candidates if p.exists()]
  if not sw_found:
    # Try a heuristic search
    for p in root.rglob("*.js"):
      if p.name.lower() in ("sw.js", "service-worker.js"):
        sw_found.append(p)

  if sw_found:
    for p in sw_found:
      try:
        changes.append(patch_service_worker(p))
      except Exception as e:
        changes.append(f"ERROR patching {p}: {e}")
  else:
    changes.append("No service worker file found (sw.js or service-worker.js). Skipped SW patch.")

  # 2) Inject Methods & Sources into index.html (or other common entry files)
  html_candidates = [
    root / "index.html",
    root / "public" / "index.html",
    root / "src" / "index.html",
    root / "www" / "index.html"
  ]
  html_found = [p for p in html_candidates if p.exists()]
  if not html_found:
    # Heuristic: first *.html under root
    for p in root.rglob("*.html"):
      html_found.append(p)
      break

  if html_found:
    for p in html_found:
      try:
        changes.append(inject_section_into_html(p))
        # Only inject into the first index-like file
        break
      except Exception as e:
        changes.append(f"ERROR injecting HTML section into {p}: {e}")
  else:
    changes.append("No HTML file found to inject Methods & Sources section.")

  # Report
  print("=== Patch summary ===")
  for line in changes:
    print(f"- {line}")
  print("\nDone.")

if __name__ == "__main__":
  main()
