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
from event_impact.ingestion.common.provenance import (
    download_and_record,
    is_already_acquired,
    write_provenance,
)
from event_impact.ingestion.common.validation import (
    Severity,
    ValidationReport,
    check_count,
    check_required_columns,
)
from event_impact.ingestion.taxi import distinct_location_ids, download_month, raw_path_for

LOOKUP_PATH = TAXI_ZONES_RAW_DIR / "taxi_zone_lookup.csv"
GEOMETRY_ZIP_PATH = TAXI_ZONES_RAW_DIR / "taxi_zones.zip"
# The zip's own top-level entry is a "taxi_zones/" folder (confirmed by inspecting the real
# archive during PR-005), so extracting into TAXI_ZONES_RAW_DIR — not a same-named
# subdirectory of it — is what avoids a doubly-nested taxi_zones/taxi_zones/ path.
GEOMETRY_EXTRACT_DIR = TAXI_ZONES_RAW_DIR

REQUIRED_LOOKUP_COLUMNS = ["LocationID", "Borough", "Zone", "service_zone"]
REQUIRED_GEOMETRY_COLUMNS = ["LocationID", "geometry"]

# Yankee Stadium, Bronx, NY — public, well-documented coordinates (WGS84), used as a single
# representative point to identify its containing taxi zone via point-in-polygon.
YANKEE_STADIUM_LON = -73.9262
YANKEE_STADIUM_LAT = 40.8296


def download_lookup() -> Path:
    return download_and_record(TAXI_ZONE_LOOKUP_URL, LOOKUP_PATH)


