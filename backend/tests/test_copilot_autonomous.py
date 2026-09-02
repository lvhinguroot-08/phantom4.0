"""
PHANTOM AI Copilot — Comprehensive Automated Test Suite
Validates multilingual natural language processing (EN/HI/GU/MR/Hinglish),
entity resolution, live tool execution, YOLO detection integration,
conversational memory, and UI action packaging.
"""

import asyncio
import pytest
from app.ai.agents.copilot import get_global_copilot_agent, CopilotChatResponse
from app.ai.agents.entity_resolver import entity_resolver
from app.ai.agents.tool_registry import phantom_tool_registry


@pytest.mark.asyncio
async def test_entity_resolver_camera_matching():
    """Test multi-pass camera entity resolution across aliases and languages."""
    inventory = await phantom_tool_registry.get_camera_inventory()
    assert len(inventory) >= 30, f"Expected at least 30 cameras, found {len(inventory)}"

    # 1. Test ONGC in English/Hinglish
    res_ongc = entity_resolver.resolve("ONGC office wali feed kholo", inventory)
    assert res_ongc.resolved_camera is not None
    assert "003" in res_ongc.resolved_camera.camera_id.lower() or "cam03" in res_ongc.resolved_camera.camera_id.lower() or "ongc" in res_ongc.resolved_camera.name.lower() or "o.n.g.c." in res_ongc.resolved_camera.name.lower()

    # 2. Test ONGC in Gujarati
    res_ongc_gu = entity_resolver.resolve("મને ONGC ઓફિસનો કેમેરો બતાવો", inventory)
    assert res_ongc_gu.resolved_camera is not None
    assert "003" in res_ongc_gu.resolved_camera.camera_id.lower() or "cam03" in res_ongc_gu.resolved_camera.camera_id.lower() or "ongc" in res_ongc_gu.resolved_camera.name.lower() or "o.n.g.c." in res_ongc_gu.resolved_camera.name.lower()

    # 3. Test Chimanbhai Bridge
    res_chiman = entity_resolver.resolve("01 Chiman bhai Bridge open karo", inventory)
    assert res_chiman.resolved_camera is not None
    assert "001" in res_chiman.resolved_camera.camera_id.lower() or "cam01" in res_chiman.resolved_camera.camera_id.lower() or "chiman" in res_chiman.resolved_camera.name.lower()

    # 4. Test Ambiguity (Visat matches cam05 and cam16)
    res_visat = entity_resolver.resolve("Visat camera dikhao", inventory)
    assert res_visat.is_ambiguous or len(res_visat.candidate_cameras) >= 2


@pytest.mark.asyncio
async def test_entity_resolver_license_plate_extraction():
    """Test extracting Indian vehicle registration plates."""
    res1 = entity_resolver.resolve("GJ01AB1234 ko trace karo")
    assert res1.resolved_plate == "GJ01AB1234"

    res2 = entity_resolver.resolve("GJ 01 AB 1234 vehicle trace report")
    assert res2.resolved_plate == "GJ01AB1234"


@pytest.mark.asyncio
async def test_mandatory_query_1_ongc_feed_kholo():
    """Test exact user query: 'ONGC office wali feed kholo'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("ONGC office wali feed kholo")

    assert resp.opened_camera is not None
    assert "cam03" in resp.opened_camera["id"].lower() or "ongc" in resp.opened_camera["name"].lower()
    assert any(act.action_type == "OPEN_CAMERA" for act in resp.ui_actions)
    assert len(resp.status_steps) >= 2


@pytest.mark.asyncio
async def test_mandatory_query_2_ongc_feed_detect_karo():
    """Test exact user query: 'ONGC office wali feed kholo aur person detect karo'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("ONGC office wali feed kholo aur person detect karo")

    assert resp.opened_camera is not None
    assert resp.detection_summary is not None
    assert any(act.action_type == "RUN_DETECTION" for act in resp.ui_actions)
    assert "detect" in resp.text_response.lower() or "person" in resp.text_response.lower()


