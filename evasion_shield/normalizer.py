from __future__ import annotations

import base64
import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Literal
from urllib.parse import unquote


EvasionTag = Literal[
    "mixed_language",
    "unicode_confusable",
    "zero_width",
    "token_splitting",
    "delimiter_comment",
    "character_format",
    "context_dilution",
    "semantic_disguise",
    "encoded_payload",
]

EVASION_TAGS: tuple[EvasionTag, ...] = (
    "mixed_language",
    "unicode_confusable",
    "zero_width",
    "token_splitting",
    "delimiter_comment",
    "character_format",
    "context_dilution",
    "semantic_disguise",
    "encoded_payload",
)

ZERO_WIDTH_RE = re.compile("[\u200b\u200c\u200d\ufeff\u2060]")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
URL_ENCODED_RE = re.compile(r"(?:%[0-9a-fA-F]{2}){2,}")
BASE64_RE = re.compile(r"\b[A-Za-z0-9+/]{12,}={0,2}\b")
RISK_KEYWORDS = (
    "ignore",
    "previous",
    "instruction",
    "system prompt",
    "jailbreak",
    "admin",
    "安全",
    "忽略",
    "指令",
    "系统提示",
    "管理员",
)

CONFUSABLES = str.maketrans(
    {
        "а": "a",
        "е": "e",
        "о": "o",
        "р": "p",
        "с": "c",
        "у": "y",
        "х": "x",
        "А": "A",
        "Е": "E",
        "О": "O",
        "Р": "P",
        "С": "C",
        "Х": "X",
        "𝕤": "s",
        "𝕪": "y",
        "𝕤": "s",
        "𝕥": "t",
        "𝕖": "e",
        "𝕞": "m",
        "𝕡": "p",
        "𝕣": "r",
        "𝕠": "o",
        "略": "略",
        "冇": "有",
    }
)

LEET_TABLE = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a"})

PHRASE_REPLACEMENTS = (
    (re.compile(r"\bignoreallpreviousinstructions?\b", re.I), "ignore all previous instructions"),
    (re.compile(r"\bignorepreviousinstructions?\b", re.I), "ignore previous instructions"),
    (re.compile(r"\bignoreallsafetyrules\b", re.I), "ignore all safety rules"),
    (re.compile(r"\bignore\s+all\s+previous\s+instructions?\b", re.I), "ignore all previous instructions"),
    (re.compile(r"\bignore\s+previous\s+instructions?\b", re.I), "ignore previous instructions"),
    (re.compile(r"\bsystem\s+prompt\b", re.I), "system prompt"),
    (re.compile(r"\bfree\s+mode\b", re.I), "free mode"),
    (re.compile(r"無視|むし"), "ignore"),
    (re.compile(r" предыдущ[а-яё]* инструкц[а-яё]*", re.I), " previous instructions"),
    (re.compile(r"忽\s*略\s*之\s*前\s*的?\s*所?\s*有?\s*指\s*令"), "忽略之前的指令"),
    (re.compile(r"系\s*统\s*提\s*示\s*词|系\s*統\s*提\s*示\s*詞"), "系统提示词"),
)

SEMANTIC_DISGUISE_PATTERNS = (
    re.compile(r"测试.*安全.*输出", re.I),
    re.compile(r"security\s+test.*output", re.I),
    re.compile(r"作为回复的开头.*系统提示词"),
    re.compile(r"定义：当我说.*管理员模式"),
)


@dataclass(frozen=True)
class NormalizationResult:
    original_text: str
    normalized_text: str
    evasion_tags: list[EvasionTag]
    transforms: list[str]
    extracted_instructions: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedField:
    source: str
    field_path: str
    result: NormalizationResult

    def to_dict(self) -> dict:
        return {"source": self.source, "field_path": self.field_path, "result": self.result.to_dict()}


def normalize_text(text: str) -> NormalizationResult:
    original = text
    current = text
    tags: set[EvasionTag] = set()
    transforms: list[str] = []
    extracted: list[str] = []

    zero_width_stripped = ZERO_WIDTH_RE.sub("", current)
    if zero_width_stripped != current:
        tags.add("zero_width")
        transforms.append("strip_zero_width")
        current = zero_width_stripped

    uncommented = _strip_comments(current)
    if uncommented != current:
        tags.add("delimiter_comment")
        transforms.append("strip_comments")
        current = uncommented

    decoded_fragments = _decode_fragments(current)
    if decoded_fragments:
        tags.add("encoded_payload")
        transforms.append("decode_encoded_fragments")
        current = f"{current} " + " ".join(decoded_fragments)
        extracted.extend(decoded_fragments)

    nfkc = unicodedata.normalize("NFKC", current)
    confusable_normalized = nfkc.translate(CONFUSABLES)
    if confusable_normalized != current:
        tags.add("unicode_confusable")
        transforms.append("unicode_nfkc_confusable")
        current = confusable_normalized

    decommented = _split_shell_delimiters(current)
    if decommented != current:
        tags.add("delimiter_comment")
        transforms.append("split_shell_delimiters")
        current = decommented

    retokenized = _rejoin_split_tokens(current)
    if retokenized != current:
        tags.add("token_splitting")
        transforms.append("rejoin_split_tokens")
        current = retokenized

    leet_normalized = _normalize_leet(current)
    if leet_normalized != current:
        tags.add("character_format")
        transforms.append("normalize_leet")
        current = leet_normalized

    lowered = current.lower()
    if _has_mixed_case_signal(current):
        tags.add("character_format")
        transforms.append("lowercase_mixed_case")
    current = lowered

    current, mixed_language = _normalize_mixed_language(current)
    if mixed_language:
        tags.add("mixed_language")
        transforms.append("normalize_mixed_language")

    current, phrase_hits = _normalize_phrases(current)
    extracted.extend(phrase_hits)

    if _looks_diluted(current):
        tags.add("context_dilution")
        transforms.append("extract_risk_windows")
        extracted.extend(_extract_risk_windows(current))

    if any(pattern.search(current) for pattern in SEMANTIC_DISGUISE_PATTERNS):
        tags.add("semantic_disguise")
        transforms.append("tag_semantic_disguise")

    normalized = _normalize_spaces(current)
    extracted = _dedupe([_normalize_spaces(item.lower()) for item in extracted if item.strip()])

    return NormalizationResult(
        original_text=original,
        normalized_text=normalized,
        evasion_tags=[tag for tag in EVASION_TAGS if tag in tags],
        transforms=transforms,
        extracted_instructions=extracted,
    )


