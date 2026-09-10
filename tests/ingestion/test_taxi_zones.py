import zipfile

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from event_impact.ingestion import taxi_zones
from event_impact.ingestion.common.http import DownloadResult
from event_impact.ingestion.common.provenance import provenance_path_for


def issue(report, check_name):
    return next(i for i in report.issues if i.check == check_name)


@pytest.fixture
def lookup_df():
    return pd.DataFrame(
        {
            "LocationID": [1, 2, 3],
            "Borough": ["Manhattan", "Bronx", "Queens"],
            "Zone": ["Zone A", "Zone B", "Zone C"],
            "service_zone": ["Yellow Zone", "Boro Zone", "Boro Zone"],
        }
    )


def test_validate_lookup_passes_clean_data(lookup_df):
    report = taxi_zones.validate_lookup(lookup_df)
    assert not report.has_errors()
    assert issue(report, "duplicate_location_id").severity.value == "info"


def test_validate_lookup_rejects_missing_required_columns():
    df = pd.DataFrame({"LocationID": [1, 2]})
    report = taxi_zones.validate_lookup(df)
    assert report.has_errors()
    assert issue(report, "required_columns").severity.value == "error"
    assert len(report.issues) == 1


def test_validate_lookup_detects_duplicate_location_id(lookup_df):
    df = pd.concat([lookup_df, lookup_df.iloc[[0]]], ignore_index=True)
    report = taxi_zones.validate_lookup(df)
    dup_issue = issue(report, "duplicate_location_id")
    assert dup_issue.count == 1
    assert dup_issue.severity.value == "error"


def test_validate_lookup_detects_null_zone_name(lookup_df):
    lookup_df.loc[0, "Zone"] = None
    report = taxi_zones.validate_lookup(lookup_df)
    assert issue(report, "null_zone_name").count == 1


def test_validate_lookup_detects_null_location_id_without_flagging_duplicate(lookup_df):
    df = pd.concat([lookup_df, lookup_df.iloc[[0]]], ignore_index=True)
    df.loc[3, "LocationID"] = None
    report = taxi_zones.validate_lookup(df)
    assert issue(report, "null_location_id").count == 1
    assert issue(report, "null_location_id").severity.value == "error"
    # The null LocationID must not also be counted as a duplicate: 4 rows, 1 null, 3 distinct
    # non-null values (1, 2, 3) -> zero true duplicates.
    assert issue(report, "duplicate_location_id").severity.value == "info"


@pytest.fixture
def zone_gdf():
    # Two simple, valid, non-overlapping unit squares.
    square_a = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    square_b = Polygon([(2, 0), (3, 0), (3, 1), (2, 1)])
    return gpd.GeoDataFrame(
        {"LocationID": [1, 2], "geometry": [square_a, square_b]}, crs="EPSG:4326"
    )


def test_validate_geometry_passes_clean_data(zone_gdf):
    report = taxi_zones.validate_geometry(zone_gdf)
    assert not report.has_errors()
    assert "EPSG:4326" in issue(report, "crs_defined").message


def test_validate_geometry_rejects_missing_required_columns():
    gdf = gpd.GeoDataFrame({"LocationID": [1]})
    report = taxi_zones.validate_geometry(gdf)
    assert report.has_errors()
    assert issue(report, "required_columns").severity.value == "error"


def test_validate_geometry_detects_invalid_geometry(zone_gdf):
    # A classic self-intersecting "bowtie" polygon.
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    zone_gdf.loc[0, "geometry"] = bowtie
    report = taxi_zones.validate_geometry(zone_gdf)
    invalid_issue = issue(report, "invalid_geometry")
    assert invalid_issue.count == 1
    assert invalid_issue.severity.value == "error"


def test_validate_geometry_detects_missing_crs():
    square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    gdf = gpd.GeoDataFrame({"LocationID": [1], "geometry": [square]})  # no crs= passed
    report = taxi_zones.validate_geometry(gdf)
    assert issue(report, "crs_defined").severity.value == "error"


