path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\styles.css"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# Add hero-meta-note style after badge-note
old_badge_note = '.badge-note { color: var(--weak); font-family: var(--mono); font-size: 11px; letter-spacing: .02em; }'
new_badge_note = old_badge_note + '''
.hero-meta-note { color: var(--weak); font-family: var(--mono); font-size: 11px; letter-spacing: .02em; margin-top: 6px; padding-left: 2px; }'''
src = src.replace(old_badge_note, new_badge_note, 1)

# Also make hero-meta items align consistently
old_hero_meta_css = '.hero-meta { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 30px; }'
new_hero_meta_css = '.hero-meta { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 30px; align-items: center; }'
src = src.replace(old_hero_meta_css, new_hero_meta_css, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("styles.css patched OK")
