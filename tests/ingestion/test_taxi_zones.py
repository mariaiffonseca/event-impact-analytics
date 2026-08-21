import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from event_impact.ingestion import taxi_zones


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


def test_check_location_id_compatibility_finds_missing_taxi_ids():
    result = taxi_zones.check_location_id_compatibility(
        taxi_location_ids={1, 2, 999}, zone_lookup_ids={1, 2, 3}
    )
    assert result.taxi_ids_missing_from_zone_lookup == [999]
    assert result.zone_ids_unused_in_taxi_data == [3]


def test_find_zone_containing_point_identifies_correct_zone(zone_gdf):
    # A point inside square_a (LocationID 1), not square_b.
    result = taxi_zones.find_zone_containing_point(zone_gdf, lon=0.5, lat=0.5)
    assert list(result["LocationID"]) == [1]


def test_find_zone_containing_point_returns_empty_when_no_zone_matches(zone_gdf):
    result = taxi_zones.find_zone_containing_point(zone_gdf, lon=10.0, lat=10.0)
    assert len(result) == 0


def test_find_yankee_stadium_zone_uses_the_documented_coordinates(monkeypatch, zone_gdf):
    monkeypatch.setattr(taxi_zones, "YANKEE_STADIUM_LON", 0.5)
    monkeypatch.setattr(taxi_zones, "YANKEE_STADIUM_LAT", 0.5)
    result = taxi_zones.find_yankee_stadium_zone(zone_gdf)
    assert list(result["LocationID"]) == [1]


def test_point_used_for_lookup_is_the_expected_location():
    # Sanity check that YANKEE_STADIUM_LON/LAT are a real (lon, lat) pair in the Bronx, not
    # accidentally swapped — Yankee Stadium is west of -73.9 and north of 40.8.
    point = Point(taxi_zones.YANKEE_STADIUM_LON, taxi_zones.YANKEE_STADIUM_LAT)
    assert -74.0 < point.x < -73.9
    assert 40.8 < point.y < 40.85
