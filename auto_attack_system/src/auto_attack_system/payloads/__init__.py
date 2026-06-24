"""Prompt注入攻击载荷数据库 — 100+ 分类标注Payload"""

from .injection import INJECTION_PAYLOADS
from .jailbreak import JAILBREAK_PAYLOADS
from .leakage import LEAKAGE_PAYLOADS
from .obfuscation import OBFUSCATION_PAYLOADS

ALL_PAYLOADS = INJECTION_PAYLOADS + JAILBREAK_PAYLOADS + LEAKAGE_PAYLOADS + OBFUSCATION_PAYLOADS

CATEGORIES = {
    "direct_injection": "直接注入",
    "jailbreak": "越狱攻击",
    "prompt_leakage": "提示泄露",
    "obfuscation": "混淆绕过",
}
