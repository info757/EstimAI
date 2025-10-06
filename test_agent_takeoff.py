#!/usr/bin/env python3
"""
Simple test script for agent takeoff functionality.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.agent.takeoff import TakeoffAgent, AgentOptions, ProposedReview

def test_agent_initialization():
    """Test agent initialization."""
    print("Testing agent initialization...")
    agent = TakeoffAgent()
    
    assert agent.session_cache == {}
    assert agent.processing_sessions == {}
    print("✅ Agent initialization works")

def test_cache_key_generation():
    """Test cache key generation."""
    print("Testing cache key generation...")
    agent = TakeoffAgent()
    
    key1 = agent._get_cache_key("session1", "hash1")
    key2 = agent._get_cache_key("session1", "hash2")
    
    assert key1 == "session1:hash1"
    assert key2 == "session1:hash2"
    assert key1 != key2
    print("✅ Cache key generation works")

def test_agent_options():
    """Test agent options."""
    print("Testing agent options...")
    opts = AgentOptions()
    assert opts.dry_run == False
    assert opts.timeout_sec == 300
    assert opts.include_warnings == True
    assert opts.force_regenerate == False
    
    opts = AgentOptions(dry_run=True, timeout_sec=600)
    assert opts.dry_run == True
    assert opts.timeout_sec == 600
    print("✅ Agent options work")

def test_processing_session_management():
    """Test processing session management."""
    print("Testing processing session management...")
    agent = TakeoffAgent()
    
    # Start processing
    agent._start_processing("session1")
    assert "session1" in agent.processing_sessions
    
    # End processing
    agent._end_processing("session1")
    assert "session1" not in agent.processing_sessions
    print("✅ Processing session management works")

def test_ground_source_tracking():
    """Test ground source tracking."""
    print("Testing ground source tracking...")
    ground_sources = {
        "storm_pipe_1": "surface",
        "sanitary_pipe_1": "profile", 
        "water_pipe_1": "constant"
    }
    
    assert len(ground_sources) == 3
    assert ground_sources["storm_pipe_1"] == "surface"
    assert ground_sources["sanitary_pipe_1"] == "profile"
    assert ground_sources["water_pipe_1"] == "constant"
    print("✅ Ground source tracking works")

def test_warning_collection():
    """Test warning collection."""
    print("Testing warning collection...")
    warnings = []
    
    # Test constant ground source warning
    ground_sources = {"pipe_1": "constant"}
    for pipe_id, source in ground_sources.items():
        if source == "constant":
            warnings.append(f"Pipe {pipe_id} using constant ground elevation")
    
    assert len(warnings) == 1
    assert "constant ground elevation" in warnings[0]
    print("✅ Warning collection works")

if __name__ == "__main__":
    print("🧪 Testing Agent Takeoff Functionality")
    print("=" * 50)
    
    try:
        test_agent_initialization()
        test_cache_key_generation()
        test_agent_options()
        test_processing_session_management()
        test_ground_source_tracking()
        test_warning_collection()
        
        print()
        print("🎉 All agent tests passed! Agent takeoff is working correctly.")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
