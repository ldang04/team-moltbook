"""Shared constants, paths, word lists, and HTTP/NLP helpers for the RQ2 pipeline."""

from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import requests

ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"
DATA_FEATURES = ROOT / "data" / "features"
DATA_ANALYSIS = ROOT / "data" / "analysis"
FIGURES = ROOT / "figures"

API_BASE = "https://www.moltbook.com/api/v1"

AGENTS: list[str] = [
    "oracle-teammoltbook",
    "explainer-teammoltbook",
    "contrarian-teammoltbook",
    "mirror-teammoltbook",
    "baselineagent",
]
CONTROL_AGENT = "baselineagent"

# Phrase order matters: longer phrases must be checked before their substrings
# so "I think" doesn't get double-counted as "think" when we use a single sweep.
HEDGE_PHRASES: list[str] = [
    "could be",
    "i think",
    "it seems",
    "in a way",
    "maybe",
    "perhaps",
    "possibly",
    "might",
    "arguably",
]

CERTAINTY_PHRASES: list[str] = [
    "without question",
    "in fact",
    "the truth is",
    "clearly",
    "obviously",
    "definitely",
    "certainly",
    "undoubtedly",
]

CONTRADICTION_PHRASES: list[str] = [
    "on the contrary",
    "i'd push back",
    "the problem with",
    "i disagree",
    "that's not",
    "to be fair",
    "that said",
    "however",
    "actually",
    "but",
]

NEGATION_TOKENS: set[str] = {
    "not",
    "no",
    "don't",
    "isn't",
    "can't",
    "won't",
    "neither",
    "nor",
}

# Small stopword list used only for Jaccard lexical overlap so the score
# reflects content words, not English glue.
STOPWORDS: set[str] = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "i",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
    "you",
    "your",
}


# ---------------------------------------------------------------------------
# .env loader (no external dep)
# ---------------------------------------------------------------------------


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Best-effort .env loader. Real env vars always win."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


@dataclass
class HttpResponse:
    status: int
    data: Any


