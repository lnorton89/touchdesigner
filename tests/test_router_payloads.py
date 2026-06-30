import unittest

from td_components.llm_model_router import router_http
from td_components.llm_model_router import router_callbacks
from td_components.llm_model_router.ModelRouterExt import ModelRouter


class FakeResponse:
    def __init__(self, status, text):
        self.status = status
        self._text = text

    def read(self):
        return self._text.encode("utf-8")


class RouterHttpTests(unittest.TestCase):
    def test_llamacpp_is_valid_provider(self):
        envelope = router_http.build_request_envelope(
            provider="llama.cpp", prompt="hello"
        )
        self.assertEqual(envelope["provider"], "llama.cpp")
        self.assertEqual(envelope["base_url"], router_http.LLAMACPP_BASE_URL.rstrip("/"))

    def test_llamacpp_base_url_defaults_to_8080(self):
        envelope = router_http.build_request_envelope(
            provider="llama.cpp", prompt="test"
        )
        self.assertIn("127.0.0.1:8080", envelope["base_url"])

    def test_unsupported_provider_raises_error(self):
        with self.assertRaises(router_http.RouterConfigError):
            router_http.build_request_envelope(provider="invalid_provider", prompt="x")

    def test_openai_compatible_response_extracts_text(self):
        envelope = router_http.build_request_envelope(prompt="hello")
        payload = {"choices": [{"message": {"content": "world"}}]}

        result = router_http.success_payload(envelope, payload)

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["response_text"], "world")
        self.assertEqual(result["request_id"], envelope["request_id"])

    def test_http_status_normalizes_to_error_payload(self):
        envelope = router_http.build_request_envelope(prompt="hello")

        result = router_http.normalize_http_response(
            envelope, status_code=500, text="server failed"
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_kind"], "http_status")
        self.assertIn("500", result["error_text"])

    def test_malformed_response_normalizes_to_error_payload(self):
        envelope = router_http.build_request_envelope(prompt="hello")

        result = router_http.normalize_http_response(
            envelope, status_code=200, json_data={"choices": []}
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_kind"], "malformed_response")

    def test_timeout_and_connection_exceptions_are_classified(self):
        class TimeoutErrorForTest(Exception):
            pass

        class ConnectionRefusedForTest(Exception):
            pass

        self.assertEqual(
            router_http.classify_exception(TimeoutErrorForTest("timed out")), "timeout"
        )
        self.assertEqual(
            router_http.classify_exception(ConnectionRefusedForTest("connection refused")),
            "connection",
        )

    def test_retry_preserves_config_and_increments_identity(self):
        first = router_http.build_request_envelope(
            prompt="try once",
            base_url="http://localhost:11434/v1",
            model="demo-model",
            callback_target="callbacks",
        )

        retry = router_http.rebuild_retry_envelope(first)

        self.assertEqual(retry["base_url"], first["base_url"])
        self.assertEqual(retry["model"], first["model"])
        self.assertEqual(retry["callback_target"], first["callback_target"])
        self.assertEqual(retry["messages"], first["messages"])
        self.assertGreater(retry["request_id"], first["request_id"])
        self.assertEqual(retry["trigger_source"], "retry")

    def test_call_openai_compatible_posts_chat_completion(self):
        calls = []

        def opener(request, timeout):
            calls.append((request, timeout))
            return FakeResponse(200, '{"choices":[{"message":{"content":"ok"}}]}')

        envelope = router_http.build_request_envelope(
            prompt="hello",
            base_url="http://localhost:11434/v1",
            model="demo-model",
            timeout=12,
        )

        result = router_http.call_openai_compatible(envelope, opener=opener)

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["response_text"], "ok")
        self.assertEqual(result["base_url"], "http://localhost:11434/v1")
        self.assertEqual(result["model"], "demo-model")
        self.assertEqual(calls[0][0].full_url, "http://localhost:11434/v1/chat/completions")
        self.assertEqual(calls[0][1], 12)

    def test_call_openai_compatible_malformed_json_is_error(self):
        envelope = router_http.build_request_envelope(prompt="hello")

        result = router_http.call_openai_compatible(
            envelope, opener=lambda request, timeout: FakeResponse(200, "not json")
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_kind"], "malformed_json")


class ModelRouterTests(unittest.TestCase):
    def test_request_is_central_entry_point_and_marks_running(self):
        router = ModelRouter()

        request_id = router.request(prompt="hello", trigger_source="pulse", dispatch=False)

        self.assertGreater(request_id, 0)
        self.assertTrue(router.state["running"])
        self.assertEqual(router.state["request_id"], request_id)

    def test_config_keys_include_touchdesigner_surface(self):
        expected = {
            "provider",
            "base_url",
            "model",
            "timeout",
            "prompt_dat",
            "callback_target",
            "callback_method",
            "api_key_source",
            "trigger_pulse",
            "reset_pulse",
            "retry_pulse",
            "status_display",
        }

        self.assertEqual(set(ModelRouter.CONFIG_PARAM_NAMES), expected)

    def test_state_exposes_required_lifecycle_fields(self):
        router = ModelRouter()

        self.assertEqual(router.state["state"], "idle")
        request_id = router.request(prompt="hello", dispatch=False)
        router.apply_result(
            {
                "request_id": request_id,
                "status": "complete",
                "response_text": "done",
                "error_text": "",
            }
        )

        self.assertEqual(router.state["state"], "complete")
        self.assertFalse(router.state["running"])
        self.assertTrue(router.state["done"])
        self.assertEqual(router.state["complete_count"], 1)
        self.assertEqual(router.state["error_count"], 0)

    def test_reset_clears_runtime_state_but_retry_preserves_last_request(self):
        router = ModelRouter()
        first_id = router.request(
            prompt="hello", trigger_source="dat_table_change", dispatch=False
        )
        router.apply_result(
            {
                "request_id": first_id,
                "status": "error",
                "response_text": "",
                "error_text": "expected test error",
            }
        )

        reset_state = router.reset()
        retry_id = router.retry(dispatch=False)

        self.assertEqual(reset_state["state"], "idle")
        self.assertEqual(reset_state["complete_count"], 0)
        self.assertEqual(reset_state["error_count"], 0)
        self.assertEqual(reset_state["response_text"], "")
        self.assertEqual(reset_state["error_text"], "")
        self.assertGreater(retry_id, first_id)
        self.assertEqual(router.state["state"], "running")
        self.assertEqual(router._last_envelope["trigger_source"], "retry")
        self.assertEqual(router.state["retry_count"], 1)
        self.assertEqual(router.state["status_channels"]["retry_count"], 1)

    def test_apply_result_owns_callback_payload_and_output_state(self):
        class CallbackTarget:
            def __init__(self):
                self.payloads = []

            def onRouterResult(self, payload):
                self.payloads.append(payload)

        target = CallbackTarget()
        router = ModelRouter()
        router._last_envelope = {
            "callback_target": target,
            "callback_method": "onRouterResult",
        }
        router._active_request_id = 10

        router._apply_result(
            {
                "request_id": 10,
                "status": "complete",
                "response_text": "done",
                "error_text": "",
                "elapsed_ms": 5,
                "trigger_source": "pulse",
            }
        )

        self.assertEqual(router.state["response_text"], "done")
        self.assertEqual(router.state["status_channels"]["done"], 1)
        self.assertEqual(target.payloads[0]["request_id"], 10)

    def test_stale_result_is_ignored(self):
        router = ModelRouter()
        newer_id = router.request(prompt="new", dispatch=False)

        router._apply_result(
            {
                "request_id": newer_id - 1,
                "status": "complete",
                "response_text": "old",
                "error_text": "",
            }
        )

        self.assertEqual(router.state["state"], "running")
        self.assertEqual(router.state["response_text"], "")

    def test_callback_helpers_call_central_router_methods(self):
        class RouterSpy:
            def __init__(self):
                self.calls = []

            def request(self, **kwargs):
                self.calls.append(("request", kwargs))
                return 101

            def reset(self):
                self.calls.append(("reset", {}))
                return {}

            def retry(self):
                self.calls.append(("retry", {}))
                return 102

        class Ext:
            pass

        class Owner:
            pass

        class Par:
            pass

        owner = Owner()
        owner.ext = Ext()
        owner.ext.ModelRouter = RouterSpy()
        par = Par()
        par.owner = owner

        self.assertEqual(router_callbacks.onTriggerPulse(par), 101)
        router_callbacks.onResetPulse(par)
        self.assertEqual(router_callbacks.onRetryPulse(par), 102)

        self.assertEqual(
            owner.ext.ModelRouter.calls[0],
            ("request", {"trigger_source": "pulse"}),
        )
        self.assertEqual(owner.ext.ModelRouter.calls[1][0], "reset")
        self.assertEqual(owner.ext.ModelRouter.calls[2][0], "retry")

    def test_dat_table_change_uses_distinct_trigger_source(self):
        class RouterSpy:
            def __init__(self):
                self.kwargs = None

            def request(self, **kwargs):
                self.kwargs = kwargs
                return 201

        class Ext:
            pass

        class Dat:
            text = "from table"

        class Owner:
            pass

        owner = Owner()
        owner.ext = Ext()
        owner.ext.ModelRouter = RouterSpy()
        dat = Dat()
        dat.owner = owner

        router_callbacks.onPromptTableChange(dat)

        self.assertEqual(owner.ext.ModelRouter.kwargs["prompt"], "from table")
        self.assertEqual(
            owner.ext.ModelRouter.kwargs["trigger_source"], "dat_table_change"
        )


if __name__ == "__main__":
    unittest.main()
