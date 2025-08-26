import re, os, time, shutil
TS = time.strftime('%Y%m%d-%H%M%S')
def backup(p): 
    if os.path.exists(p): shutil.copy2(p, f"{p}.bak-"+TS)

idx, app, sw = "index.html", "app.js", "sw.js"
for p in (idx, app, sw):
    if os.path.exists(p): backup(p)

# 1) index.html — remove any nav button containing "Harmon" and any <section> whose id/name contains "harmon" or "bridge"
s = open(idx, "r", encoding="utf-8").read()

# Remove nav buttons that show the tab
s = re.sub(r'<button[^>]*>[^<]*Harmon[^<]*</button>\s*', '', s, flags=re.I)

# Remove the Harmonize/Bridge panel sections
def drop_panels(html, key):
    return re.sub(rf'<section[^>]*?(id|class)[^>]*?{key}[^>]*>.*?</section>\s*',
                  '', html, flags=re.I|re.S)
for key in ("harmon", "bridge"):
    s = drop_panels(s, key)

open(idx, "w", encoding="utf-8").write(s)
print("index.html: removed Harmonize/Bridge tab & panel(s).")

# 2) app.js — (optional) strip legacy helper block comment header so it’s clear it’s unused
try:
    js = open(app, "r", encoding="utf-8").read()
    js = js.replace("/* --- Legacy helpers kept for the Harmonize Tools tab (do not use on Diagnostic) --- */",
                    "/* (Legacy helpers retained; Harmonize tab removed) */")
    open(app, "w", encoding="utf-8").write(js)
    print("app.js: marked legacy helpers as unused.")
except FileNotFoundError:
    pass

# 3) bump SW cache so clients reload
try:
    swc = open(sw, "r", encoding="utf-8").read()
    import re
    swc2, n = re.subn(r'amyloid-helper-v\d+', 'amyloid-helper-v14', swc)
    if n == 0:
        swc2 = re.sub(r"(const CACHE=)['\"][^'\"]+(['\"])", r"\1amyloid-helper-v14\2", swc, count=1)
    open(sw, "w", encoding="utf-8").write(swc2)
    print("sw.js: bumped cache to amyloid-helper-v14.")
except FileNotFoundError:
    pass
