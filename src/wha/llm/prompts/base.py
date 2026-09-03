"""Base prompt definition with mandatory six-component structure."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from wha.errors import LLMUnavailable
from wha.llm.client import Prompt

PROMPT_MAX_CHARS = 16000  # Character budget ceiling to prevent silent context overflow


class PromptDefinition(BaseModel):
    """Structured prompt specification carrying all six mandatory components."""

    model_config = ConfigDict(frozen=True)

    prompt_id: str
    prompt_version: str = "1"
    temperature: float = 0.0

    # The Six Mandatory Components
    instruction: str
    context_template: str
    output_schema: str
    constraints: list[str] = Field(default_factory=list)
    examples: list[dict[str, Any]] = Field(default_factory=list)
    refusal_conditions: list[str] = Field(default_factory=list)

    def render(self, context_vars: dict[str, Any] | None = None) -> Prompt:
        """Render prompt with context variables, raising on oversize rather than truncating."""
        ctx_dict = context_vars or {}
        try:
            rendered_context = self.context_template.format(**ctx_dict)
        except (KeyError, IndexError, ValueError) as exc:
            # Refuse rather than fall back to the unrendered template. A caller that
            # forgets a key used to ship the literal text "{facts}" to the model, and the
            # only visible symptom was a worse answer. It also silently disarmed the
            # oversize guard below, because the unrendered template is always short.
            raise LLMUnavailable(
                f"Prompt '{self.prompt_id}' is missing a context variable: {exc}. "
                "Refusing to send a partially rendered prompt."
            ) from exc

        constraints_text = "\n".join(f"- {c}" for c in self.constraints)
        refusal_text = "\n".join(f"- {r}" for r in self.refusal_conditions)
        examples_text = str(self.examples)

        system_msg = (
            f"# INSTRUCTION\n{self.instruction}\n\n"
            f"# CONSTRAINTS\n{constraints_text}\n\n"
            f"# REFUSAL CONDITIONS\n{refusal_text}\n\n"
            f"# OUTPUT SCHEMA\n{self.output_schema}\n\n"
            f"# EXAMPLES\n{examples_text}"
        )

        user_msg = f"# CONTEXT\n{rendered_context}"

        total_length = len(system_msg) + len(user_msg)
        if total_length > PROMPT_MAX_CHARS:
            raise LLMUnavailable(
                f"Prompt '{self.prompt_id}' exceeded character budget: "
                f"{total_length} chars > max {PROMPT_MAX_CHARS} chars. Refusing to truncate silently."
            )

        return Prompt(
            prompt_id=self.prompt_id,
            prompt_version=self.prompt_version,
            system=system_msg,
            user=user_msg,
        )
