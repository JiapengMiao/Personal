#!/usr/bin/env python3
"""Generate US/UK/India comparison chart using existing uk_trade.json."""
import json
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT_PNG = ROOT / "output" / "us_uk_india_silver_trade_preview.png"

C = {"bg":"#0a101b","panel":"#0e1524","raised":"#121a2b","hairline":"#1c2a3d",
     "text":"#e8eef6","sub":"#9fb0c3","weak":"#64748b","imp":"#56c8dc","exp":"#8a9bb5",
     "net":"#d9a441","us":"#56c8dc","uk":"#d9a441","in":"#f26d6d","event":"#f26d6d"}

US_USGS = {2015:(5930,817),2016:(6160,289),2017:(5040,157),2018:(4840,604),2019:(4760,220),
           2020:(6730,141),2021:(6160,137),2022:(4490,276),2023:(4950,73),2024:(4430,113),2025:(7600,300)}
IN_IMP={2015:8093,2016:3000,2017:5133,2018:6942,2019:5969,2020:2218,2021:2773,2022:9450,2023:3574,2024:7695,2025:7222}
IN_EXP={2020:217.9,2021:440.0,2022:94.7,2023:170.4,2024:524.9,2025:130.8}

def main():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei","SimHei","Arial Unicode MS","DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    uk = json.loads((ROOT/"web/public/data/uk_trade.json").read_text("utf-8"))
    us_y = sorted(US_USGS); us_imp=[US_USGS[y][0] for y in us_y]; us_exp=[US_USGS[y][1] for y in us_y]; us_net=[a-b for a,b in zip(us_imp,us_exp)]
    uk_y = [int(y) for y in uk["years"]]; uk_imp=uk["imports"]; uk_exp=uk["exports"]; uk_net=uk["netImport"]
    in_y = sorted(IN_IMP); in_imp=[IN_IMP[y] for y in in_y]; in_exp=[IN_EXP.get(y,0) for y in in_y]; in_net=[a-b for a,b in zip(in_imp,in_exp)]

    fig = plt.figure(figsize=(15.2,11.2), facecolor=C["bg"])
    gs = GridSpec(3,3,figure=fig,height_ratios=[0.7,2.2,2.0],hspace=0.42,wspace=0.28,left=0.06,right=0.98,top=0.91,bottom=0.06)
    fig.text(0.06,0.965,"美 / 英 / 印 白银贸易对比 · 净进口口径",color=C["text"],fontsize=16,fontweight="600",va="top")
    fig.text(0.06,0.935,"净进口 = 进口 − 出口（正=净流入）。美=USGS银含量；英=HMRC BDS；印=WSS/Comtrade。口径不同，比趋势不比绝对水平硬加总。",color=C["sub"],fontsize=9.5,va="top")

    top_cards = [
        ("美国 USGS", f"2024 净进口 {us_net[-2]:,.0f} t", f"2025e 进口 {us_imp[-1]:,.0f} t（初估）", C["us"]),
        ("英国 HMRC", f"{uk['asOf']} 净进口 {uk_net[-1]:,.0f} t", f"2025 年度净进口 {sum(1 for r in uk_net if r>0)} 正月", C["uk"]),
        ("印度 消费国", f"2025 净进口 {in_net[-1]:,.0f} t", "2026-05 进口 33 t（加税后）", C["in"]),
    ]
    for i,(t,v1,v2,col) in enumerate(top_cards):
        ax=fig.add_subplot(gs[0,i]); ax.set_facecolor(C["raised"])
        for sp in ax.spines.values(): sp.set_color(C["hairline"])
        ax.set_xticks([]); ax.set_yticks([])
        ax.text(0.06,0.72,t,transform=ax.transAxes,color=C["sub"],fontsize=11,va="center")
        ax.text(0.06,0.40,v1,transform=ax.transAxes,color=col,fontsize=15,fontweight="600",va="center")
        ax.text(0.06,0.14,v2,transform=ax.transAxes,color=C["weak"],fontsize=10,va="center")

    def style(ax):
        ax.set_facecolor(C["panel"]); ax.tick_params(colors=C["sub"],labelsize=8)
        for sp in ax.spines.values(): sp.set_color(C["hairline"])
        ax.yaxis.grid(True,color=C["hairline"],lw=0.8); ax.set_axisbelow(True)

    axn=fig.add_subplot(gs[1,:]); style(axn)
    axn.set_title("三国净进口对比（吨）",color=C["text"],fontsize=12,loc="left",pad=8)
    axn.plot(us_y,us_net,color=C["us"],lw=2.3,marker="o",ms=4.5,label="美国净进口（USGS）")
    axn.plot(uk_y,uk_net,color=C["uk"],lw=2.3,marker="s",ms=4.5,label="英国净进口（HMRC BDS）")
    axn.plot(in_y,in_net,color=C["in"],lw=2.3,marker="^",ms=4.5,label="印度净进口（WSS/Comtrade）")
    axn.axhline(0,color=C["weak"],ls="--",lw=1)
    axn.set_ylabel("吨",color=C["sub"])
    max_yr=max(us_y[-1],uk_y[-1],in_y[-1]); axn.set_xlim(2014.5,max_yr+0.5)
    leg=axn.legend(loc="upper left",fontsize=8,frameon=True,ncol=3)
    leg.get_frame().set_facecolor(C["raised"]); leg.get_frame().set_edgecolor(C["hairline"])
    for t in leg.get_texts(): t.set_color(C["text"])

    ax_us=fig.add_subplot(gs[2,0:2]); style(ax_us)
    ax_us.set_title("美国进出口（USGS 银含量，吨）",color=C["text"],fontsize=11,loc="left",pad=8)
    x=np.arange(len(us_y)); w=0.36
    colors_imp=[C["event"] if y==2025 else C["imp"] for y in us_y]
    ax_us.bar(x-w/2,us_imp,width=w,color=colors_imp,alpha=0.75,label="进口")
    ax_us.bar(x+w/2,us_exp,width=w,color=C["exp"],alpha=0.65,label="出口")
    ax_us.plot(x,us_net,color=C["net"],lw=2,marker="o",ms=4,label="净进口")
    ax_us.set_xticks(x); ax_us.set_xticklabels([f"{y}e" if y==2025 else str(y) for y in us_y],color=C["sub"],fontsize=8)
    ax_us.set_ylabel("吨",color=C["sub"])
    leg=ax_us.legend(loc="upper left",fontsize=8,frameon=True)
    leg.get_frame().set_facecolor(C["raised"]); leg.get_frame().set_edgecolor(C["hairline"])
    for t in leg.get_texts(): t.set_color(C["text"])

    ax_uk=fig.add_subplot(gs[2,2]); style(ax_uk)
    ax_uk.set_title(f"英国进出口（吨）截至 {uk['asOf']}",color=C["text"],fontsize=11,loc="left",pad=8)
    x2=np.arange(len(uk_y))
    ax_uk.bar(x2-w/2,uk_imp,width=w,color=C["imp"],alpha=0.75,label="进口")
    ax_uk.bar(x2+w/2,uk_exp,width=w,color=C["exp"],alpha=0.65,label="出口")
    ax_uk.plot(x2,uk_net,color=C["net"],lw=2,marker="o",ms=3.5,label="净进口")
    ax_uk.axhline(0,color=C["weak"],ls="--",lw=0.8)
    ax_uk.set_xticks(x2); ax_uk.set_xticklabels([str(y)[2:] for y in uk_y],color=C["sub"],fontsize=7)
    ax_uk.set_ylabel("吨",color=C["sub"])
    leg=ax_uk.legend(loc="upper left",fontsize=7,frameon=True)
    leg.get_frame().set_facecolor(C["raised"]); leg.get_frame().set_edgecolor(C["hairline"])
    for t in leg.get_texts(): t.set_color(C["text"])

    fig.text(0.06,0.012,f"口径提示：三国序列来源不同（USGS含量 / 英HMRC BDS / 印WSS），适比趋势不适合硬加总。  生成：{datetime.now().astimezone().isoformat(timespec='seconds')}",color=C["weak"],fontsize=8)
    OUT_PNG.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(OUT_PNG,dpi=160,facecolor=C["bg"]); plt.close(fig)
    print(f"[OK] PNG {OUT_PNG}")

if __name__=="__main__": main()
