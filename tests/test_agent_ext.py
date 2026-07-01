import json
import unittest

from td_components.llm_agent.AgentExt import LLMAgent
from td_components.llm_model_router.ModelRouterExt import ModelRouter


class FakeDat:
    def __init__(self, text=""):
        self.text = text


class FakeRouter:
    def __init__(self):
        self.calls = []
        self.next_request_id = 42

    def build_request_envelope(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "request_id": self.next_request_id,
            "provider": "openai_compatible",
            "base_url": "http://localhost:11434/v1",
            "model": "demo-model",
            "timeout": 30.0,
            "messages": kwargs["messages"],
            "trigger_source": kwargs["trigger_source"],
        }

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return self.next_request_id


class AgentTests(unittest.TestCase):
    def test_agent_builds_system_history_and_user_messages(self):
        router = FakeRouter()
        agent = LLMAgent(router=router)
        agent.append_history("user", "hello")
        agent.append_history("assistant", "hi")

        request_id = agent.send(
            "what next?",
            system_prompt="You are inside TouchDesigner.",
            dispatch=False,
        )

        self.assertEqual(request_id, 42)
        self.assertEqual(router.calls[0]["trigger_source"], "agent")
        self.assertEqual(
            router.calls[0]["messages"],
            [
                {"role": "system", "content": "You are inside TouchDesigner."},
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
                {"role": "user", "content": "what next?"},
            ],
        )

    def test_agent_apply_result_appends_assistant_and_writes_outputs(self):
        class Parent:
            def __init__(self):
                self.children = {
                    "agent_response": FakeDat(),
                    "agent_response_json": FakeDat(),
                    "agent_error": FakeDat(),
                    "agent_status_json": FakeDat(),
                    "agent_history": FakeDat(),
                }

            def op(self, name):
                return self.children.get(name)

        class Owner:
            def __init__(self, parent):
                self._parent = parent

            def parent(self):
                return self._parent

        parent = Parent()
        agent = LLMAgent(ownerComp=Owner(parent), router=FakeRouter())
        request_id = agent.send("hello", dispatch=False)

        state = agent.apply_result(
            {
                "request_id": request_id,
                "status": "complete",
                "response_text": "agent ready",
                "error_text": "",
            }
        )

        self.assertEqual(state["state"], "complete")
        self.assertEqual(agent.history[-1], {"role": "assistant", "content": "agent ready"})
        self.assertEqual(parent.children["agent_response"].text, "agent ready")
        self.assertIn('"response_ready": 1', parent.children["agent_status_json"].text)
        self.assertEqual(
            json.loads(parent.children["agent_history"].text),
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "agent ready"},
            ],
        )

    def test_agent_reads_message_dat_from_owner_parent(self):
        class Parent:
            def __init__(self):
                self.children = {"agent_message": FakeDat("from dat")}

            def op(self, name):
                return self.children.get(name)

        class Owner:
            def parent(self):
                return Parent()

        router = FakeRouter()
        agent = LLMAgent(ownerComp=Owner(), router=router)

        agent.send(dispatch=False)

        self.assertEqual(router.calls[0]["messages"][-1], {"role": "user", "content": "from dat"})

    def test_agent_passes_router_config_overrides(self):
        router = FakeRouter()
        agent = LLMAgent(router=router)

        agent.send(
            "use a different model",
            dispatch=False,
            config_overrides={
                "base_url": "http://127.0.0.1:8080/v1",
                "model": "local-test",
            },
        )

        self.assertEqual(
            router.calls[0]["config_overrides"],
            {"base_url": "http://127.0.0.1:8080/v1", "model": "local-test"},
        )

    def test_agent_dispatch_worker_applies_router_http_result(self):
        router = FakeRouter()
        agent = LLMAgent(router=router)

        class PatchResult:
            def __init__(self):
                self.calls = []

            def __call__(self, envelope):
                self.calls.append(envelope)
                return {
                    "request_id": envelope["request_id"],
                    "status": "complete",
                    "response_text": "from worker",
                    "error_text": "",
                }

        patch_result = PatchResult()
        original = __import__(
            "td_components.llm_agent.AgentExt", fromlist=["router_http"]
        ).router_http.call_openai_compatible
        try:
            __import__(
                "td_components.llm_agent.AgentExt", fromlist=["router_http"]
            ).router_http.call_openai_compatible = patch_result
            request_id = agent.send("hello", dispatch=True)
            while agent.state["running"]:
                pass
        finally:
            __import__(
                "td_components.llm_agent.AgentExt", fromlist=["router_http"]
            ).router_http.call_openai_compatible = original

        self.assertEqual(request_id, 42)
        self.assertEqual(agent.state["response_text"], "from worker")
        self.assertEqual(agent.state["status_channels"]["response_ready"], 1)

    def test_clear_history_resets_visible_state(self):
        agent = LLMAgent(router=FakeRouter())
        agent.append_history("user", "old")
        agent.send("new", dispatch=False)

        state = agent.clear_history()

        self.assertEqual(state["state"], "idle")
        self.assertEqual(state["history"], [])
        self.assertEqual(state["status_channels"]["history_length"], 0)


class RouterOverrideTests(unittest.TestCase):
    def test_model_router_request_accepts_per_request_overrides(self):
        router = ModelRouter()

        router.request(
            prompt="hello",
            dispatch=False,
            config_overrides={
                "base_url": "http://127.0.0.1:8080/v1",
                "model": "override-model",
                "timeout": 5,
            },
        )

        self.assertEqual(router._last_envelope["base_url"], "http://127.0.0.1:8080/v1")
        self.assertEqual(router._last_envelope["model"], "override-model")
        self.assertEqual(router._last_envelope["timeout"], 5.0)


if __name__ == "__main__":
    unittest.main()
