"""Personal-data masking (Lab 72): placeholders for the model, real values for people."""

from sovereign_brain.security.pii import get_masker, unmask

IBAN = "GB82 WEST 1234 5698 7654 32"


def test_an_iban_becomes_a_placeholder_and_comes_back() -> None:
    vault: dict[str, str] = {}
    text = f"Compare the energy exposure with the account behind IBAN {IBAN}."

    masked = get_masker().mask(text, vault)

    assert masked == "Compare the energy exposure with the account behind IBAN <IBAN_CODE_1>."
    assert vault == {"<IBAN_CODE_1>": IBAN}
    assert unmask(masked, vault) == text


def test_the_banks_account_numbers_are_masked() -> None:
    vault: dict[str, str] = {}

    masked = get_masker().mask("Move it from CLB-12345678 to CLB-87654321.", vault)

    assert masked == "Move it from <ACCOUNT_NUMBER_1> to <ACCOUNT_NUMBER_2>."


def test_the_same_value_keeps_its_placeholder() -> None:
    vault: dict[str, str] = {}
    masker = get_masker()

    first = masker.mask("Fees on CLB-12345678?", vault)
    second = masker.mask("And the balance of CLB-12345678?", vault)

    assert first == "Fees on <ACCOUNT_NUMBER_1>?"
    assert second == "And the balance of <ACCOUNT_NUMBER_1>?"
    assert len(vault) == 1


def test_client_ids_and_figures_stay_visible() -> None:
    text = "How exposed is C-1042 to a 40% fall in energy stocks?"

    assert get_masker().mask(text, {}) == text  # the tools need the client ID and the numbers