def _strip_comments(text: str) -> str:
    return BLOCK_COMMENT_RE.sub(" ", HTML_COMMENT_RE.sub(" ", text))


def _split_shell_delimiters(text: str) -> str:
    replaced = re.sub(r"[;&|]{1,2}", " ", text)
    return re.sub(r"(?m)(?<=\s)#.*$", " ", replaced)


def _decode_fragments(text: str) -> list[str]:
    decoded: list[str] = []
    for match in URL_ENCODED_RE.finditer(text):
        candidate = unquote(match.group(0))
        if _is_useful_decoded_text(candidate):
            decoded.append(candidate)

    for match in BASE64_RE.finditer(text):
        token = match.group(0)
        try:
            padded = token + ("=" * (-len(token) % 4))
            raw = base64.b64decode(padded, validate=False)
            candidate = raw.decode("utf-8")
        except Exception:
            continue
        if _is_useful_decoded_text(candidate):
            decoded.append(candidate)
    return _dedupe(decoded)


def _is_useful_decoded_text(text: str) -> bool:
    if not text or any(ord(ch) < 9 for ch in text):
        return False
    lowered = text.lower()
    return any(keyword in lowered for keyword in ("ignore", "safety", "rules", "指令", "系统", "忽略"))


def _rejoin_split_tokens(text: str) -> str:
    current = re.sub(r"(?<=[\u4e00-\u9fff])[\s\-_]+(?=[\u4e00-\u9fff])", "", text)

    def collapse(match: re.Match[str]) -> str:
        return match.group(0).replace(" ", "").replace("-", "").replace("_", "")

    for _ in range(3):
        current = re.sub(r"\b(?:[a-zA-Z][\s\-_]+){2,}[a-zA-Z]\b", collapse, current)
    return current


def _normalize_leet(text: str) -> str:
    words = []
    changed = False
    for word in re.split(r"(\W+)", text):
        translated = word.translate(LEET_TABLE) if re.search(r"[013457@]", word) else word
        if translated != word and re.search(r"[A-Za-z]", translated):
            changed = True
        words.append(translated)
    candidate = "".join(words)
    return candidate if changed and _has_risk_signal(candidate) else text


def _has_mixed_case_signal(text: str) -> bool:
    words = re.findall(r"[A-Za-z]{5,}", text)
    return any(_is_suspicious_mixed_case(word) for word in words)


def _is_suspicious_mixed_case(word: str) -> bool:
    if not (any(ch.islower() for ch in word) and any(ch.isupper() for ch in word)):
        return False
    return not word.istitle()


def _normalize_mixed_language(text: str) -> tuple[str, bool]:
    changed = False
    current = text
    replacements = {
        "指令": " instructions ",
        "系统提示词": " system prompt ",
        "管理员": " admin ",
        "安全规则": " safety rules ",
        "無視": " ignore ",
        "инструкции": " instructions ",
        "предыдущие": " previous ",
    }
    contains_ascii = bool(re.search(r"[a-zA-Z]", text))
    contains_non_ascii = bool(re.search(r"[^\x00-\x7F]", text))
    if contains_ascii and contains_non_ascii:
        for old, new in replacements.items():
            if old.lower() in current:
                current = current.replace(old.lower(), new)
                changed = True
    return current, changed or (contains_ascii and contains_non_ascii and _has_risk_signal(text))


def _normalize_phrases(text: str) -> tuple[str, list[str]]:
    current = text
    hits: list[str] = []
    for pattern, replacement in PHRASE_REPLACEMENTS:
        if pattern.search(current):
            current = pattern.sub(replacement, current)
            hits.append(replacement)
    return current, hits


def _looks_diluted(text: str) -> bool:
    return len(text) > 500 and _has_risk_signal(text)


def _has_risk_signal(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in RISK_KEYWORDS)


def _extract_risk_windows(text: str, radius: int = 80) -> list[str]:
    lowered = text.lower()
    windows: list[str] = []
    for keyword in RISK_KEYWORDS:
        index = lowered.find(keyword.lower())
        if index == -1:
            continue
        start = max(0, index - radius)
        end = min(len(text), index + len(keyword) + radius)
        windows.append(text[start:end])
    return _dedupe(windows)


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