def test_validate_geometry_detects_null_location_id_without_flagging_duplicate(zone_gdf):
    df = pd.concat([zone_gdf, zone_gdf.iloc[[0]]], ignore_index=True)
    df.loc[2, "LocationID"] = None
    report = taxi_zones.validate_geometry(gpd.GeoDataFrame(df, crs=zone_gdf.crs))
    assert issue(report, "null_location_id").count == 1
    assert issue(report, "null_location_id").severity.value == "error"
    assert issue(report, "duplicate_location_id").severity.value == "info"


def test_check_location_id_compatibility_finds_missing_taxi_ids():
    result = taxi_zones.check_location_id_compatibility(
        taxi_location_ids={1, 2, 999}, zone_lookup_ids={1, 2, 3}
    )
    assert result.taxi_ids_missing_from_zone_lookup == [999]
    assert result.zone_ids_unused_in_taxi_data == [3]


def test_validate_location_id_compatibility_flags_missing_taxi_ids_as_error():
    compatibility = taxi_zones.check_location_id_compatibility(
        taxi_location_ids={1, 2, 999}, zone_lookup_ids={1, 2, 3}
    )
    report = taxi_zones.validate_location_id_compatibility(compatibility)
    assert report.has_errors()
    missing_issue = issue(report, "taxi_ids_missing_from_zone_lookup")
    assert missing_issue.severity.value == "error"
    assert missing_issue.count == 1
    unused_issue = issue(report, "zone_ids_unused_in_taxi_data")
    assert unused_issue.severity.value == "info"


def test_validate_location_id_compatibility_passes_when_fully_compatible():
    compatibility = taxi_zones.check_location_id_compatibility(
        taxi_location_ids={1, 2}, zone_lookup_ids={1, 2, 3}
    )
    report = taxi_zones.validate_location_id_compatibility(compatibility)
    assert not report.has_errors()
    assert issue(report, "taxi_ids_missing_from_zone_lookup").severity.value == "info"


def test_find_zone_containing_point_identifies_correct_zone(zone_gdf):
    # A point inside square_a (LocationID 1), not square_b.
    result = taxi_zones.find_zone_containing_point(zone_gdf, lon=0.5, lat=0.5)
    assert list(result["LocationID"]) == [1]


def test_find_zone_containing_point_returns_empty_when_no_zone_matches(zone_gdf):
    result = taxi_zones.find_zone_containing_point(zone_gdf, lon=10.0, lat=10.0)
    assert len(result) == 0


def test_find_zone_containing_point_raises_when_gdf_has_no_crs():
    square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    gdf = gpd.GeoDataFrame({"LocationID": [1], "geometry": [square]})  # no crs= passed
    with pytest.raises(ValueError, match="no CRS"):
        taxi_zones.find_zone_containing_point(gdf, lon=0.5, lat=0.5)


def test_find_yankee_stadium_zone_uses_the_documented_coordinates(monkeypatch, zone_gdf):
    monkeypatch.setattr(taxi_zones, "YANKEE_STADIUM_LON", 0.5)
    monkeypatch.setattr(taxi_zones, "YANKEE_STADIUM_LAT", 0.5)
    result = taxi_zones.find_yankee_stadium_zone(zone_gdf)
    assert list(result["LocationID"]) == [1]


def test_find_yankee_stadium_zone_raises_when_no_zone_matches(monkeypatch, zone_gdf):
    monkeypatch.setattr(taxi_zones, "YANKEE_STADIUM_LON", 10.0)
    monkeypatch.setattr(taxi_zones, "YANKEE_STADIUM_LAT", 10.0)
    with pytest.raises(ValueError, match="found 0"):
        taxi_zones.find_yankee_stadium_zone(zone_gdf)


def test_find_yankee_stadium_zone_raises_when_multiple_zones_match(monkeypatch, zone_gdf):
    # Point exactly on the shared boundary the two unit squares would have if adjacent —
    # simulated here by adding a third polygon that overlaps square_a entirely.
    overlapping = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    gdf = gpd.GeoDataFrame(
        {"LocationID": [1, 2, 3], "geometry": [zone_gdf.geometry[0], zone_gdf.geometry[1], overlapping]},
        crs=zone_gdf.crs,
    )
    monkeypatch.setattr(taxi_zones, "YANKEE_STADIUM_LON", 0.5)
    monkeypatch.setattr(taxi_zones, "YANKEE_STADIUM_LAT", 0.5)
    with pytest.raises(ValueError, match="found 2"):
        taxi_zones.find_yankee_stadium_zone(gdf)


