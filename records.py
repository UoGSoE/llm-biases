from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Trial(BaseModel):
    """One prompt sent to one model, with the ground truth recorded at
    generation time. Analysis reads these records only — never the prompt text.
    """

    eval_name: str
    pair_id: str
    first_option: str
    second_option: str
    condition: str  # "baseline" or "stated"
    stated_preference: str | None = None
    prompt: str
    model: str
    repeat_index: int
    response: str | None = None
    error: str | None = None
    cost: float | None = None  # USD via litellm's price map; None when unmapped
    # Usage as reported by the provider; None when it reports nothing.
    # reasoning_tokens is billed hidden thinking — often the real cost driver,
    # and invisible in the response text.
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    # Build time by default; the runner overwrites this with the completion
    # time once a response (or error) lands, so it reads as "when answered".
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
