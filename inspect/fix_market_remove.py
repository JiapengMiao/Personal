path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Market.tsx"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find line numbers for DomesticStocksPanel, OverseasStocksPanel, StockLines
start_remove = None
end_remove = None
for i, line in enumerate(lines):
    if "function DomesticStocksPanel" in line and start_remove is None:
        start_remove = i
    if "function FundPanel" in line:
        end_remove = i
        break

print(f"Removing lines {start_remove+1} to {end_remove} (DomesticStocksPanel + OverseasStocksPanel + StockLines)")

if start_remove is not None and end_remove is not None:
    # Remove the blank line before DomesticStocksPanel too
    if start_remove > 0 and lines[start_remove-1].strip() == "":
        start_remove -= 1
    new_lines = lines[:start_remove] + ["\n"] + lines[end_remove:]
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"Removed {end_remove - start_remove} lines")
else:
    print(f"ERROR: start={start_remove}, end={end_remove}")
