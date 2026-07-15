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
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