def _find_geometry_shapefile() -> Path:
    """Locate the extracted zone geometry .shp file by search rather than assuming the zip's
    exact internal folder name. TLC's real archive turned out to already contain a top-level
    `taxi_zones/` folder (the extraction-nesting bug fixed elsewhere in this module) — a
    hardcoded path baked in today's layout would silently break if TLC repackages the zip
    with a different (or no) internal folder."""
    matches = sorted(GEOMETRY_EXTRACT_DIR.rglob("*.shp"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"expected exactly one .shp file under {GEOMETRY_EXTRACT_DIR}, found "
            f"{len(matches)}: {matches}"
        )
    return matches[0]


def download_geometry() -> Path:
    """Download the zone geometry Shapefile archive and extract it, skipping the download
    entirely when the zip was already fully acquired (see `is_already_acquired`).

    Provenance is recorded only once extraction succeeds — not against the raw zip alone — so
    a process killed between download and extraction (disk full, OOM, SIGKILL) can't leave a
    provenance sidecar that looks complete while the extracted shapefile is partial/corrupt.
    """
    if is_already_acquired(GEOMETRY_ZIP_PATH):
        return _find_geometry_shapefile()
    result = download_file(TAXI_ZONE_GEOMETRY_URL, GEOMETRY_ZIP_PATH)
    with zipfile.ZipFile(GEOMETRY_ZIP_PATH) as zf:
        zf.extractall(GEOMETRY_EXTRACT_DIR)
    shapefile_path = _find_geometry_shapefile()
    write_provenance(result)
    return shapefile_path


def load_lookup(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path if path is not None else LOOKUP_PATH)


def load_geometry(path: Path | None = None) -> gpd.GeoDataFrame:
    return gpd.read_file(path if path is not None else _find_geometry_shapefile())


def validate_lookup(df: pd.DataFrame) -> ValidationReport:
    """Source-quality validation only — no cleaning or record removal."""
    report = ValidationReport(source="taxi_zone_lookup.csv")
    check_required_columns(report, list(df.columns), REQUIRED_LOOKUP_COLUMNS)
    if report.has_errors():
        return report

    total = len(df)
    null_location_id_count = int(df["LocationID"].isna().sum())
    check_count(
        report,
        "null_location_id",
        null_location_id_count,
        total=total,
        ok_message="no null LocationID values",
        problem_message="rows with a null LocationID",
        severity=Severity.ERROR,
    )
    check_count(
        report,
        "duplicate_location_id",
        # nunique() defaults to dropna=True, so subtracting it from a null-inclusive total
        # would double-count a null LocationID as a "duplicate" on top of the dedicated null
        # check above; subtracting the null count first isolates true (non-null) duplicates.
        total - null_location_id_count - df["LocationID"].nunique(),
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
    null_location_id_count = int(gdf["LocationID"].isna().sum())
    check_count(
        report,
        "null_location_id",
        null_location_id_count,
        total=total,
        ok_message="no null LocationID values in the geometry file",
        problem_message="rows with a null LocationID in the geometry file",
        severity=Severity.ERROR,
    )
    check_count(
        report,
        "duplicate_location_id",
        # See the matching comment in validate_lookup: subtract the null count before
        # subtracting nunique() (dropna=True) so a null LocationID isn't also counted here.
        total - null_location_id_count - gdf["LocationID"].nunique(),
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


def validate_location_id_compatibility(compatibility: LocationIdCompatibility) -> ValidationReport:
    """Wrap `check_location_id_compatibility`'s result in a `ValidationReport` so a real
    incompatibility (a taxi trip referencing a zone absent from the lookup table) trips
    `has_errors()` like every other check in this module, instead of only being visible to a
    human reading the raw dataclass. Zones unused by the taxi data are expected and reported
    at INFO — see `check_location_id_compatibility`'s docstring."""
    report = ValidationReport(source="taxi_zone_location_id_compatibility")

    missing = compatibility.taxi_ids_missing_from_zone_lookup
    if missing:
        report.add(
            "taxi_ids_missing_from_zone_lookup",
            Severity.ERROR,
            f"taxi LocationIDs not present in the zone lookup: {missing}",
            count=len(missing),
        )
    else:
        report.add(
            "taxi_ids_missing_from_zone_lookup",
            Severity.INFO,
            "every taxi LocationID is present in the zone lookup",
        )

    unused = compatibility.zone_ids_unused_in_taxi_data
    report.add(
        "zone_ids_unused_in_taxi_data",
        Severity.INFO,
        f"{len(unused)} zone LocationIDs unused in the taxi data: {unused}"
        if unused
        else "every zone LocationID is used in the taxi data",
        count=len(unused) if unused else None,
    )

    return report


def find_zone_containing_point(
    gdf: gpd.GeoDataFrame, lon: float, lat: float
) -> gpd.GeoDataFrame:
    """Return the zone row(s) whose polygon contains a (lon, lat) WGS84 point — used here to
    identify Yankee Stadium's zone. This is identification only; the distance/adjacency
    methodology for the spatial analysis itself is not decided here (data-dependent, per
    docs/project/01_ANALYTICAL_PLAN.md).

    General-purpose: a point may legitimately match zero zones (outside all polygons) or, for
    overlapping polygons, more than one — callers that require exactly one match (e.g.
    `find_yankee_stadium_zone`) must check the result count themselves.
    """
    if gdf.crs is None:
        raise ValueError(
            "gdf has no CRS defined — run validate_geometry first (its crs_defined check "
            "exists for exactly this case) before calling find_zone_containing_point"
        )
    point = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(gdf.crs).iloc[0]
    return gdf[gdf.contains(point)]


def find_yankee_stadium_zone(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Identify the single zone containing Yankee Stadium's coordinates.

    Yankee Stadium's fixed lon/lat is itself an approximation, so a result count other than
    exactly one (no match, if it lands outside every polygon; more than one, if it lands on a
    shared edge between adjacent polygons) is treated as an error rather than silently
    returned — a caller expecting one zone should never get zero or the wrong one silently.
    """
    result = find_zone_containing_point(gdf, YANKEE_STADIUM_LON, YANKEE_STADIUM_LAT)
    if len(result) != 1:
        raise ValueError(
            "expected exactly one zone containing Yankee Stadium's coordinates "
            f"({YANKEE_STADIUM_LON}, {YANKEE_STADIUM_LAT}), found {len(result)}"
        )
    return result


def run_zone_acquisition(
    taxi_year_month: str = "2019-01",
) -> tuple[
    ValidationReport,
    ValidationReport,
    ValidationReport,
    gpd.GeoDataFrame,
]:
    """Download (if needed), load, and validate the zone lookup and geometry; check
    LocationID compatibility against a real taxi trip slice; and identify Yankee Stadium's
    zone — the single reproducible entry point for the numbers documented in
    docs/project/03_DATA_ACQUISITION.md.

    Returns `(lookup_report, geometry_report, compatibility_report, yankee_stadium_zone)`.
    """
    download_lookup()
    download_geometry()
    lookup_df = load_lookup()
    geometry_gdf = load_geometry()

    lookup_report = validate_lookup(lookup_df)
    geometry_report = validate_geometry(geometry_gdf)

    taxi_path = raw_path_for(taxi_year_month)
    download_month(taxi_year_month)
    taxi_ids = distinct_location_ids(taxi_path)
    compatibility = check_location_id_compatibility(taxi_ids, set(lookup_df["LocationID"]))
    compatibility_report = validate_location_id_compatibility(compatibility)

    yankee_stadium_zone = find_yankee_stadium_zone(geometry_gdf)

    return lookup_report, geometry_report, compatibility_report, yankee_stadium_zone


if __name__ == "__main__":
    lookup_report, geometry_report, compatibility_report, yankee_stadium_zone = (
        run_zone_acquisition()
    )
    print(lookup_report.summary())
    print()
    print(geometry_report.summary())
    print()
    print(compatibility_report.summary())
    print()
    print(f"Yankee Stadium zone LocationID(s): {list(yankee_stadium_zone['LocationID'])}")
