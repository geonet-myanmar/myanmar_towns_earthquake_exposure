# Myanmar Earthquake Hazard Exposure Analysis

## Data and downloads
- Earthquakes: USGS FDSN event API (1900-01-01 to 2026-02-25), filtered to Myanmar boundary.
- Towns: MIMU Town Points PCode v9.4 (GeoJSON via HDX resource endpoint).
- Earthquake records in Myanmar: 2844
- Town points analyzed: 494

## Methodology
1. Download Myanmar boundary and compute country bounding box.
2. Query all available USGS earthquake events from 1900-01-01 to today in that bounding box.
3. Apply point-in-polygon filtering so only events inside Myanmar national boundary are retained.
4. Download Myanmar town points and calculate, per town: nearest event distance, number of events within 50 km and 100 km, and local magnitude metrics within 100 km.
5. Build a composite hazard exposure score (0 to 1 after normalization) using weighted factors: proximity risk (30%), event frequency within 100 km (35%), maximum local magnitude within 100 km (20%), and magnitude-distance index (15%).
6. Classify town scores into Low, Moderate, High, and Very High exposure classes using quartile-like equal-interval bins over the observed score range.

## Results
- Very High exposure towns: 14
- High exposure towns: 48
- Moderate exposure towns: 313
- Low exposure towns: 119

### Top 20 most exposed towns
| Rank | Town | Township | Score | Nearest EQ (km) | EQ <=100 km | Max Mag <=100 km |
|---:|---|---|---:|---:|---:|---:|
| 1 | Shwe Pyi Aye | Homalin | 0.8171 | 0.85 | 496 | 7.30 |
| 2 | Kale | Kale | 0.8153 | 1.31 | 588 | 7.02 |
| 3 | Mingin | Mingin | 0.7657 | 2.31 | 561 | 7.02 |
| 4 | Mawlaik | Mawlaik | 0.7655 | 2.18 | 586 | 6.90 |
| 5 | Kalewa | Kalewa | 0.7406 | 5.17 | 619 | 7.02 |
| 6 | Khaikam | Tedim | 0.7187 | 3.28 | 575 | 7.02 |
| 7 | Paungbyin | Paungbyin | 0.7019 | 3.41 | 535 | 7.07 |
| 8 | Webula | Falam | 0.6995 | 3.11 | 549 | 7.02 |
| 9 | Kyaw | Gangaw | 0.6940 | 0.48 | 321 | 7.02 |
| 10 | Myothit | Tamu | 0.6586 | 4.14 | 491 | 7.30 |
| 11 | Homalin | Homalin | 0.6499 | 4.66 | 478 | 7.30 |
| 12 | Gangaw | Gangaw | 0.6434 | 1.39 | 399 | 7.02 |
| 13 | Khampat | Tamu | 0.6382 | 4.36 | 529 | 6.34 |
| 14 | Mo Waing Lut | Homalin | 0.6172 | 4.12 | 426 | 7.30 |
| 15 | Pinlebu | Pinlebu | 0.5820 | 5.78 | 465 | 7.64 |
| 16 | Hakha | Hakha | 0.5812 | 1.87 | 352 | 7.02 |
| 17 | Tamu | Tamu | 0.5710 | 6.28 | 467 | 6.20 |
| 18 | Shwebo | Shwebo | 0.5619 | 0.75 | 167 | 7.70 |
| 19 | Hkamti | Hkamti | 0.5413 | 1.06 | 216 | 7.00 |
| 20 | Falam | Falam | 0.5362 | 10.32 | 431 | 7.02 |

## Output files
- myanmar_earthquakes_usgs.geojson
- myanmar_towns.geojson
- myanmar_town_earthquake_exposure.geojson
- myanmar_earthquake_hazard_report.md
