"""
FeePrint schemas (Pydantic v2).

Every provider describes its pricing differently: "Fee: A$3.99",
"No transfer fee", "1.2% of amount". The extractors (Beautiful Soup
first, Gemini only as a fallback) must turn that text into ONE shape,
ExtractedQuote, before anything is stored or calculated.

If a value is missing, impossible, or can't be found in the page text
it supposedly came from, validation fails and the row is rejected
instead of being shown to users.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

FeeType = Literal["fixed", "percent", "zero"]
ExtractionMethod = Literal["selector", "llm"]
CaptureStatus = Literal["ok", "failed"]

CURRENCY = r"^[A-Z]{3}$"
MAX_PERCENT_FEE = 10.0    # a % fee above this is almost certainly a parsing mistake
MAX_FIXED_FEE_SHARE = 0.10  # a fixed fee above 10% of the amount sent is suspicious
MAX_RATE_GAP = 0.05       # provider rate must be within 5% of the mid-market rate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def numbers_in(text: str) -> list[float]:
    """Every number written in a piece of text: 'A$1,000.50 fee' -> [1000.5]."""
    return [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)]


def appears_in(value: float, text: str, tolerance: float = 0.005) -> bool:
    """True if `value` is actually written in `text` (the evidence check)."""
    return any(abs(n - value) <= tolerance for n in numbers_in(text))


class StrictModel(BaseModel):
    # extra="forbid": unknown fields are an error, which matters when an
    # LLM returns something we didn't ask for.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Provider(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$", max_length=40)  # slug, e.g. "wise"
    name: str = Field(min_length=1)
    pricing_url: HttpUrl
    extractor: ExtractionMethod = "selector"


class Capture(StrictModel):
    """One page load: the evidence behind every extracted number."""

    provider_id: str
    url: HttpUrl
    fetched_at: datetime = Field(default_factory=_utcnow)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")  # SHA-256 of the saved HTML
    html_path: str = Field(min_length=1)                   # where the rendered HTML is saved
    status: CaptureStatus = "ok"


class ExtractedQuote(StrictModel):
    """One provider's price for one corridor, normalised to a common shape."""

    provider_id: str
    capture_id: Optional[int] = None
    send_currency: str = Field("AUD", pattern=CURRENCY)
    receive_currency: str = Field("INR", pattern=CURRENCY)
    send_amount: float = Field(gt=0)

    # fixed   -> fee_amount is in send_currency (e.g. 3.99 AUD)
    # percent -> fee_amount is a percentage of send_amount (e.g. 1.2)
    # zero    -> fee_amount must be 0
    fee_type: FeeType
    fee_amount: float = Field(ge=0)
    provider_rate: float = Field(gt=0)  # 1 send_currency = provider_rate receive_currency

    speed_text: str = Field(min_length=1)  # as written on the site
    speed_min_hours: Optional[float] = Field(None, ge=0)
    speed_max_hours: Optional[float] = Field(None, ge=0)

    fee_snippet: str = Field(min_length=1)   # exact page text the fee came from
    rate_snippet: str = Field(min_length=1)  # exact page text the rate came from
    method: ExtractionMethod = "selector"
    extracted_at: datetime = Field(default_factory=_utcnow)

    @field_validator("send_currency", "receive_currency", mode="before")
    @classmethod
    def _upper(cls, v):
        return v.upper() if isinstance(v, str) else v

    @model_validator(mode="after")
    def _rules(self) -> "ExtractedQuote":
        if self.send_currency == self.receive_currency:
            raise ValueError("send and receive currency must differ")

        if self.fee_type == "zero" and self.fee_amount != 0:
            raise ValueError("fee_type 'zero' needs fee_amount 0")
        if self.fee_type == "percent" and self.fee_amount > MAX_PERCENT_FEE:
            raise ValueError(f"percent fee {self.fee_amount}% is above {MAX_PERCENT_FEE}%")
        if self.fee_type == "fixed" and self.fee_amount > self.send_amount * MAX_FIXED_FEE_SHARE:
            raise ValueError(f"fixed fee {self.fee_amount} is over 10% of {self.send_amount}")

        if (
            self.speed_min_hours is not None
            and self.speed_max_hours is not None
            and self.speed_min_hours > self.speed_max_hours
        ):
            raise ValueError("speed_min_hours is greater than speed_max_hours")

        # Evidence check: each number must be written in the text it came from.
        if self.fee_type != "zero" and not appears_in(self.fee_amount, self.fee_snippet):
            raise ValueError(f"fee {self.fee_amount} not found in fee_snippet {self.fee_snippet!r}")
        if not appears_in(self.provider_rate, self.rate_snippet):
            raise ValueError(f"rate {self.provider_rate} not found in rate_snippet {self.rate_snippet!r}")
        return self


class ReferenceRate(StrictModel):
    """Mid-market rate that provider rates are compared against."""

    base_currency: str = Field("AUD", pattern=CURRENCY)
    quote_currency: str = Field("INR", pattern=CURRENCY)
    mid_rate: float = Field(gt=0)
    source: str = Field(min_length=1)
    fetched_at: datetime = Field(default_factory=_utcnow)


def check_against_mid(quote: ExtractedQuote, mid: ReferenceRate) -> list[str]:
    """Checks that need a second record. Returns problems; empty list = OK."""
    problems = []
    if (mid.base_currency, mid.quote_currency) != (quote.send_currency, quote.receive_currency):
        problems.append(
            f"reference rate is {mid.base_currency}/{mid.quote_currency}, "
            f"quote is {quote.send_currency}/{quote.receive_currency}"
        )
        return problems
    gap = abs(quote.provider_rate - mid.mid_rate) / mid.mid_rate
    if gap > MAX_RATE_GAP:
        problems.append(
            f"provider rate {quote.provider_rate} is {gap:.1%} from mid-market "
            f"{mid.mid_rate} (limit {MAX_RATE_GAP:.0%})"
        )
    return problems
