"""Personal-data masking (Lab 72): the model sees placeholders, people see the real values.

Microsoft Presidio finds personal data in a text: names (with the spaCy language model),
e-mail addresses, phone numbers, IBANs, card numbers, and the bank's own account numbers.
Each value is swapped for a numbered placeholder like <PERSON_1>. The originals stay in a
small "vault" (a dictionary) for this one request, so the answer can be unmasked for the
analyst. The model, the checkpoints, the cache and the traces only ever hold placeholders.
"""

from functools import cache

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "IBAN_CODE",
    "CREDIT_CARD",
    "ACCOUNT_NUMBER",
]
SPACY_SMALL = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}
# Crescent Ledger Bank's own account numbers: CLB- and eight digits
ACCOUNT_NUMBERS = PatternRecognizer(
    supported_entity="ACCOUNT_NUMBER",
    patterns=[Pattern("crescent_ledger_account", r"\bCLB-\d{8}\b", 0.9)],
)


class PiiMasker:
    """Finds personal data with Presidio and swaps it for numbered placeholders."""

    def __init__(self, analyzer: AnalyzerEngine, score_threshold: float = 0.5) -> None:
        self.analyzer = analyzer
        self.score_threshold = score_threshold

    def find(self, text: str) -> list[RecognizerResult]:
        return self.analyzer.analyze(
            text=text, language="en", entities=ENTITIES, score_threshold=self.score_threshold
        )

    def mask(self, text: str, vault: dict[str, str]) -> str:
        """Replace personal data with placeholders; the vault remembers the original values."""
        found = sorted(self.find(text), key=lambda result: (result.start, -result.score))
        pieces, position = [], 0
        for result in found:
            if result.start < position:  # overlaps a value that is already replaced
                continue
            original = text[result.start : result.end]
            placeholder = next((key for key, value in vault.items() if value == original), None)
            if placeholder is None:  # a new value: the next number for its type
                number = sum(key.startswith(f"<{result.entity_type}_") for key in vault) + 1
                placeholder = f"<{result.entity_type}_{number}>"
                vault[placeholder] = original
            pieces += [text[position : result.start], placeholder]
            position = result.end
        masked = "".join(pieces) + text[position:]
        # A value found once is hidden everywhere, also where Presidio missed it
        # (for example "Amina Rahman" inside the company name "Amina Rahman Holdings")
        for placeholder, original in vault.items():
            masked = masked.replace(original, placeholder)
        return masked


def unmask(text: str, vault: dict[str, str]) -> str:
    """Put the original values back, for the person who is allowed to see them."""
    for placeholder, original in vault.items():
        text = text.replace(placeholder, original)
    return text


@cache
def get_masker() -> PiiMasker:
    """Built once per process: loading the spaCy model takes a moment."""
    nlp_engine = NlpEngineProvider(nlp_configuration=SPACY_SMALL).create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
    analyzer.registry.add_recognizer(ACCOUNT_NUMBERS)
    return PiiMasker(analyzer)
