import re, time, shutil, os
TS=time.strftime('%Y%m%d-%H%M%S')

def bak(p):
    if os.path.exists(p):
        shutil.copy2(p, f"{p}.bak-{TS}")

# --- Fix app.js: convert any template string used in .textContent that contains ${...} into safe concat
fn = "app.js"; bak(fn)
src = open(fn,"r",encoding="utf-8").read()

# Convert lines like: el.textContent = `... ${expr} ...`;
# to:                el.textContent = "... " + (expr) + " ...";
pattern = re.compile(r'(document\.getElementById\("[^"]+"\)\.textContent\s*=\s*)`([^`]*?)\$\{([^}]+)\}([^`]*)`', re.S)
changed = 0
while True:
    src2, n = pattern.subn(r'\1"\2" + (\3) + "\4"', src)
    changed += n
    if n == 0: break
    src = src2

# Also, some earlier patches may have left a half-open template specifically for "Posterior ..."
src = re.sub(
    r'document\.getElementById\("post_aut_p1"\)\.textContent\s*=\s*[^;]*;',
    'document.getElementById("post_aut_p1").textContent = "Posterior P(A+) = " + fmtPct(p);',
    src
)
src = re.sub(
    r'document\.getElementById\("post_aut_p2"\)\.textContent\s*=\s*[^;]*;',
    'document.getElementById("post_aut_p2").textContent = "Posterior P(A+) = " + fmtPct(p);',
    src
)

# Quick brace balance check
stack=[]; ok=True
for ch in src:
    if ch=='{': stack.append('{')
    elif ch=='}':
        if not stack: ok=False; break
        stack.pop()
ok = ok and not stack

if not ok:
    print("ERROR: app.js still looks unbalanced after patch. Restoring backup.")
    # restore most recent backup
    for b in sorted([x for x in os.listdir('.') if x.startswith('app.js.bak-')], reverse=True):
        shutil.copy2(b, fn)
        print(f"Restored {fn} from {b}")
        break
else:
    open(fn,"w",encoding="utf-8").write(src)
    print(f"app.js patched ({changed} template line(s) converted). Backup: app.js.bak-{TS}")

# --- Fix sw.js: ignore non-http(s) requests and non-GET; bump cache key
sw = "sw.js"; bak(sw)
s = open(sw,"r",encoding="utf-8").read()

# Insert guards inside fetch handler
if "protocol !== 'http'" not in s:
    s = re.sub(
        r'self\.addEventListener\(\s*[\'"]fetch[\'"]\s*,\s*function?\s*\(\s*e\s*\)\s*\{',
        "self.addEventListener('fetch', function(e){\n  try{\n    const url = new URL(e.request.url);\n    if((url.protocol !== 'http:' && url.protocol !== 'https:') || e.request.method !== 'GET'){ return; }\n  }catch(_) { return; }",
        s, count=1
    )

# Bump cache version string
s = re.sub(r'amyloid-helper-v\d+', 'amyloid-helper-v202', s)
if "amyloid-helper-v202" not in s:
    s = re.sub(r'(const\s+CACHE\s*=\s*[\'"])[^\'"]+([\'"])', r"\1amyloid-helper-v202\2", s, count=1)

open(sw,"w",encoding="utf-8").write(s)
print("sw.js patched (guards added, cache bumped to v202).")