def test_point_used_for_lookup_is_the_expected_location():
    # Sanity check that YANKEE_STADIUM_LON/LAT are a real (lon, lat) pair in the Bronx, not
    # accidentally swapped — Yankee Stadium is west of -73.9 and north of 40.8.
    point = Point(taxi_zones.YANKEE_STADIUM_LON, taxi_zones.YANKEE_STADIUM_LAT)
    assert -74.0 < point.x < -73.9
    assert 40.8 < point.y < 40.85


def test_load_lookup_reads_current_lookup_path_after_monkeypatch(tmp_path, monkeypatch):
    # Regression test: load_lookup's default argument must not freeze LOOKUP_PATH at import
    # time, or redirecting the module-level constant (as a test or future caller would) would
    # have no effect on a no-argument call.
    df = pd.DataFrame(
        {
            "LocationID": [7],
            "Borough": ["Queens"],
            "Zone": ["Zone Q"],
            "service_zone": ["Boro Zone"],
        }
    )
    path = tmp_path / "taxi_zone_lookup.csv"
    df.to_csv(path, index=False)
    monkeypatch.setattr(taxi_zones, "LOOKUP_PATH", path)

    result = taxi_zones.load_lookup()

    assert list(result["LocationID"]) == [7]


def test_find_geometry_shapefile_raises_when_none_found(tmp_path, monkeypatch):
    monkeypatch.setattr(taxi_zones, "GEOMETRY_EXTRACT_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        taxi_zones._find_geometry_shapefile()


def test_find_geometry_shapefile_raises_when_multiple_found(tmp_path, monkeypatch):
    monkeypatch.setattr(taxi_zones, "GEOMETRY_EXTRACT_DIR", tmp_path)
    (tmp_path / "a.shp").touch()
    (tmp_path / "b.shp").touch()
    with pytest.raises(FileNotFoundError):
        taxi_zones._find_geometry_shapefile()


def test_load_geometry_discovers_shapefile_dynamically_by_search(tmp_path, monkeypatch):
    # Regression test: the shapefile path must be discovered by search, not assumed from a
    # hardcoded "taxi_zones/taxi_zones.shp" layout — placed under an unrelated folder name to
    # prove this isn't coincidentally matching the old hardcoded constant.
    monkeypatch.setattr(taxi_zones, "GEOMETRY_EXTRACT_DIR", tmp_path)
    nested_dir = tmp_path / "some_other_layout"
    nested_dir.mkdir()
    square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    gpd.GeoDataFrame({"LocationID": [1]}, geometry=[square], crs="EPSG:4326").to_file(
        nested_dir / "zones.shp"
    )

    result = taxi_zones.load_geometry()

    assert list(result["LocationID"]) == [1]


def _build_zip_with_shapefile(zip_dest, source_dir, internal_folder_name) -> None:
    square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    shp_src = source_dir / "zones.shp"
    gpd.GeoDataFrame({"LocationID": [1]}, geometry=[square], crs="EPSG:4326").to_file(shp_src)
    with zipfile.ZipFile(zip_dest, "w") as zf:
        for part in source_dir.glob("zones.*"):
            zf.write(part, arcname=f"{internal_folder_name}/{part.name}")


def test_download_geometry_extracts_discovers_shapefile_and_records_provenance(
    tmp_path, monkeypatch
):
    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    zip_dest = tmp_path / "taxi_zones.zip"
    monkeypatch.setattr(taxi_zones, "GEOMETRY_ZIP_PATH", zip_dest)
    monkeypatch.setattr(taxi_zones, "GEOMETRY_EXTRACT_DIR", extract_dir)
    source_dir = tmp_path / "_source"
    source_dir.mkdir()
    call_count = {"n": 0}

    def fake_download_file(url, dest_path, **kwargs):
        call_count["n"] += 1
        # Internal folder name deliberately differs from the real archive's "taxi_zones/" to
        # prove discovery isn't relying on that specific name.
        _build_zip_with_shapefile(dest_path, source_dir, "some_other_folder_name")
        return DownloadResult(
            url=url, dest_path=dest_path, size_bytes=dest_path.stat().st_size, sha256="x"
        )

    monkeypatch.setattr(taxi_zones, "download_file", fake_download_file)

    shapefile_path = taxi_zones.download_geometry()

    assert shapefile_path == extract_dir / "some_other_folder_name" / "zones.shp"
    assert shapefile_path.exists()
    assert provenance_path_for(zip_dest).exists()

    # A second call must skip the download entirely — zip + provenance already acquired.
    taxi_zones.download_geometry()
    assert call_count["n"] == 1


def test_download_geometry_does_not_record_provenance_when_extraction_fails(
    tmp_path, monkeypatch
):
    zip_dest = tmp_path / "taxi_zones.zip"
    monkeypatch.setattr(taxi_zones, "GEOMETRY_ZIP_PATH", zip_dest)
    monkeypatch.setattr(taxi_zones, "GEOMETRY_EXTRACT_DIR", tmp_path)

    def fake_download_file(url, dest_path, **kwargs):
        dest_path.write_bytes(b"not a real zip")  # extraction will fail on this
        return DownloadResult(
            url=url, dest_path=dest_path, size_bytes=dest_path.stat().st_size, sha256="x"
        )

    monkeypatch.setattr(taxi_zones, "download_file", fake_download_file)

    with pytest.raises(zipfile.BadZipFile):
        taxi_zones.download_geometry()

    # A provenance sidecar existing would (per is_already_acquired) tell a future caller the
    # source is fully acquired even though extraction never completed.
    assert not provenance_path_for(zip_dest).exists()


def test_run_zone_acquisition_wires_the_full_pipeline(tmp_path, monkeypatch):
    """Regression test for check_location_id_compatibility having no committed caller: this
    exercises the same download -> load -> validate -> compatibility-check -> zone-lookup
    chain the PR's headline numbers are claimed to come from."""
    lookup_df = pd.DataFrame(
        {
            "LocationID": [1, 2, 3],
            "Borough": ["Manhattan", "Bronx", "Queens"],
            "Zone": ["Zone A", "Zone B", "Zone C"],
            "service_zone": ["Yellow Zone", "Boro Zone", "Boro Zone"],
        }
    )
    lookup_path = tmp_path / "taxi_zone_lookup.csv"
    lookup_df.to_csv(lookup_path, index=False)

    square_a = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    square_b = Polygon([(2, 0), (3, 0), (3, 1), (2, 1)])
    geometry_path = tmp_path / "zones.shp"
    gpd.GeoDataFrame(
        {"LocationID": [1, 2]}, geometry=[square_a, square_b], crs="EPSG:4326"
    ).to_file(geometry_path)

    monkeypatch.setattr(taxi_zones, "download_lookup", lambda: lookup_path)
    monkeypatch.setattr(taxi_zones, "download_geometry", lambda: geometry_path)
    monkeypatch.setattr(taxi_zones, "load_lookup", lambda path=None: pd.read_csv(lookup_path))
    monkeypatch.setattr(
        taxi_zones, "load_geometry", lambda path=None: gpd.read_file(geometry_path)
    )
    monkeypatch.setattr(taxi_zones, "YANKEE_STADIUM_LON", 0.5)
    monkeypatch.setattr(taxi_zones, "YANKEE_STADIUM_LAT", 0.5)
    monkeypatch.setattr(taxi_zones, "download_month", lambda year_month: None)
    monkeypatch.setattr(taxi_zones, "distinct_location_ids", lambda path: {1, 2, 999})

    lookup_report, geometry_report, compatibility_report, yankee_zone = (
        taxi_zones.run_zone_acquisition()
    )

    assert not lookup_report.has_errors()
    assert not geometry_report.has_errors()
    assert compatibility_report.has_errors()  # taxi LocationID 999 is missing from the lookup
    assert list(yankee_zone["LocationID"]) == [1]
