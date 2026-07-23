# 美国白银进出口数据整理

> 整理日期：2026-07-23  
> **表达基准：净进口 = 进口 − 出口（正值 = 净流入美国）**  
> 主序列：**USGS 银含量**（Mineral Commodity Summaries / Historical Statistics）

## 1. 主序列（USGS，吨银含量）

| 年 | 进口 | 出口 | 净进口 | 备注 |
|---:|---:|---:|---:|---|
| 2015 | 5,930 | 817 | 5,113.0 | USGS hist |
| 2016 | 6,160 | 289 | 5,871.0 | USGS hist |
| 2017 | 5,040 | 157 | 4,883.0 | USGS hist |
| 2018 | 4,840 | 604 | 4,236.0 | USGS hist |
| 2019 | 4,760 | 220 | 4,540.0 | USGS hist |
| 2020 | 6,730 | 141 | 6,589.0 | USGS MCS |
| 2021 | 6,160 | 137 | 6,023.0 | USGS MCS |
| 2022 | 4,490 | 276 | 4,214.0 | USGS MCS revised |
| 2023 | 4,950 | 73 | 4,877.0 | USGS MCS revised |
| 2024 | 4,430 | 113 | 4,317.0 | USGS MCS 2026 |
| 2025 | 7,600 | 300 | 7,300.0 | USGS MCS 2026 estimate e |

- 美国长期**净进口**；净进口依赖度近年约表观消费的 60–80%。
- 进口主源：墨西哥（约 44–50%）、加拿大（约 17–29%）等。
- 2025 初估进口跳升至约 **7,600 吨**（关税/EFP 担忧下 CME 入库等因素，见 WSS 2026）。

## 2. 交叉验证

### Comtrade HS7106 毛重（吨）
| 年 | 进口 | 出口 | 净进口 |
|---:|---:|---:|---:|
| 2020 | 8,918.5 | 2,622.0 | 6,296.5 |
| 2021 | 8,216.3 | 3,236.2 | 4,980.1 |
| 2022 | 7,389.0 | 2,333.6 | 5,055.4 |
| 2023 | 7,740.0 | 1,730.8 | 6,009.2 |
| 2024 | 5,812.8 | 1,464.4 | 4,348.4 |

### WSS 金条 2024
- 进口 4,636 吨（−12%，15 年低点）；出口 445 吨（−34%）

## 3. 一手源
- USGS Silver：https://www.usgs.gov/centers/national-minerals-information-center/silver-statistics-and-information
- MCS 2026 PDF：https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-silver.pdf
- Historical ds140：USGS Data Series 140 silver xlsx
- Census / USITC DataWeb（HS/HTS 明细）
- WSS 2025/2026（Metals Focus）

## 4. 文件
- `data/us/us_silver_trade_compiled.csv`
- `web/public/data/us_trade.json`