class MoltbookClient:
    """Thin requests wrapper with Bearer auth, polite delay, and 429 backoff."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = API_BASE,
        delay: float = 0.5,
        max_retries: int = 6,
        timeout: float = 30.0,
        log: Any = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.delay = delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.api_key = api_key
        self._auth_failed_unauthed = False
        self._log = log or (lambda msg: print(msg, file=sys.stderr))
        self._session = requests.Session()

    def _headers(self, force_auth: bool) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "openclaw-rq2/1.0"}
        if force_auth and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def get(self, path: str, params: dict[str, Any] | None = None) -> HttpResponse:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        attempt = 0
        # Try unauthed once, then promote to authed if 401/403 came back.
        force_auth = self._auth_failed_unauthed and bool(self.api_key)
        while True:
            time.sleep(self.delay)
            try:
                resp = self._session.get(
                    url,
                    params=params,
                    headers=self._headers(force_auth),
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                if attempt >= 3:
                    raise
                wait = min(30.0, (2**attempt) + random.random())
                self._log(f"[http] {exc!r} — retrying in {wait:.1f}s")
                time.sleep(wait)
                attempt += 1
                continue

            if resp.status_code in (401, 403) and not force_auth and self.api_key:
                self._auth_failed_unauthed = True
                force_auth = True
                self._log(f"[http] {resp.status_code} unauthed — retrying with Bearer")
                continue

            if resp.status_code == 429:
                if attempt >= self.max_retries:
                    raise RuntimeError(f"429 ratelimited after {attempt} retries: {url}")
                # Honor Retry-After if present, otherwise exponential backoff.
                ra = resp.headers.get("Retry-After")
                wait = float(ra) if ra and ra.isdigit() else min(60.0, 2**attempt)
                self._log(f"[http] 429 {url} — backing off {wait:.1f}s")
                time.sleep(wait)
                attempt += 1
                continue

            if 500 <= resp.status_code < 600:
                if attempt >= 3:
                    raise RuntimeError(
                        f"5xx after retries: {resp.status_code} {url}: {resp.text[:200]}"
                    )
                wait = min(30.0, (2**attempt) + random.random())
                self._log(f"[http] {resp.status_code} — retrying in {wait:.1f}s")
                time.sleep(wait)
                attempt += 1
                continue

            if resp.status_code == 404:
                return HttpResponse(status=404, data=None)

            if resp.status_code >= 400:
                raise RuntimeError(
                    f"HTTP {resp.status_code} {url}: {resp.text[:300]}"
                )

            try:
                return HttpResponse(status=resp.status_code, data=resp.json())
            except ValueError:
                raise RuntimeError(f"non-JSON response from {url}: {resp.text[:200]}")


def make_client(delay: float = 0.5) -> MoltbookClient:
    load_dotenv()
    api_key = os.environ.get("MOLTBOOK_API_KEY") or None
    return MoltbookClient(api_key=api_key, delay=delay)


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# NLP helpers
# ---------------------------------------------------------------------------


_WORD_RE = re.compile(r"[A-Za-z']+")
_SENT_RE = re.compile(r"[.!?]+(?=\s|$)")
_BULLET_RE = re.compile(r"^\s*([-*]|\d+\.)\s", re.MULTILINE)
_HEADER_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)
_FENCE_RE = re.compile(r"^```", re.MULTILINE)


def tokenize_words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_RE.split(text) if p and p.strip()]
    return parts


def count_phrases(text: str, phrases: Iterable[str]) -> int:
    """Case-insensitive, non-overlapping phrase count.

    Uses word boundaries where the phrase starts/ends with an alphabetic
    character so "but" doesn't match "button". Apostrophes and spaces are
    handled as literal text inside phrases.
    """
    if not text:
        return 0
    lower = text.lower()
    total = 0
    for phrase in phrases:
        p = phrase.lower()
        # Word-boundary on alphabetic edges only.
        left = r"\b" if p[:1].isalpha() else ""
        right = r"\b" if p[-1:].isalpha() else ""
        pattern = left + re.escape(p) + right
        total += len(re.findall(pattern, lower))
    return total


def count_negations(text: str) -> int:
    if not text:
        return 0
    tokens = re.findall(r"[A-Za-z']+", text.lower())
    return sum(1 for t in tokens if t in NEGATION_TOKENS)


def has_bullets(text: str) -> bool:
    return bool(text) and bool(_BULLET_RE.search(text))


def has_headers(text: str) -> bool:
    return bool(text) and bool(_HEADER_RE.search(text))


def count_formatting_elements(text: str) -> int:
    if not text:
        return 0
    bullets = len(_BULLET_RE.findall(text))
    headers = len(_HEADER_RE.findall(text))
    fences = len(_FENCE_RE.findall(text))
    # Each fenced code block is 2 fence lines (open + close); approximate.
    return bullets + headers + (fences // 2)


def avg_word_length(text: str) -> float:
    tokens = tokenize_words(text)
    if not tokens:
        return 0.0
    return sum(len(t) for t in tokens) / len(tokens)


def jaccard_overlap(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    sa = {t for t in tokenize_words(a) if t not in STOPWORDS}
    sb = {t for t in tokenize_words(b) if t not in STOPWORDS}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# ---------------------------------------------------------------------------
# Sentiment singletons (lazy)
# ---------------------------------------------------------------------------

_vader = None
_textblob_ready = False


def vader_compound(text: str) -> float:
    global _vader
    if _vader is None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        _vader = SentimentIntensityAnalyzer()
    if not text:
        return 0.0
    return float(_vader.polarity_scores(text)["compound"])


def textblob_subjectivity(text: str) -> float:
    global _textblob_ready
    if not _textblob_ready:
        _ensure_textblob_corpora()
        _textblob_ready = True
    if not text:
        return 0.0
    from textblob import TextBlob

    return float(TextBlob(text).sentiment.subjectivity)


def _ensure_textblob_corpora() -> None:
    """TextBlob's POS tagger needs NLTK punkt + averaged_perceptron_tagger.

    We do a guarded check so users don't have to remember the manual step.
    """
    try:
        import nltk  # type: ignore

        for resource in ("tokenizers/punkt", "taggers/averaged_perceptron_tagger"):
            try:
                nltk.data.find(resource)
            except LookupError:
                name = resource.split("/", 1)[1]
                print(f"[common] downloading NLTK corpus: {name}", file=sys.stderr)
                nltk.download(name, quiet=True)
    except Exception as exc:  # pragma: no cover
        print(f"[common] NLTK corpus check skipped: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def parse_agent_arg(value: str | None) -> list[str]:
    if not value:
        return list(AGENTS)
    return [s.strip() for s in value.split(",") if s.strip()]


def minmax_normalize(values: dict[str, float]) -> dict[str, float]:
    """Min-max scale the dict to [0, 1]; returns 0.5 for all if range is 0."""
    if not values:
        return {}
    lo = min(values.values())
    hi = max(values.values())
    if hi == lo:
        return {k: 0.5 for k in values}
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}
