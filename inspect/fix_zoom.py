import re

# ============ 1. Fix dataZoom: remove startValue from ALL components ============

# Daily.tsx
path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Daily.tsx"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()
# Remove all startValue from dataZoom
src = re.sub(r',\s*startValue:\s*Math\.max\(0,\s*[^)]+\)', '', src)
with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Daily.tsx: removed startValue")

# Market.tsx
path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Market.tsx"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()
src = re.sub(r',\s*startValue:\s*Math\.max\(0,\s*[^)]+\)', '', src)
with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Market.tsx: removed startValue")

# Positions.tsx
path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Positions.tsx"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()
src = re.sub(r',\s*startValue:\s*Math\.max\(0,\s*[^)]+\)', '', src)
with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Positions.tsx: removed startValue")

print("\nAll startValue removed from dataZoom configs")
