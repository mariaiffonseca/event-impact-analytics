"""NYC TLC Taxi Zone lookup table and zone geometry — acquisition and source validation.

Acquires the zone lookup table (CSV) and zone geometry (Shapefile), validates them, checks
LocationID compatibility against the taxi trip data, and identifies the taxi zone containing
Yankee Stadium. Distance/adjacency methodology is explicitly not decided here — see
docs/project/01_ANALYTICAL_PLAN.md.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from event_impact.config import TAXI_ZONE_GEOMETRY_URL, TAXI_ZONE_LOOKUP_URL, TAXI_ZONES_RAW_DIR
from event_impact.ingestion.common.http import download_file
from event_impact.ingestion.common.provenance import write_provenance
from event_impact.ingestion.common.validation import (
    Severity,
    ValidationReport,
    check_count,
    check_required_columns,
)

LOOKUP_PATH = TAXI_ZONES_RAW_DIR / "taxi_zone_lookup.csv"
GEOMETRY_ZIP_PATH = TAXI_ZONES_RAW_DIR / "taxi_zones.zip"
# The zip's own top-level entry is a "taxi_zones/" folder (confirmed by inspecting the real
# archive during PR-005), so extracting into TAXI_ZONES_RAW_DIR — not a same-named
# subdirectory of it — is what avoids a doubly-nested taxi_zones/taxi_zones/ path.
GEOMETRY_EXTRACT_DIR = TAXI_ZONES_RAW_DIR
GEOMETRY_SHAPEFILE_PATH = GEOMETRY_EXTRACT_DIR / "taxi_zones" / "taxi_zones.shp"

REQUIRED_LOOKUP_COLUMNS = ["LocationID", "Borough", "Zone", "service_zone"]
REQUIRED_GEOMETRY_COLUMNS = ["LocationID", "geometry"]

# Yankee Stadium, Bronx, NY — public, well-documented coordinates (WGS84), used as a single
# representative point to identify its containing taxi zone via point-in-polygon.
YANKEE_STADIUM_LON = -73.9262
YANKEE_STADIUM_LAT = 40.8296


def download_lookup() -> Path:
    result = download_file(TAXI_ZONE_LOOKUP_URL, LOOKUP_PATH)
    write_provenance(result)
    return LOOKUP_PATH


def download_geometry() -> Path:
    """Download the zone geometry Shapefile archive and extract it, with provenance recorded
    against the downloaded .zip (not the individual extracted shapefile parts)."""
    result = download_file(TAXI_ZONE_GEOMETRY_URL, GEOMETRY_ZIP_PATH)
    write_provenance(result)
    with zipfile.ZipFile(GEOMETRY_ZIP_PATH) as zf:
        zf.extractall(GEOMETRY_EXTRACT_DIR)
    return GEOMETRY_SHAPEFILE_PATH


def load_lookup(path: Path = LOOKUP_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def load_geometry(path: Path = GEOMETRY_SHAPEFILE_PATH) -> gpd.GeoDataFrame:
    return gpd.read_file(path)


def validate_lookup(df: pd.DataFrame) -> ValidationReport:
    """Source-quality validation only — no cleaning or record removal."""
    report = ValidationReport(source="taxi_zone_lookup.csv")
    check_required_columns(report, list(df.columns), REQUIRED_LOOKUP_COLUMNS)
    if report.has_errors():
        return report

    total = len(df)
    check_count(
        report,
        "duplicate_location_id",
        total - df["LocationID"].nunique(),
        total=total,
        ok_message="all LocationID values unique",
        problem_message="duplicate LocationID values",
        severity=Severity.ERROR,
    )
    check_count(
        report,
        "null_zone_name",
        int(df["Zone"].isna().sum()),
        total=total,
        ok_message="no null Zone names",
        problem_message="rows with a null Zone name",
    )
    check_count(
        report,
        "null_borough",
        int(df["Borough"].isna().sum()),
        total=total,
        ok_message="no null Borough values",
        problem_message="rows with a null Borough",
    )

    return report


def validate_geometry(gdf: gpd.GeoDataFrame) -> ValidationReport:
    """Source-quality validation only — no cleaning or record removal."""
    report = ValidationReport(source="taxi_zones geometry")
    check_required_columns(report, list(gdf.columns), REQUIRED_GEOMETRY_COLUMNS)
    if report.has_errors():
        return report

    total = len(gdf)
    check_count(
        report,
        "invalid_geometry",
        int((~gdf.geometry.is_valid).sum()),
        total=total,
        ok_message="all geometries valid",
        problem_message="rows with an invalid (e.g. self-intersecting) geometry",
        severity=Severity.ERROR,
    )
    check_count(
        report,
        "empty_geometry",
        int(gdf.geometry.is_empty.sum()),
        total=total,
        ok_message="no empty geometries",
        problem_message="rows with an empty geometry",
        severity=Severity.ERROR,
    )
    check_count(
        report,
        "duplicate_location_id",
        total - gdf["LocationID"].nunique(),
        total=total,
        ok_message="all LocationID values unique in the geometry file",
        problem_message="duplicate LocationID values in the geometry file",
        severity=Severity.ERROR,
    )

    if gdf.crs is None:
        report.add("crs_defined", Severity.ERROR, "no CRS defined for the zone geometry")
    else:
        report.add("crs_defined", Severity.INFO, f"CRS: {gdf.crs}")

    return report


@dataclass(frozen=True)
class LocationIdCompatibility:
    taxi_ids_missing_from_zone_lookup: list[int]
    zone_ids_unused_in_taxi_data: list[int]


def check_location_id_compatibility(
    taxi_location_ids: set[int], zone_lookup_ids: set[int]
) -> LocationIdCompatibility:
    """Every LocationID the taxi data actually uses should be a real zone in the lookup
    table. The reverse isn't required — plenty of zones legitimately see zero trips in any
    given slice."""
    return LocationIdCompatibility(
        taxi_ids_missing_from_zone_lookup=sorted(taxi_location_ids - zone_lookup_ids),
        zone_ids_unused_in_taxi_data=sorted(zone_lookup_ids - taxi_location_ids),
    )


def find_zone_containing_point(
    gdf: gpd.GeoDataFrame, lon: float, lat: float
) -> gpd.GeoDataFrame:
    """Return the zone row(s) whose polygon contains a (lon, lat) WGS84 point — used here to
    identify Yankee Stadium's zone. This is identification only; the distance/adjacency
    methodology for the spatial analysis itself is not decided here (data-dependent, per
    docs/project/01_ANALYTICAL_PLAN.md)."""
    point = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(gdf.crs).iloc[0]
    return gdf[gdf.contains(point)]


def find_yankee_stadium_zone(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return find_zone_containing_point(gdf, YANKEE_STADIUM_LON, YANKEE_STADIUM_LAT)
