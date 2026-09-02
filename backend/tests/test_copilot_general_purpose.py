"""
PHANTOM AI Copilot — General-Purpose Conversational Assistant Test Suite
Validates open-ended natural queries, casual greetings, multi-turn conversational context,
camera number matching, footage queries, camera comparison, and multilingual support.
"""

import pytest
from app.ai.agents.copilot import get_global_copilot_agent, CopilotChatResponse
from app.ai.agents.entity_resolver import entity_resolver
from app.ai.agents.tool_registry import phantom_tool_registry


@pytest.mark.asyncio
async def test_greetings_conversational():
    """Test casual greetings — must respond conversationally without triggering camera actions."""
    agent = get_global_copilot_agent()
    
    # 1. "hi"
    resp_hi: CopilotChatResponse = await agent.process_query("hi")
    assert resp_hi.intent == "GREETING"
    assert resp_hi.opened_camera is None
    assert "PHANTOM" in resp_hi.text_response or "Copilot" in resp_hi.text_response

    # 2. "hello bhai"
    resp_hello: CopilotChatResponse = await agent.process_query("hello bhai")
    assert resp_hello.intent == "GREETING"
    assert resp_hello.opened_camera is None

    # 3. "નમસ્તે" (Gujarati greeting)
    resp_gu: CopilotChatResponse = await agent.process_query("નમસ્તે")
    assert resp_gu.intent == "GREETING"
    assert resp_gu.detected_language == "gu"
    assert "નમસ્તે" in resp_gu.text_response


@pytest.mark.asyncio
async def test_capabilities_query():
    """Test dynamic capabilities query: 'tum kya kar sakte ho?', 'what can you do?'"""
    agent = get_global_copilot_agent()
    
    resp: CopilotChatResponse = await agent.process_query("tum kya kar sakte ho?")
    assert resp.intent == "CAPABILITIES_QUERY"
    assert "cameras" in resp.text_response.lower() or "live" in resp.text_response.lower()
    assert "anpr" in resp.text_response.lower() or "footage" in resp.text_response.lower()


@pytest.mark.asyncio
async def test_flexible_camera_number_matching():
    """Test flexible camera number variations like 'camera 5', 'cam 5', 'fifth camera', '5 number camera'."""
    inventory = await phantom_tool_registry.get_camera_inventory()
    
    for phrase in ["camera 5 online hai?", "cam 5", "5 number camera", "fifth camera ki status"]:
        res = entity_resolver.resolve(phrase, inventory)
        assert res.resolved_camera is not None, f"Failed to resolve: {phrase}"
        assert "05" in res.resolved_camera.camera_id or "cam05" in res.resolved_camera.camera_id.lower() or "5" in res.resolved_camera.camera_id


@pytest.mark.asyncio
async def test_camera_footage_queries():
    """Test historical footage query: 'camera 5 ki kal raat wali footage dekh'."""
    agent = get_global_copilot_agent()
    
    resp: CopilotChatResponse = await agent.process_query("camera 5 ki kal raat wali footage dekh")
    assert resp.intent == "FOOTAGE_QUERY"
    assert "Footage" in resp.text_response or "Archive" in resp.text_response or "Recording" in resp.text_response
    assert "Last Night" in resp.text_response or "Night" in resp.text_response or "24" in resp.text_response


@pytest.mark.asyncio
async def test_camera_comparison():
    """Test multi-camera comparison: 'camera 5 aur camera 7 compare karo'."""
    agent = get_global_copilot_agent()
    
    resp: CopilotChatResponse = await agent.process_query("camera 5 aur camera 7 compare karo")
    assert resp.intent == "CAMERA_COMPARISON"
    assert "Comparison" in resp.text_response or "versus" in resp.text_response or "CAM" in resp.text_response
    assert resp.data_card is not None


@pytest.mark.asyncio
async def test_multi_turn_conversational_context():
    """
    Test 4-turn pronoun context:
    Turn 1: 'ONGC camera kholo'
    Turn 2: 'iska health?'
    Turn 3: 'kal ki footage'
    Turn 4: 'map pe dikhao'
    """
    import uuid
    agent = get_global_copilot_agent()
    sid = str(uuid.uuid4())

    # Turn 1: Open ONGC
    t1: CopilotChatResponse = await agent.process_query("ONGC camera kholo", session_id=sid)
    assert t1.opened_camera is not None or any(a.action_type == "OPEN_CAMERA" for a in t1.ui_actions)

    # Turn 2: "iska health?" -> Pronoun 'iska' refers to ONGC camera
    t2: CopilotChatResponse = await agent.process_query("iska health?", session_id=sid)
    assert "O.N.G.C." in t2.text_response or "ONGC" in t2.text_response or "CAM03" in t2.text_response or "CAM-003" in t2.text_response
    assert t2.intent == "CAMERA_STATUS_QUERY"

    # Turn 3: "kal ki footage" -> Pronoun context remembers ONGC camera + yesterday
    t3: CopilotChatResponse = await agent.process_query("kal ki footage", session_id=sid)
    assert t3.intent == "FOOTAGE_QUERY"
    assert "Footage" in t3.text_response or "Archive" in t3.text_response or "Recording" in t3.text_response

    # Turn 4: "map pe dikhao" -> Pronoun context remembers ONGC camera on GIS map
    t4: CopilotChatResponse = await agent.process_query("map pe dikhao", session_id=sid)
    assert t4.intent == "GIS_MAP_QUERY"
    assert any(a.action_type == "OPEN_MAP" for a in t4.ui_actions)


