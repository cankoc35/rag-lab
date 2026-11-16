"""Generator settings, API boundaries and smoke opt-in checks without network access."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

from rag_workflow_lab.config import GeneratorSettings, load_settings
from rag_workflow_lab.llm import generate_text
from scripts import llm_smoke


class GeneratorConfigTests(unittest.TestCase):
    def load(self, generator=""):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "pilot.toml"
            path.write_text('[project]\nname="test"\n[paths]\nsources_manifest="sources.json"\n'
                            'local_data_dir="local"\n' + generator, encoding="utf-8")
            return load_settings(path)

    def test_generator_is_optional_for_existing_configs(self):
        self.assertIsNone(self.load().generator)

    def test_generator_defaults_and_pilot_selection(self):
        self.assertEqual(self.load('[generator]\nmodel_id="gpt-6-luna"').generator,
                         GeneratorSettings("gpt-6-luna"))
        self.assertEqual(load_settings(llm_smoke.ROOT / "configs/pilot.toml").generator,
                         GeneratorSettings("gpt-6-luna"))

    def test_invalid_settings_fail_before_any_api_call(self):
        for section in ('[generator]', '[generator]\nmodel_id=""',
                        '[generator]\nmodel_id="gpt-6-luna"\nreasoning_effort="invalid"',
                        '[generator]\nmodel_id="gpt-6-luna"\nmax_output_tokens=true',
                        '[generator]\nmodel_id="gpt-6-luna"\nmax_output_tokens=15'):
            with self.subTest(section=section), self.assertRaises(ValueError):
                self.load(section)


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.response = SimpleNamespace(
            id="resp_fixture", model="gpt-6-luna", status="completed", output_text="Fixture answer.",
            usage=Mock(), incomplete_details=None,
        )
        self.response.usage.model_dump.return_value = {
            "input_tokens": 20, "output_tokens": 8, "total_tokens": 28,
            "output_tokens_details": {"reasoning_tokens": 0},
        }
        self.client.responses.create.return_value = self.response

    def test_one_bounded_request_preserves_provider_text_and_usage(self):
        result = generate_text(self.client, GeneratorSettings("gpt-6-luna"),
                               instructions="Use evidence.", prompt="Question and evidence.")
        self.client.responses.create.assert_called_once_with(
            model="gpt-6-luna", instructions="Use evidence.", input="Question and evidence.",
            reasoning={"effort": "none"}, max_output_tokens=1000, service_tier="default", store=False,
        )
        self.assertEqual(result["answer"], "Fixture answer.")
        self.assertEqual(result["response_id"], "resp_fixture")
        self.assertEqual(result["usage"]["total_tokens"], 28)

    def test_partial_response_and_unknown_usage_are_not_reported_as_complete_or_zero(self):
        self.response.status = "incomplete"
        self.response.incomplete_details = SimpleNamespace(reason="max_output_tokens")
        self.response.usage = None
        result = generate_text(self.client, GeneratorSettings("gpt-6-luna"), instructions="", prompt="test")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["incomplete_reason"], "max_output_tokens")
        self.assertIsNone(result["usage"])


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.stdout, self.stderr = StringIO(), StringIO()
        self.enterContext(redirect_stdout(self.stdout))
        self.enterContext(redirect_stderr(self.stderr))
        self.enterContext(patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-secret"}))
        self.api_error = type("FixtureAPIError", (Exception,), {})
        self.factory = MagicMock()
        self.enterContext(patch.dict("sys.modules", {
            "openai": SimpleNamespace(OpenAI=self.factory, OpenAIError=self.api_error),
        }))
        self.enterContext(patch.object(llm_smoke, "version", return_value="fixture-sdk"))
        self.generate = self.enterContext(patch.object(llm_smoke, "generate_text", return_value={
            "status": "completed", "answer": "Luna API smoke test passed.",
            "usage": {"input_tokens": 20, "output_tokens": 8, "total_tokens": 28},
        }))

    def test_paid_call_requires_opt_in(self):
        with self.assertRaises(SystemExit) as error:
            llm_smoke.main([])
        self.assertEqual(error.exception.code, 2)
        self.factory.assert_not_called()

    def test_missing_key_stops_before_client_creation(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}), self.assertRaises(SystemExit) as error:
            llm_smoke.main(["--call-api"])
        self.assertEqual(error.exception.code, 2)
        self.assertIn("Set OPENAI_API_KEY", self.stderr.getvalue())
        self.factory.assert_not_called()

    def test_success_prints_usage_without_credentials_and_disables_retries(self):
        self.assertEqual(llm_smoke.main(["--call-api"]), 0)
        report = json.loads(self.stdout.getvalue())
        self.assertEqual(report["configuration"]["model_id"], "gpt-6-luna")
        self.assertEqual(report["usage"]["total_tokens"], 28)
        self.assertEqual(report["prompt"], llm_smoke.PROMPT)
        self.assertNotIn("fixture-secret", self.stdout.getvalue() + self.stderr.getvalue())
        self.factory.assert_called_once_with(base_url="https://api.openai.com/v1", timeout=30, max_retries=0)
        self.generate.assert_called_once()

    def test_partial_response_keeps_the_report_but_returns_failure(self):
        self.generate.return_value["status"] = "incomplete"
        self.assertEqual(llm_smoke.main(["--call-api"]), 2)
        self.assertEqual(json.loads(self.stdout.getvalue())["status"], "incomplete")

    def test_provider_error_messages_are_not_printed(self):
        self.generate.side_effect = self.api_error("fixture-secret must stay private")
        self.assertEqual(llm_smoke.main(["--call-api"]), 2)
        self.assertIn("FixtureAPIError", self.stderr.getvalue())
        self.assertNotIn("fixture-secret", self.stdout.getvalue() + self.stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