@pytest.mark.asyncio
async def test_mandatory_query_3_kitne_cameras_online():
    """Test exact user query: 'Abhi kitne cameras online hain?'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("Abhi kitne cameras online hain?")

    assert "30" in resp.text_response or "online" in resp.text_response.lower()
    assert resp.data_card is not None


@pytest.mark.asyncio
async def test_mandatory_query_4_kaunse_cameras_offline():
    """Test exact user query: 'Kaunse cameras offline hain?'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("Kaunse cameras offline hain?")

    assert "offline" in resp.text_response.lower() or "100%" in resp.text_response or "0" in resp.text_response


@pytest.mark.asyncio
async def test_mandatory_query_5_system_health():
    """Test exact user query: 'System health kaisi hai?'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("System health kaisi hai?")

    assert "HEALTHY" in resp.text_response.upper() or "ONLINE" in resp.text_response.upper()
    assert any("stream" in s.label.lower() or "backend" in s.label.lower() for s in resp.status_steps)


@pytest.mark.asyncio
async def test_mandatory_query_6_anpr_detection():
    """Test exact user query: 'GJ01AB1234 ka latest detection dikhao'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("GJ01AB1234 ka latest detection dikhao")

    assert "GJ01AB1234" in resp.text_response or "GJ 01 AB 1234" in resp.text_response
    assert any(act.action_type == "OPEN_ANPR" for act in resp.ui_actions)


@pytest.mark.asyncio
async def test_mandatory_query_7_incidents():
    """Test exact user query: 'Last 24 hours mein kitne incidents hue?'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("Last 24 hours mein kitne incidents hue?")

    assert "alert" in resp.text_response.lower() or "incident" in resp.text_response.lower()
    assert resp.data_card is not None


@pytest.mark.asyncio
async def test_mandatory_query_8_map_ongc():
    """Test exact user query: 'Map par ONGC wala camera dikhao'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("Map par ONGC wala camera dikhao")

    assert any(act.action_type == "OPEN_MAP" for act in resp.ui_actions)


@pytest.mark.asyncio
async def test_mandatory_query_9_gujarati_offline():
    """Test exact user query: 'ગુજરાતીમાં કહો કે કેટલા કેમેરા offline છે'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("ગુજરાતીમાં કહો કે કેટલા કેમેરા offline છે")

    assert resp.detected_language == "gu"
    # Response contains Gujarati text
    assert any('\u0a80' <= ch <= '\u0aff' for ch in resp.text_response)


@pytest.mark.asyncio
async def test_mandatory_query_10_hindi_live():
    """Test exact user query: 'अभी कितने कैमरे live हैं?'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("अभी कितने कैमरे live हैं?")

    assert resp.detected_language in ("hi", "hinglish")
    assert "30" in resp.text_response or "कैमरे" in resp.text_response or "cameras" in resp.text_response


@pytest.mark.asyncio
async def test_mandatory_query_11_hindi_detection():
    """Test exact user query: 'भाई ONGC वाला camera खोल और detection चला'"""
    agent = get_global_copilot_agent()
    resp: CopilotChatResponse = await agent.process_query("भाई ONGC वाला camera खोल और detection चला")

    assert resp.opened_camera is not None
    assert resp.detection_summary is not None


@pytest.mark.asyncio
async def test_conversational_pronoun_context():
    """Test multi-turn context memory: 'ONGC office wala camera kholo' followed by 'Isme person detection chalao'"""
    agent = get_global_copilot_agent()
    sid = "test_conv_session_123"

    # Turn 1: Open camera
    resp1 = await agent.process_query("ONGC office wala camera kholo", session_id=sid)
    assert resp1.opened_camera is not None
    assert "cam03" in resp1.opened_camera["id"].lower() or "ongc" in resp1.opened_camera["name"].lower()

    # Turn 2: Refer to previously opened camera with pronoun "isme"
    resp2 = await agent.process_query("Isme person detection chalao", session_id=sid)
    assert resp2.opened_camera is not None
    assert resp2.opened_camera["id"] == resp1.opened_camera["id"]
    assert resp2.detection_summary is not None
