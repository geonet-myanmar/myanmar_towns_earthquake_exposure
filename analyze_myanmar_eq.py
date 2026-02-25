import json
import importlib
import importlib.util
import math
from datetime import date
from pathlib import Path

import requests

cloudscraper = (
    importlib.import_module("cloudscraper")
    if importlib.util.find_spec("cloudscraper")
    else None
)


USGS_QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_COUNT_URL = "https://earthquake.usgs.gov/fdsnws/event/1/count"
MYANMAR_BOUNDARY_URL = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries/MMR.geo.json"
TOWNS_GEOJSON_URL = (
    "https://geonode.themimu.info/geoserver/geonode/ows?service=WFS&version=1.0.0"
    "&request=GetFeature&outputFormat=application%2Fjson&typeName=geonode:mmr_pplp1_mimu250k"
)


def fetch_json(url, params=None, timeout=180):
    response = requests.get(url, params=params, timeout=timeout)
    if response.status_code == 403 and cloudscraper is not None:
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "linux", "desktop": True}
        )
        response = scraper.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_text(url, params=None, timeout=180):
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.text


def normalize_polygons(geometry):
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    raise ValueError(f"Unsupported geometry type: {geometry['type']}")


def point_in_ring(lon, lat, ring):
    inside = False
    n = len(ring)
    if n < 3:
        return False
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if ((y1 > lat) != (y2 > lat)) and (
            lon < (x2 - x1) * (lat - y1) / ((y2 - y1) + 1e-15) + x1
        ):
            inside = not inside
    return inside


def point_in_polygon(lon, lat, polygon_rings):
    if not point_in_ring(lon, lat, polygon_rings[0]):
        return False
    for hole in polygon_rings[1:]:
        if point_in_ring(lon, lat, hole):
            return False
    return True


def point_in_multipolygon(lon, lat, polygons):
    for polygon in polygons:
        if point_in_polygon(lon, lat, polygon):
            return True
    return False


def haversine_km(lon1, lat1, lon2, lat2):
    r = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(
        dlambda / 2.0
    ) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bounds_from_polygons(polygons):
    lons = []
    lats = []
    for polygon in polygons:
        for ring in polygon:
            for lon, lat in ring:
                lons.append(lon)
                lats.append(lat)
    return min(lats), max(lats), min(lons), max(lons)


def feature_point_coords(feature):
    geom = feature.get("geometry") or {}
    if geom.get("type") != "Point":
        return None
    coords = geom.get("coordinates")
    if not coords or len(coords) < 2:
        return None
    return float(coords[0]), float(coords[1])


def safe_prop(properties, keys, default=None):
    for key in keys:
        if key in properties and properties[key] not in (None, ""):
            return properties[key]
    return default


def town_name(properties):
    return str(
        safe_prop(
            properties,
            [
                "town_name",
                "Town_Name",
                "name",
                "Name",
                "NAME",
                "TOWN",
                "town",
                "Town",
                "P_Name",
            ],
            "Unknown",
        )
    )


def township_name(properties):
    return str(
        safe_prop(
            properties,
            [
                "Township",
                "township",
                "Tsp_Name",
                "tsp_name",
                "TSP",
                "TS_Pcode",
            ],
            "Unknown",
        )
    )


def normalize(values):
    if not values:
        return []
    vmin = min(values)
    vmax = max(values)
    if math.isclose(vmin, vmax):
        return [0.0 for _ in values]
    return [(v - vmin) / (vmax - vmin) for v in values]


