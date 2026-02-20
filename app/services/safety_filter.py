"""
app/services/safety_filter.py

Multi-layer content safety pipeline for Nexxi.

Design Decisions:
- Layered approach: fast regex checks first (O(1) cost), then
  ML-based moderation only if text passes initial heuristics.
- PII redaction happens BEFORE logging — sanitised text is what
  gets persisted, not original input.  This is GDPR-aligned.
- Prompt injection detection uses a combination of pattern matching
  and statistical markers (unusual formatting, role-switching keywords).
- The HF moderation model call is optional and can be disabled via
  config for development or cost reasons.
- SafetyResult is a dataclass (not Pydantic) as it's an internal
  object never serialised to JSON directly.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

from app.utils.exceptions import SafetyFilterError
from app.utils.logger import get_logger
from app.utils.metrics import safety_violations_total

logger = get_logger(__name__)

# ── PII patterns (compiled once at module load for performance) ──

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)
_PHONE_RE = re.compile(
    r"(?<!\d)(\+?1?\s?)?(\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4})(?!\d)"
)
_SSN_RE = re.compile(
    r"\b(?!000|666|9\d{2})\d{3}[- ]?(?!00)\d{2}[- ]?(?!0000)\d{4}\b"
)
_CREDIT_CARD_RE = re.compile(
    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|"
    r"6(?:011|5[0-9]{2})[0-9]{12})\b"
)
_IP_ADDRESS_RE = re.compile(
    r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
)

# ── Prompt injection / jailbreak markers ─────────────────────

_INJECTION_PATTERNS = [
    # Role-switching attempts
    re.compile(r"\b(ignore|forget|disregard)\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)\b", re.I),
    re.compile(r"\bact\s+as\s+(if\s+)?(you\s+are|a|an)\b.{0,50}(without|no)\s+(restrictions?|limits?|guidelines?)\b", re.I),
    re.compile(r"\byou\s+are\s+now\s+(dan|jailbreak|evil|unrestricted|free)", re.I),
    re.compile(r"\b(system|assistant|user)\s*:\s*", re.I),   # Fake role injection
    # Token manipulation
    re.compile(r"<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>", re.I),
    # Common jailbreak phrases
    re.compile(r"\b(jailbreak|jail\s*break|bypass\s+(filter|safety|restriction))\b", re.I),
    re.compile(r"\bdo\s+anything\s+now\b", re.I),  # DAN prompt
    re.compile(r"\bpretend\s+(you\s+)?(have\s+no|don.t\s+have)\s+(rules?|restrictions?|guidelines?)\b", re.I),
    # Instruction override attempts
    re.compile(r"###\s*(new\s+)?instructions?\s*:", re.I),
    re.compile(r"\binitial\s+prompt\b", re.I),
]

# ── Blocked topic keywords (extended list) ────────────────────

_DEFAULT_BLOCKED_TOPICS: list[str] = [
    "violence",
    "illegal activities",
    "self harm",
    "hate speech",
    "explicit content",
    "terrorism",
    "child exploitation",
]


@dataclass
class SafetyResult:
    """
    Result from the safety filter pipeline.

    Attributes:
        is_safe: True if input passes ALL safety checks.
        reason: Human-readable explanation if is_safe is False.
        cleaned_input: Sanitised text with PII redacted (use this downstream).
        pii_detected: List of PII types found (without the actual values).
        threat_level: 'low' | 'medium' | 'high' — for logging/alerting.
    """

    is_safe: bool
    reason: str = ""
    cleaned_input: str = ""
    pii_detected: list[str] = field(default_factory=list)
    threat_level: str = "low"


class SafetyFilter:
    """
    Multi-layer content moderation and input sanitisation.

    Layers (applied in order of cost, cheapest first):
      1. HTML / script stripping
      2. Length enforcement
      3. PII detection and redaction
      4. Prompt injection / jailbreak detection
      5. Blocked topic matching
      6. (Optional) ML-based moderation model
    """

    def __init__(
        self,
        max_input_length: int = 1000,
        blocked_topics: list[str] | None = None,
        enable_ml_moderation: bool = False,
    ) -> None:
        self._max_length = max_input_length
        self._blocked = [t.lower() for t in (blocked_topics or _DEFAULT_BLOCKED_TOPICS)]
        self._enable_ml = enable_ml_moderation
        self._moderation_model: object | None = None

        if enable_ml_moderation:
            self._load_moderation_model()

    def _load_moderation_model(self) -> None:
        """
        Lazily load the HF text classification moderation model.
        Uses 'facebook/roberta-hate-speech-dynabench-r4-target' by default.
        Falls back gracefully if unavailable.
        """
        try:
            from transformers import pipeline as hf_pipeline  # type: ignore[import]

            self._moderation_model = hf_pipeline(
                "text-classification",
                model="martin-ha/toxic-comment-model",
                device=-1,  # CPU — moderation doesn't need GPU
            )
            logger.info("ML moderation model loaded")
        except Exception as exc:
            logger.warning(f"ML moderation model failed to load: {exc}. Continuing without it.")
            self._moderation_model = None

    # ── Public API ─────────────────────────────────────────────

    def check(self, user_input: str) -> SafetyResult:
        """
        Run the full safety pipeline on raw user input.

        Args:
            user_input: Raw text from the API request body.

        Returns:
            SafetyResult with is_safe, cleaned_input, and metadata.

        Note:
            This method does NOT raise — callers should inspect is_safe
            and raise SafetyFilterError themselves if needed.
        """
        # ── Layer 1: HTML / Script sanitisation ───────────────
        cleaned = self._strip_html(user_input)

        # ── Layer 2: Length check ─────────────────────────────
        if len(cleaned) > self._max_length:
            safety_violations_total.labels(reason="input_too_long").inc()
            return SafetyResult(
                is_safe=False,
                reason=f"Input exceeds maximum length of {self._max_length} characters.",
                cleaned_input=cleaned[: self._max_length],
                threat_level="low",
            )

        if not cleaned.strip():
            return SafetyResult(
                is_safe=False,
                reason="Input cannot be empty.",
                cleaned_input="",
                threat_level="low",
            )

        # ── Layer 3: PII detection and redaction ──────────────
        cleaned, pii_types = self._redact_pii(cleaned)

        # ── Layer 4: Prompt injection / jailbreak detection ───
        injection_match = self._detect_injection(cleaned)
        if injection_match:
            safety_violations_total.labels(reason="prompt_injection").inc()
            logger.warning(f"Prompt injection attempt detected: {injection_match[:60]}...")
            return SafetyResult(
                is_safe=False,
                reason="Potential prompt injection or jailbreak attempt detected.",
                cleaned_input=cleaned,
                pii_detected=pii_types,
                threat_level="high",
            )

        # ── Layer 5: Blocked topic check ──────────────────────
        topic_match = self._check_blocked_topics(cleaned)
        if topic_match:
            safety_violations_total.labels(reason=f"blocked_topic:{topic_match}").inc()
            logger.info(f"Blocked topic detected: '{topic_match}'")
            return SafetyResult(
                is_safe=False,
                reason=f"Topic not supported: '{topic_match}'.",
                cleaned_input=cleaned,
                pii_detected=pii_types,
                threat_level="medium",
            )

        # ── Layer 6: ML moderation (optional) ────────────────
        if self._enable_ml and self._moderation_model:
            ml_result = self._run_ml_moderation(cleaned)
            if ml_result:
                safety_violations_total.labels(reason="ml_moderation").inc()
                return SafetyResult(
                    is_safe=False,
                    reason="Content flagged by moderation model.",
                    cleaned_input=cleaned,
                    pii_detected=pii_types,
                    threat_level="high",
                )

        return SafetyResult(
            is_safe=True,
            reason="",
            cleaned_input=cleaned,
            pii_detected=pii_types,
            threat_level="low",
        )

    def check_or_raise(self, user_input: str) -> str:
        """
        Run safety checks and raise SafetyFilterError if input is unsafe.

        Args:
            user_input: Raw user text.

        Returns:
            Sanitised input text (PII redacted).

        Raises:
            SafetyFilterError: If any safety check fails.
        """
        result = self.check(user_input)
        if not result.is_safe:
            raise SafetyFilterError(result.reason)
        return result.cleaned_input

    # ── Private pipeline methods ───────────────────────────────

    @staticmethod
    def _strip_html(text: str) -> str:
        """
        Remove HTML tags and decode HTML entities.
        Prevents HTML injection and <script> execution in downstream use.
        """
        # Unescape HTML entities (e.g. &lt; → <)
        text = html.unescape(text)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Remove null bytes and control characters (except \n \t)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        return text.strip()

    @staticmethod
    def _redact_pii(text: str) -> tuple[str, list[str]]:
        """
        Detect and redact PII from text.

        Returns:
            Tuple of (redacted_text, list_of_pii_types_found).
        """
        pii_found: list[str] = []

        if _EMAIL_RE.search(text):
            text = _EMAIL_RE.sub("[EMAIL REDACTED]", text)
            pii_found.append("email")

        if _PHONE_RE.search(text):
            text = _PHONE_RE.sub("[PHONE REDACTED]", text)
            pii_found.append("phone")

        if _SSN_RE.search(text):
            text = _SSN_RE.sub("[SSN REDACTED]", text)
            pii_found.append("ssn")

        if _CREDIT_CARD_RE.search(text):
            text = _CREDIT_CARD_RE.sub("[CREDIT CARD REDACTED]", text)
            pii_found.append("credit_card")

        if _IP_ADDRESS_RE.search(text):
            text = _IP_ADDRESS_RE.sub("[IP REDACTED]", text)
            pii_found.append("ip_address")

        if pii_found:
            logger.info(f"PII detected and redacted: {pii_found}")

        return text, pii_found

    @staticmethod
    def _detect_injection(text: str) -> str | None:
        """
        Scan for prompt injection / jailbreak patterns.

        Returns:
            The matched string if found, else None.
        """
        for pattern in _INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return None

    def _check_blocked_topics(self, text: str) -> str | None:
        """
        Check if the input mentions any explicitly blocked topics.

        Returns:
            The matched topic string if found, else None.
        """
        lowered = text.lower()
        for topic in self._blocked:
            # Use word boundary to avoid false positives (e.g. 'violent' != 'violence')
            pattern = re.compile(rf"\b{re.escape(topic)}\b")
            if pattern.search(lowered):
                return topic
        return None

    def _run_ml_moderation(self, text: str) -> bool:
        """
        Run the HF toxicity classification model.

        Returns:
            True if the text is classified as toxic/harmful.
        """
        try:
            results = self._moderation_model(  # type: ignore[operator]
                text[:512],  # Limit input length to model's context window
                truncation=True,
            )
            # Model returns list of dicts: [{"label": "toxic", "score": 0.95}]
            for result in results:
                if (
                    result.get("label", "").lower() in ("toxic", "hate", "harmful")
                    and result.get("score", 0) > 0.8  # High-confidence threshold
                ):
                    return True
        except Exception as exc:
            logger.warning(f"ML moderation model error (non-fatal): {exc}")
        return False