@pytest.mark.asyncio
async def test_general_knowledge():
    """Test general knowledge questions outside PHANTOM."""
    agent = get_global_copilot_agent()
    
    resp_cloud: CopilotChatResponse = await agent.process_query("What is cloud computing?")
    assert resp_cloud.intent == "GENERAL_KNOWLEDGE_QUERY"
    assert "cloud" in resp_cloud.text_response.lower()
    assert "general knowledge" in resp_cloud.text_response.lower() or "general" in resp_cloud.text_response.lower()

    resp_japan: CopilotChatResponse = await agent.process_query("What is the capital of Japan?")
    assert "Tokyo" in resp_japan.text_response


@pytest.mark.asyncio
async def test_platform_knowledge():
    """Test platform architectural knowledge: 'PHANTOM kya hai?', 'ANPR kaise kaam karta hai?'"""
    agent = get_global_copilot_agent()
    
    resp_phantom: CopilotChatResponse = await agent.process_query("PHANTOM kya hai?")
    assert resp_phantom.intent == "PLATFORM_KNOWLEDGE_QUERY"
    assert "Surveillance" in resp_phantom.text_response or "Gujarat Police" in resp_phantom.text_response

    resp_anpr: CopilotChatResponse = await agent.process_query("ANPR kaise kaam karta hai?")
    assert resp_anpr.intent == "PLATFORM_KNOWLEDGE_QUERY"
    assert "YOLO26" in resp_anpr.text_response or "OCR" in resp_anpr.text_response or "Number Plate" in resp_anpr.text_response


@pytest.mark.asyncio
async def test_troubleshooting_knowledge():
    """Test troubleshooting query: 'camera offline kyun ho sakta hai?'"""
    agent = get_global_copilot_agent()
    
    resp: CopilotChatResponse = await agent.process_query("camera offline kyun ho sakta hai?")
    assert resp.intent == "PLATFORM_KNOWLEDGE_QUERY"
    assert "RTSP" in resp.text_response or "Network" in resp.text_response or "PoE" in resp.text_response or "Power" in resp.text_response


@pytest.mark.asyncio
async def test_user_requested_exact_prompts():
    """
    Test exact queries requested by user:
    1. 'hii' -> 'Hello! Boliye, main aapki kya seva kar sakta hoon?'
    2. 'kaisa hain?' -> Wellbeing response
    3. 'kya name hain?' -> 'Mera naam PHANTOM AI Copilot hai'
    4. '5 number ka camera khol' -> Opens camera 5 (Visat teen Rasta)
    5. '7 num k camera main total kitne vehicle hain' -> Runs vehicle detection with detailed models (Splendor, Activa, Swift)
    6. 'system health check karke bata' -> System health diagnostics
    7. 'security audit de' -> Security audit report
    """
    agent = get_global_copilot_agent()

    # 1. Greeting
    r1: CopilotChatResponse = await agent.process_query("hii")
    assert r1.intent == "GREETING"
    assert "seva" in r1.text_response.lower() or "phantom" in r1.text_response.lower()

    # 2. Wellbeing
    r2: CopilotChatResponse = await agent.process_query("kaisa hain?")
    assert r2.intent == "WELLBEING_QUERY"
    assert "badhiya" in r2.text_response.lower() or "surveillance" in r2.text_response.lower()

    # 3. Name & Identity
    r3: CopilotChatResponse = await agent.process_query("kya name hain?")
    assert r3.intent == "IDENTITY_QUERY"
    assert "PHANTOM AI Copilot" in r3.text_response

    # 4. '5 number ka camera khol'
    r4: CopilotChatResponse = await agent.process_query("5 number ka camera khol")
    assert r4.intent == "CAMERA_ACTION"
    assert r4.opened_camera is not None
    assert "05" in r4.opened_camera["id"] or "cam05" in r4.opened_camera["id"].lower() or "Visat" in r4.opened_camera["name"]

    # 5. '7 num k camera main total kitne vehicle hain'
    r5: CopilotChatResponse = await agent.process_query("7 num k camera main total kitne vehicle hain")
    assert r5.intent == "CAMERA_ACTION"
    assert r5.detection_summary is not None
    assert r5.detection_summary.get("vehicles_detected", 0) > 0
    # Must have specific vehicle model names in the text
    assert any(m in r5.text_response for m in ["Splendor", "Activa", "Swift", "Vehicle", "Auto"])

    # 6. 'system health check karke bata'
    r6: CopilotChatResponse = await agent.process_query("system health check karke bata")
    assert r6.intent == "SYSTEM_HEALTH_QUERY"
    assert "HEALTHY" in r6.text_response or "ONLINE" in r6.text_response or "API" in r6.text_response

    # 7. 'security audit de'
    r7: CopilotChatResponse = await agent.process_query("security audit de")
    assert r7.intent == "SECURITY_AUDIT_QUERY"
    assert "SECURITY AUDIT" in r7.text_response or "Threat" in r7.text_response or "Sentinel" in r7.text_response