def compute_exposure(towns_features, eq_features):
    town_metrics = []
    radii = [50.0, 100.0]

    for feature in towns_features:
        coords = feature_point_coords(feature)
        if not coords:
            continue
        town_lon, town_lat = coords

        nearest_km = float("inf")
        near_50 = 0
        near_100 = 0
        max_mag_100 = 0.0
        sum_mag_100 = 0.0
        mag_weighted_index = 0.0

        for event in eq_features:
            eq_lon, eq_lat = event["geometry"]["coordinates"][0:2]
            dist = haversine_km(town_lon, town_lat, float(eq_lon), float(eq_lat))
            if dist < nearest_km:
                nearest_km = dist

            mag = event.get("properties", {}).get("mag")
            mag = float(mag) if mag is not None else 0.0

            if dist <= radii[0]:
                near_50 += 1
            if dist <= radii[1]:
                near_100 += 1
                max_mag_100 = max(max_mag_100, mag)
                sum_mag_100 += mag
                mag_weighted_index += max(mag, 0.0) / ((dist + 10.0) ** 1.2)

        avg_mag_100 = (sum_mag_100 / near_100) if near_100 > 0 else 0.0
        nearest_km = nearest_km if nearest_km != float("inf") else None

        town_metrics.append(
            {
                "feature": feature,
                "town_name": town_name(feature.get("properties", {})),
                "township": township_name(feature.get("properties", {})),
                "nearest_event_km": nearest_km,
                "events_within_50km": near_50,
                "events_within_100km": near_100,
                "max_mag_within_100km": round(max_mag_100, 2),
                "avg_mag_within_100km": round(avg_mag_100, 3),
                "mag_distance_index": mag_weighted_index,
            }
        )

    nearest_vals = [m["nearest_event_km"] if m["nearest_event_km"] is not None else 9999.0 for m in town_metrics]
    freq_vals = [m["events_within_100km"] for m in town_metrics]
    mag_vals = [m["max_mag_within_100km"] for m in town_metrics]
    mdi_vals = [m["mag_distance_index"] for m in town_metrics]

    nearest_risk = normalize([1.0 / (v + 1.0) for v in nearest_vals])
    freq_norm = normalize(freq_vals)
    mag_norm = normalize(mag_vals)
    mdi_norm = normalize(mdi_vals)

    for i, metric in enumerate(town_metrics):
        score = (
            0.30 * nearest_risk[i]
            + 0.35 * freq_norm[i]
            + 0.20 * mag_norm[i]
            + 0.15 * mdi_norm[i]
        )
        metric["hazard_exposure_score"] = round(score, 4)

    scores = [m["hazard_exposure_score"] for m in town_metrics]
    lo = min(scores)
    hi = max(scores)
    step = (hi - lo) / 4.0 if not math.isclose(hi, lo) else 1.0

    for metric in town_metrics:
        s = metric["hazard_exposure_score"]
        if s >= lo + 3 * step:
            cls = "Very High"
        elif s >= lo + 2 * step:
            cls = "High"
        elif s >= lo + step:
            cls = "Moderate"
        else:
            cls = "Low"
        metric["hazard_class"] = cls
        metric["feature"]["properties"].update(
            {
                "eq_near_km": round(metric["nearest_event_km"], 3)
                if metric["nearest_event_km"] is not None
                else None,
                "eq_n50": metric["events_within_50km"],
                "eq_n100": metric["events_within_100km"],
                "eq_maxm100": metric["max_mag_within_100km"],
                "eq_avgm100": metric["avg_mag_within_100km"],
                "eq_mdi": round(metric["mag_distance_index"], 6),
                "eq_hz_score": metric["hazard_exposure_score"],
                "eq_hz_class": cls,
            }
        )

    town_metrics.sort(key=lambda x: x["hazard_exposure_score"], reverse=True)
    return town_metrics


