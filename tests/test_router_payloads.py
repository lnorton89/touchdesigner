import unittest

from td_components.llm_model_router import router_http
from td_components.llm_model_router.ModelRouterExt import ModelRouter


class RouterHttpTests(unittest.TestCase):
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


class ModelRouterTests(unittest.TestCase):
    def test_request_is_central_entry_point_and_marks_running(self):
        router = ModelRouter()

        request_id = router.request(prompt="hello", trigger_source="pulse")

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
        request_id = router.request(prompt="hello")
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
        first_id = router.request(prompt="hello", trigger_source="dat_change")

        reset_state = router.reset()
        retry_id = router.retry()

        self.assertEqual(reset_state["state"], "idle")
        self.assertGreater(retry_id, first_id)
        self.assertEqual(router.state["state"], "running")
        self.assertEqual(router._last_envelope["trigger_source"], "retry")


if __name__ == "__main__":
    unittest.main()
