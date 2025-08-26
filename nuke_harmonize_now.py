import os, re, time, shutil

TS = time.strftime('%Y%m%d-%H%M%S')
def backup(p): 
    if os.path.exists(p): shutil.copy2(p, f"{p}.bak-"+TS)

idx = "index.html"
app = "app.js"
sw  = "sw.js"

for p in (idx, app, sw):
    if os.path.exists(p): backup(p)

# --- index.html: remove any Harmonize buttons and panels (robust) ---
if os.path.exists(idx):
    s = open(idx,"r",encoding="utf-8").read()
    before = s

    # Remove any <button>...</button> that contains 'Harmonize' (case-insensitive)
    s = re.sub(r'<button[^>]*>[^<]*Harmonize[^<]*</button>\s*', '', s, flags=re.I)

    # Remove any <a ...>Harmonize</a> entries (in case nav uses <a>)
    s = re.sub(r'<a[^>]*>[^<]*Harmonize[^<]*</a>\s*', '', s, flags=re.I)

    # Remove entire <section> blocks whose id contains 'harmonize'
    s = re.sub(r'<section[^>]*id=["\'][^"\']*harmonize[^"\']*["\'][^>]*>.*?</section>\s*',
               '', s, flags=re.I|re.S)

    # Remove any leftover list items containing "Harmonize"
    s = re.sub(r'<li[^>]*>.*?Harmonize.*?</li>\s*', '', s, flags=re.I|re.S)

    # Remove inline references like role="tab" elements that contain Harmonize
    s = re.sub(r'<[^>]+Harmonize[^>]*>.*?</[^>]+>\s*', '', s, flags=re.I|re.S)

    if s != before:
        open(idx,"w",encoding="utf-8").write(s)
        print("index.html: Harmonize UI removed.")
    else:
        print("index.html: no Harmonize UI found (nothing to remove).")
else:
    print("index.html not found; skipping.")

# --- app.js: remove legacy bridge helpers if they still exist ---
removed = []
if os.path.exists(app):
    js = open(app,"r",encoding="utf-8").read()

    def drop_func(src, name):
        m = re.search(rf'function\s+{name}\s*\(', src)
        if not m: return src, False
        lb = src.find("{", m.end()-1)
        if lb < 0: return src, False
        depth, i = 1, lb+1
        while i < len(src) and depth>0:
            c = src[i]
            if c == "{": depth += 1
            elif c == "}": depth -= 1
            i += 1
        return (src[:m.start()] + src[i:]), True

    for fn in ("seSpFromLR", "bridgeToAutopsy_fromLR"):
        js, did = drop_func(js, fn)
        if did: removed.append(fn)

    if removed:
        open(app,"w",encoding="utf-8").write(js)
        print("app.js: removed functions:", ", ".join(removed))
    else:
        print("app.js: no legacy bridge helpers found (nothing to remove).")
else:
    print("app.js not found; skipping.")

# --- bump Service Worker cache string to force reload ---
if os.path.exists(sw):
    swc = open(sw,"r",encoding="utf-8").read()
    swc2, n = re.subn(r'amyloid-helper-v\d+', 'amyloid-helper-v99', swc)
    if n == 0:
        # fallback: replace first CACHE assignment
        swc2 = re.sub(r'(const\s+CACHE\s*=\s*[\'"])[^\'"]+([\'"])', r'\1amyloid-helper-v99\2', swc, count=1)
    open(sw,"w",encoding="utf-8").write(swc2)
    print("sw.js: bumped cache to amyloid-helper-v99")
else:
    print("sw.js not found; skipping SW bump.")