def main():
    out_dir = Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)

    boundary = fetch_json(MYANMAR_BOUNDARY_URL)
    boundary_feature = boundary["features"][0]
    polygons = normalize_polygons(boundary_feature["geometry"])
    min_lat, max_lat, min_lon, max_lon = bounds_from_polygons(polygons)

    today = date.today().isoformat()
    count_params = {
        "starttime": "1900-01-01",
        "endtime": today,
        "minlatitude": min_lat,
        "maxlatitude": max_lat,
        "minlongitude": min_lon,
        "maxlongitude": max_lon,
    }
    total_count = int(fetch_text(USGS_COUNT_URL, params=count_params).strip())

    page_size = 20000
    offset = 1
    collected = []
    while offset <= total_count:
        query_params = {
            "format": "geojson",
            "starttime": "1900-01-01",
            "endtime": today,
            "minlatitude": min_lat,
            "maxlatitude": max_lat,
            "minlongitude": min_lon,
            "maxlongitude": max_lon,
            "orderby": "time-asc",
            "limit": page_size,
            "offset": offset,
        }
        payload = fetch_json(USGS_QUERY_URL, params=query_params)
        features = payload.get("features", [])
        if not features:
            break
        collected.extend(features)
        offset += page_size

    myanmar_events = []
    for f in collected:
        geom = f.get("geometry")
        if not geom or geom.get("type") != "Point":
            continue
        lon, lat = geom["coordinates"][0:2]
        if point_in_multipolygon(float(lon), float(lat), polygons):
            myanmar_events.append(f)

    eq_geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "source": "USGS Earthquake Catalog",
            "query_start": "1900-01-01",
            "query_end": today,
            "country": "Myanmar",
            "count_bbox_query": len(collected),
            "count_within_boundary": len(myanmar_events),
        },
        "features": myanmar_events,
    }

    eq_path = out_dir / "myanmar_earthquakes_usgs.geojson"
    eq_path.write_text(json.dumps(eq_geojson, ensure_ascii=True), encoding="utf-8")

    towns_geojson = fetch_json(TOWNS_GEOJSON_URL)
    towns_path = out_dir / "myanmar_towns.geojson"
    towns_path.write_text(json.dumps(towns_geojson, ensure_ascii=True), encoding="utf-8")

    town_features = towns_geojson.get("features", [])
    metrics = compute_exposure(town_features, myanmar_events)

    enriched = {
        "type": "FeatureCollection",
        "metadata": {
            "analysis": "Town earthquake hazard exposure",
            "method": "Composite score from proximity, frequency, and magnitude",
            "earthquake_count": len(myanmar_events),
            "town_count": len(metrics),
            "source_earthquakes": "USGS Earthquake Catalog",
            "source_towns": "MIMU Town Points PCode v9.4",
            "generated_on": today,
        },
        "features": [m["feature"] for m in metrics],
    }

    exposure_geojson_path = out_dir / "myanmar_town_earthquake_exposure.geojson"
    exposure_geojson_path.write_text(
        json.dumps(enriched, ensure_ascii=True), encoding="utf-8"
    )

    top_n = 20
    lines = []
    lines.append("# Myanmar Earthquake Hazard Exposure Analysis")
    lines.append("")
    lines.append("## Data and downloads")
    lines.append(
        f"- Earthquakes: USGS FDSN event API (1900-01-01 to {today}), filtered to Myanmar boundary."
    )
    lines.append("- Towns: MIMU Town Points PCode v9.4 (GeoJSON via HDX resource endpoint).")
    lines.append(f"- Earthquake records in Myanmar: {len(myanmar_events)}")
    lines.append(f"- Town points analyzed: {len(metrics)}")
    lines.append("")
    lines.append("## Methodology")
    lines.append("1. Download Myanmar boundary and compute country bounding box.")
    lines.append(
        "2. Query all available USGS earthquake events from 1900-01-01 to today in that bounding box."
    )
    lines.append(
        "3. Apply point-in-polygon filtering so only events inside Myanmar national boundary are retained."
    )
    lines.append(
        "4. Download Myanmar town points and calculate, per town: nearest event distance, number of events within 50 km and 100 km, and local magnitude metrics within 100 km."
    )
    lines.append(
        "5. Build a composite hazard exposure score (0 to 1 after normalization) using weighted factors: proximity risk (30%), event frequency within 100 km (35%), maximum local magnitude within 100 km (20%), and magnitude-distance index (15%)."
    )
    lines.append(
        "6. Classify town scores into Low, Moderate, High, and Very High exposure classes using quartile-like equal-interval bins over the observed score range."
    )
    lines.append("")
    lines.append("## Results")
    class_counts = {}
    for m in metrics:
        class_counts[m["hazard_class"]] = class_counts.get(m["hazard_class"], 0) + 1
    for cls in ["Very High", "High", "Moderate", "Low"]:
        lines.append(f"- {cls} exposure towns: {class_counts.get(cls, 0)}")

    lines.append("")
    lines.append(f"### Top {top_n} most exposed towns")
    lines.append(
        "| Rank | Town | Township | Score | Nearest EQ (km) | EQ <=100 km | Max Mag <=100 km |"
    )
    lines.append("|---:|---|---|---:|---:|---:|---:|")
    for i, m in enumerate(metrics[:top_n], 1):
        nearest = m["nearest_event_km"]
        nearest_val = f"{nearest:.2f}" if nearest is not None else "NA"
        lines.append(
            f"| {i} | {m['town_name']} | {m['township']} | {m['hazard_exposure_score']:.4f} | {nearest_val} | {m['events_within_100km']} | {m['max_mag_within_100km']:.2f} |"
        )

    lines.append("")
    lines.append("## Output files")
    lines.append("- myanmar_earthquakes_usgs.geojson")
    lines.append("- myanmar_towns.geojson")
    lines.append("- myanmar_town_earthquake_exposure.geojson")
    lines.append("- myanmar_earthquake_hazard_report.md")

    report_path = out_dir / "myanmar_earthquake_hazard_report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Saved: {eq_path}")
    print(f"Saved: {towns_path}")
    print(f"Saved: {exposure_geojson_path}")
    print(f"Saved: {report_path}")
    print(f"Myanmar earthquakes retained: {len(myanmar_events)}")
    print(f"Myanmar towns processed: {len(metrics)}")
    print("Top 10 most exposed towns:")
    for i, m in enumerate(metrics[:10], 1):
        print(
            f"{i:>2}. {m['town_name']} ({m['township']}) | score={m['hazard_exposure_score']:.4f} | n100={m['events_within_100km']} | maxM100={m['max_mag_within_100km']:.2f}"
        )


if __name__ == "__main__":
    main()
