import os, re, time, shutil

ts = time.strftime('%Y%m%d-%H%M%S')
idx = 'index.html'
app = 'app.js'
sw  = 'sw.js'

def backup(p):
    if os.path.exists(p):
        shutil.copy2(p, f"{p}.bak-{ts}")

def sub_file(path, patterns):
    with open(path, 'r', encoding='utf-8') as f:
        s = f.read()
    orig = s
    for pat, repl, flags in patterns:
        s = re.sub(pat, repl, s, flags=flags)
    if s != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(s)
        return True
    return False

# --- Backups ---
for p in (idx, app, sw):
    if os.path.exists(p): backup(p)

# --- index.html: rename result headers to make the layers explicit ---
idx_changed = sub_file(idx, [
    # PET layer cards (top numbers)
    (r'(<h3 class="h">)\s*Posterior after Test A\s*\(as-entered\)\s*(</h3>)',
     r'\1PET layer after Test A — P(PET+)\2', re.M),
    (r'(<h3 class="h">)\s*Posterior after Test A → Test B\s*\(as-entered\)\s*(</h3>)',
     r'\1PET layer after Test A → Test B — P(PET+)\2', re.M),

    # Autopsy layer cards (bottom panel)
    (r'(<h3 class="h">)\s*Autopsy-anchored posterior after Test A\s*(</h3>)',
     r'\1Autopsy layer after Test A — Posterior P(autopsy A+)\2', re.M),
    (r'(<h3 class="h">)\s*Autopsy-anchored posterior after Test A → Test B\s*(</h3>)',
     r'\1Autopsy layer after Test A → Test B — Posterior P(autopsy A+)\2', re.M),
])

# --- app.js: make chip text refer to PET explicitly (not generic Aβ) ---
app_changed = sub_file(app, [
    (r'High probability of Aβ positivity', r'High likelihood of PET positivity', re.M),
    (r'Likely Aβ positivity',              r'Likely PET positivity',            re.M),
    (r'Likely Aβ negative',                r'Likely PET negative',              re.M),
])

# --- bump Service Worker cache so browsers reload ---
sw_changed = False
if os.path.exists(sw):
    sw_changed = sub_file(sw, [
        (r'amyloid-helper-v\d+', r'amyloid-helper-v10', re.M),
        (r'(const CACHE=)[\'"][^\'"]+[\'"]', r"\1'amyloid-helper-v10'", re.M),
    ])

print("Patched:", {
    'index.html': idx_changed,
    'app.js': app_changed,
    'sw.js bumped': sw_changed
})
