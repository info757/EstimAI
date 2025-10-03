# backend/tests/test_scope_agent_contract.py
import asyncio
import types

from backend.app.agents import scope_agent
from backend.app.models.schemas import ScopeOutput


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_scope_agent_returns_valid_output_with_list_scopes(monkeypatch):
    async def fake_llm_call_json(*, prompt, context, schema):
        return {
            "project_id": context["project_id"],
            "scopes": [
                {
                    "trade": "Concrete",
                    "inclusions": ["Place 3000 psi slab"],
                    "exclusions": ["Vapor barrier"],
                    "clarifications": ["GC provides layout"],
                }
            ],
        }

    # Patch the function the agent actually calls
    monkeypatch.setattr(scope_agent, "llm_call_json", fake_llm_call_json)
    out = run(scope_agent.run("P1"))
    assert isinstance(out, ScopeOutput)
    assert out.project_id == "P1"
    assert isinstance(out.scopes, list)
    assert len(out.scopes) == 1
    assert out.scopes[0].trade == "Concrete"


def test_scope_agent_normalizes_missing_scopes_to_empty_list(monkeypatch):
    async def fake_llm_call_json(*, prompt, context, schema):
        # No "scopes" key returned
        return {"project_id": context["project_id"]}

    monkeypatch.setattr(scope_agent, "llm_call_json", fake_llm_call_json)
    out = run(scope_agent.run("P2"))
    assert isinstance(out, ScopeOutput)
    assert out.project_id == "P2"
    assert isinstance(out.scopes, list)
    assert out.scopes == []


def test_scope_agent_normalizes_bad_scopes_type(monkeypatch):
    async def fake_llm_call_json(*, prompt, context, schema):
        # Bad type: model returned a number instead of an array
        return {"project_id": context["project_id"], "scopes": 0}

    monkeypatch.setattr(scope_agent, "llm_call_json", fake_llm_call_json)
    out = run(scope_agent.run("P3"))
    assert isinstance(out, ScopeOutput)
    assert out.project_id == "P3"
    assert isinstance(out.scopes, list)
    assert out.scopes == []


def test_scope_agent_fallback_when_model_returns_non_dict(monkeypatch):
    async def fake_llm_call_json(*, prompt, context, schema):
        # Totally malformed return
        return "not a dict"

    monkeypatch.setattr(scope_agent, "llm_call_json", fake_llm_call_json)
    out = run(scope_agent.run("P4"))
    assert isinstance(out, ScopeOutput)
    assert out.project_id == "P4"
    assert isinstance(out.scopes, list)
    assert out.scopes == []


