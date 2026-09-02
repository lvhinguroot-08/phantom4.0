"""
PHANTOM Surveillance GIS & Spatial Copilot Test Suite
Validates verified PostGIS geolocations, road coverage, geodesic wedge calculations,
data quality diagnostics, and AI Copilot GIS routing.
"""

import pytest
from app.core.cctv_gis_data import (
    GUJARAT_CCTV_GIS_REGISTRY,
    get_all_cctv_gis_nodes,
    get_cctv_gis_dict,
    calculate_coverage_wedge_points,
)
from app.ai.agents.copilot import get_global_copilot_agent, CopilotChatResponse
from app.ai.agents.tool_registry import phantom_tool_registry


def test_gis_registry_completeness():
    """Verify that all 30 cameras have valid verified coordinates, road names, and headings."""
    assert len(GUJARAT_CCTV_GIS_REGISTRY) == 30

    for cam in GUJARAT_CCTV_GIS_REGISTRY:
        # Latitude & Longitude must be within Gujarat bounds (20°N-25°N, 68°E-75°E)
        assert 20.0 <= cam["latitude"] <= 25.0, f"Invalid latitude {cam['latitude']} for {cam['id']}"
        assert 68.0 <= cam["longitude"] <= 75.0, f"Invalid longitude {cam['longitude']} for {cam['id']}"
        assert cam["road_name"], f"Missing road name for {cam['id']}"
        assert cam["police_station"], f"Missing police station for {cam['id']}"
        assert isinstance(cam["heading"], (int, float)), f"Missing heading for {cam['id']}"
        assert 0.0 <= cam["heading"] <= 360.0
        assert cam["has_valid_location"] is True


def test_coverage_wedge_geometry_calculation():
    """Verify that calculate_coverage_wedge_points generates a valid closed polygon."""
    # ONGC camera at (23.1028, 72.5856), heading 0.0 deg (North), FOV 90.0, range 190.0m
    points = calculate_coverage_wedge_points(
        lat=23.1028,
        lon=72.5856,
        heading_deg=0.0,
        fov_deg=90.0,
        distance_meters=190.0,
        num_points=12,
    )

    # Must start and end at the camera origin
    assert len(points) == 15  # origin + 13 arc points + origin
    assert points[0] == [23.1028, 72.5856]
    assert points[-1] == [23.1028, 72.5856]

    # Because heading is North (0°), the arc points must be north of the origin (lat > 23.1028)
    for p in points[1:-1]:
        assert p[0] >= 23.1028, f"Expected arc point to be North of origin, got {p}"


@pytest.mark.asyncio
async def test_tool_registry_gis_tools():
    """Verify tool_registry GIS methods."""
    loc = await phantom_tool_registry.get_camera_location("cam03")
    assert loc["found"] is True
    assert "O.N.G.C." in loc["name"] or "ONGC" in loc["name"]
    assert "ONGC Office Marg" in loc["road_name"]
    assert loc["heading"] == 0.0

    # Test query by road
    road_cams = await phantom_tool_registry.query_cameras_by_road("ONGC Office Marg")
    assert len(road_cams) >= 1
    assert any("cam03" in c["id"] for c in road_cams)


@pytest.mark.asyncio
async def test_copilot_road_coverage_query():
    """Test user query: 'ONGC camera kis road ko cover karta hai?'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("ONGC camera kis road ko cover karta hai?")

    assert "ONGC Office Marg" in resp.text_response or "Road" in resp.text_response
    assert "Chandkheda" in resp.text_response or "Police" in resp.text_response
    assert any(act.action_type == "OPEN_MAP" for act in resp.ui_actions)


@pytest.mark.asyncio
async def test_copilot_satellite_view_query():
    """Test user query: 'ONGC camera ka satellite view kholo'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("ONGC camera ka satellite view kholo")

    assert any(act.action_type == "OPEN_MAP" and act.payload.get("map_mode") == "SATELLITE" for act in resp.ui_actions)
    assert "satellite" in resp.text_response.lower()


@pytest.mark.asyncio
async def test_copilot_street_view_query():
    """Test user query: 'ONGC camera ka street view dikhao'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("ONGC camera ka street view dikhao")

    assert any(act.action_type == "OPEN_MAP" and act.payload.get("map_mode") == "STREET_VIEW" for act in resp.ui_actions)
    assert "street view" in resp.text_response.lower()


@pytest.mark.asyncio
async def test_copilot_gujarati_cctv_count_query():
    """Test user query: 'ગુજરાતીમાં કહો કે અમદાવાદમાં કેટલા કેમેરા છે'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("ગુજરાતીમાં કહો કે અમદાવાદમાં કેટલા કેમેરા છે")

    assert resp.detected_language == "gu"
    assert any('\u0a80' <= ch <= '\u0aff' for ch in resp.text_response)
