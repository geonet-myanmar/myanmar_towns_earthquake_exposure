# Myanmar Earthquake Hazard Exposure Analysis

This project downloads historical earthquake records from the USGS Earthquake Catalog for Myanmar, downloads Myanmar town point data from HDX/MIMU, and performs a spatial hazard exposure analysis to identify towns that are more vulnerable based on proximity to epicenters, local event frequency, and magnitude characteristics.

## What this project produces

- A GeoJSON of Myanmar earthquake events filtered to the country boundary
- A GeoJSON of Myanmar town points
- An enriched GeoJSON of towns with earthquake exposure metrics and hazard class
- A markdown report summarizing methods and findings

Generated files:

- `analysis_output/myanmar_earthquakes_usgs.geojson`
- `analysis_output/myanmar_towns.geojson`
- `analysis_output/myanmar_town_earthquake_exposure.geojson`
- `analysis_output/myanmar_earthquake_hazard_report.md`

Main script:

- `analysis_output/analyze_myanmar_eq.py`

---

## Repository structure

```text
.
├── README.md
└── analysis_output/
    ├── analyze_myanmar_eq.py
    ├── myanmar_earthquake_hazard_report.md
    ├── myanmar_earthquakes_usgs.geojson
    ├── myanmar_town_earthquake_exposure.geojson
    └── myanmar_towns.geojson
```

---

## Data sources

### 1) Earthquakes

- Source: USGS FDSN Event Web Service
- Endpoint: `https://earthquake.usgs.gov/fdsnws/event/1/`
- Query period: `1900-01-01` to run date
- Retrieval format: GeoJSON

### 2) Town points

- Source dataset page: `https://data.humdata.org/dataset/mimu-geonode-myanmar-town-points-pcode`
- Provider: Myanmar Information Management Unit (MIMU) via HDX
- Retrieval format: GeoJSON (WFS endpoint referenced by HDX resource)

### 3) Myanmar boundary used for filtering

- Source: country boundary GeoJSON from `johan/world.geo.json`
- Used only for point-in-polygon filtering of earthquake epicenters inside Myanmar

---

## Methodology

The workflow is fully implemented in `analysis_output/analyze_myanmar_eq.py`.

1. Download Myanmar boundary geometry.
2. Compute boundary bounding box.
3. Query all available USGS events in that bounding box (paged requests).
4. Filter events using point-in-polygon to keep only epicenters inside Myanmar.
5. Download Myanmar town points from the HDX-linked GeoJSON endpoint.
6. For each town, compute exposure indicators:
   - nearest epicenter distance (km)
   - number of events within 50 km (`eq_n50`)
   - number of events within 100 km (`eq_n100`)
   - maximum magnitude within 100 km (`eq_maxm100`)
   - average magnitude within 100 km (`eq_avgm100`)
   - magnitude-distance index (`eq_mdi`)
7. Normalize selected indicators and compute a composite hazard exposure score (`eq_hz_score`) using:
   - Proximity risk: 30%
   - Event frequency within 100 km: 35%
   - Maximum magnitude within 100 km: 20%
   - Magnitude-distance index: 15%
8. Classify towns into hazard classes (`eq_hz_class`) using equal-interval bins over the score range:
   - Low
   - Moderate
   - High
   - Very High

### Score interpretation

- Higher `eq_hz_score` means higher relative earthquake hazard exposure in this dataset.
- Scores are relative to the analyzed town set and should not be interpreted as absolute probability of damage.

---

## Requirements

Python 3.10+ is recommended.

Required package:

- `requests`

Optional but strongly recommended:

- `cloudscraper` (used as fallback when the endpoint is behind anti-bot protection)

Install packages:

```bash
pip install requests cloudscraper
```

---

## How to run

From repository root:

```bash
python analysis_output/analyze_myanmar_eq.py
```

The script will:

- download/refresh input datasets,
- perform analysis,
- overwrite output files in `analysis_output/`.

---

## Output schema (enriched towns)

Each feature in `analysis_output/myanmar_town_earthquake_exposure.geojson` contains original town attributes plus added fields:

- `eq_near_km`: nearest earthquake distance in km
- `eq_n50`: event count within 50 km
- `eq_n100`: event count within 100 km
- `eq_maxm100`: max magnitude within 100 km
- `eq_avgm100`: average magnitude within 100 km
- `eq_mdi`: magnitude-distance index
- `eq_hz_score`: composite exposure score
- `eq_hz_class`: Low/Moderate/High/Very High

---

## Reproducibility notes

- Results change over time as USGS catalog updates and new earthquakes occur.
- The script always uses current run date as the query end date.
- If endpoint availability changes (especially MIMU GeoNode), rerun later or use a mirrored source.

---

## Assumptions and limitations

- This is a hazard exposure screening analysis, not a full seismic risk model.
- It does not include:
  - local soil amplification,
  - building vulnerability,
  - fault mechanics,
  - population/building exposure intensity,
  - temporal declustering of aftershocks.
- Distance-based metrics use haversine distance and earthquake epicenters only.
- Hazard class thresholds are data-driven from current score distribution.

---

## Legal and usage notes

- USGS data is public and should be cited appropriately.
- MIMU dataset includes terms/conditions on HDX; check the dataset page before redistribution and online publication.

Recommended citations:

- USGS Earthquake Catalog (FDSN Event Web Service)
- HDX/MIMU Myanmar Town Points PCode v9.4

---

## Troubleshooting

### 403 when downloading town points

The endpoint may be protected by anti-bot checks.

What to do:

1. Ensure `cloudscraper` is installed:
   ```bash
   pip install cloudscraper
   ```
2. Rerun the script.

### Slow run time

- The USGS historical query can take time due to event volume and pagination.
- Stable internet is required.

---

## Suggested extensions

- Add seismic zoning/fault-line layers and perform multi-factor weighting.
- Add population and critical infrastructure exposure overlays.
- Produce static and interactive maps (Leaflet/Folium/QGIS exports).
- Add automated tests and CI for repeatable runs.
