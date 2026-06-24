from pathlib import Path

from auto_attack_system.indirect_injection import HTML_POISON_SCENARIOS, generate_html_poison
from auto_attack_system.payloads import ALL_PAYLOADS, CATEGORIES


def test_payload_database_has_expected_categories() -> None:
    assert ALL_PAYLOADS
    assert {"direct_injection", "jailbreak", "prompt_leakage", "obfuscation"} <= set(CATEGORIES)


def test_indirect_injection_generator_writes_html(tmp_path: Path) -> None:
    output = tmp_path / "poison.html"
    html, metadata = generate_html_poison(HTML_POISON_SCENARIOS[0], str(output))

    assert output.exists()
    assert metadata["format"] == "html"
    assert metadata["scenario_id"]
    assert "<html" in html.lower()
    assert output.read_text(encoding="utf-8") == html
