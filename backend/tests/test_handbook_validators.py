"""Tests for pre-insertion handbook term validators."""
from services.handbook_validators import validate_term_scope


# --- Happy path: clearly-technical terms accept ---

def test_scope_allows_canonical_technical_term():
    ok, reason = validate_term_scope("Transformer", term_type="model_algorithm_family")
    assert ok is True
    assert reason == ""


def test_scope_allows_training_technique():
    ok, _ = validate_term_scope("Knowledge Distillation", term_type="training_optimization_method")
    assert ok is True


# --- Rejection: literal HR/regulatory blocklist ---

def test_scope_rejects_hr_literal():
    ok, reason = validate_term_scope("acquihire", term_type="foundational_concept")
    assert ok is False
    assert "blocklist" in reason.lower()


def test_scope_rejects_iso_literal():
    ok, reason = validate_term_scope("ISO 42001", term_type="foundational_concept")
    assert ok is False
    # Could match via literal blocklist OR regex; either fine


# --- Rejection: standard-family regex ---

def test_scope_rejects_arbitrary_iec_standard():
    ok, reason = validate_term_scope("IEC 62443", term_type="foundational_concept")
    assert ok is False
    assert "pattern" in reason.lower() or "regex" in reason.lower() or "out_of_scope" in reason.lower()


def test_scope_rejects_ieee_standard():
    ok, _ = validate_term_scope("IEEE 802.11", term_type="foundational_concept")
    assert ok is False


def test_scope_rejects_nist_sp():
    ok, _ = validate_term_scope("NIST SP 800-53", term_type="foundational_concept")
    assert ok is False


# --- Rejection: product_platform_service without allowlist ---

def test_scope_rejects_unlisted_product():
    """A product-type term not in MAJOR_AI_PRODUCT_ALLOWLIST should be rejected."""
    ok, reason = validate_term_scope("Firefly AI Assistant", term_type="product_platform_service")
    assert ok is False
    assert "product" in reason.lower()


def test_scope_rejects_another_random_product():
    ok, _ = validate_term_scope("Random Chatbot App", term_type="product_platform_service")
    assert ok is False


# --- Acceptance: allowlisted product ---

def test_scope_accepts_allowlisted_product():
    """'Firefly' is in MAJOR_AI_PRODUCT_ALLOWLIST."""
    ok, _ = validate_term_scope("Firefly", term_type="product_platform_service")
    assert ok is True


# --- Acceptance: versioned model pattern ---

def test_scope_accepts_gpt_version():
    ok, _ = validate_term_scope("GPT-5.2", term_type="model_algorithm_family")
    assert ok is True


def test_scope_accepts_claude_version():
    ok, _ = validate_term_scope("Claude Sonnet 4.6", term_type="model_algorithm_family")
    assert ok is True


def test_scope_accepts_versioned_product_even_if_classified_as_product():
    """GPT-Rosalind got classified as product but matches MODEL_VERSION_PATTERN."""
    ok, _ = validate_term_scope("GPT-Rosalind", term_type="product_platform_service")
    assert ok is True


# --- Allowlist override: beats blocklist ---

def test_scope_allowlist_overrides_blocklist():
    """If Amy decides 'ISO 42001' is worth including, allowlist wins over blocklist."""
    ok, _ = validate_term_scope(
        "ISO 42001",
        term_type="foundational_concept",
        _allowlist_override=frozenset({"ISO 42001"}),
    )
    assert ok is True


# --- Edge cases ---

def test_scope_accepts_term_with_unknown_type():
    """If term_type is None/empty, don't reject purely for that reason —
    fall through to blocklist/regex checks only."""
    ok, _ = validate_term_scope("Transformer", term_type=None)
    assert ok is True


def test_scope_rejects_blocklist_even_with_unknown_type():
    ok, _ = validate_term_scope("acquihire", term_type=None)
    assert ok is False


def test_scope_empty_term_rejected():
    ok, reason = validate_term_scope("", term_type="foundational_concept")
    assert ok is False
    assert "empty" in reason.lower()
