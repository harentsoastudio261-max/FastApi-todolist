"""Gemini implementation for AI task idea generation."""
from typing import Any

from pydantic import ValidationError

from app.core.exceptions import AIProviderException
from app.core.logging import get_logger
from app.providers.ai.helpers.task_creation_prompt import build_task_creation_prompt
from app.schemas import GeneratedTaskIdea, TaskCreationType

logger = get_logger(__name__)


class GeminiTaskIdeaProvider:
    def __init__(self, api_key: str | None, model: str):
        self.api_key = api_key
        self.model = model
        self._client: Any | None = None

    def generate_task_idea(self, task_type: TaskCreationType) -> GeneratedTaskIdea:
        prompt = build_task_creation_prompt(task_type)
        client = self._get_client()

        try:
            response = client.interactions.create(
                model=self.model,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": GeneratedTaskIdea.model_json_schema(),
                },
            )
        except Exception as exc:
            logger.exception("Gemini task generation failed for type=%s", task_type.value)
            raise AIProviderException("Gemini task generation failed", "ai_provider_error") from exc

        output_text = getattr(response, "output_text", None)
        if not output_text:
            raise AIProviderException("Gemini returned an empty response", "ai_provider_empty_response")

        try:
            return GeneratedTaskIdea.model_validate_json(output_text)
        except ValidationError as exc:
            logger.warning("Gemini returned invalid task payload: %s", output_text)
            raise AIProviderException("Gemini returned invalid task data", "ai_provider_invalid_response") from exc

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from google import genai
        except ImportError as exc:
            raise AIProviderException(
                "google-genai dependency is not installed",
                "ai_dependency_missing",
            ) from exc

        try:
            self._client = genai.Client(api_key=self.api_key) if self.api_key else genai.Client()
        except Exception as exc:
            raise AIProviderException("Unable to initialize Gemini client", "ai_provider_init_failed") from exc

        return self._client