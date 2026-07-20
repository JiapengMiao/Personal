path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Chrome.tsx"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# Replace the hero-meta block: move badge-note outside the badges row
old_hero_meta = '''        <div className="hero-meta">
          <CountBadge label="Ag(T+D) 收盘" target={agtdClose} decimals={0} unit="元/千克" active={inView} />
          <span className="hero-badge-stack">
            <span>
              国内库存 <DomesticCount target={domestic} active={inView} /> 吨
            </span>
            <small className="badge-note">
              上期所 {shfeV === null ? "—" : formatNumber(shfeV, 3)}（{shortMd(shfeD)}）+ 上金所 {sgeV === null ? "—" : formatNumber(sgeV, 3)}（{shortMd(sgeD)}{sgeSuffix}）
            </small>
          </span>
          <CountBadge label="COMEX 库存" target={comex} decimals={1} unit="吨" active={inView} />
          <CountBadge label="金银比" target={ratio} decimals={1} unit="" active={inView} />
        </div>'''

new_hero_meta = '''        <div className="hero-meta">
          <CountBadge label="Ag(T+D) 收盘" target={agtdClose} decimals={0} unit="元/千克" active={inView} />
          <span>
            国内库存 <DomesticCount target={domestic} active={inView} /> 吨
          </span>
          <CountBadge label="COMEX 库存" target={comex} decimals={1} unit="吨" active={inView} />
          <CountBadge label="金银比" target={ratio} decimals={1} unit="" active={inView} />
        </div>
        <div className="hero-meta-note">
          上期所 {shfeV === null ? "—" : formatNumber(shfeV, 3)}（{shortMd(shfeD)}）+ 上金所 {sgeV === null ? "—" : formatNumber(sgeV, 3)}（{shortMd(sgeD)}{sgeSuffix}）
        </div>'''

src = src.replace(old_hero_meta, new_hero_meta, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Chrome.tsx patched OK")
