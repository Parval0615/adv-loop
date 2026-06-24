import re

# 敏感信息正则规则
SENSITIVE_PATTERNS = {
    "手机号": r"1[3-9]\d{9}",
    "身份证号": r"[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]",
    "银行卡号": r"\d{16,19}",
    "邮箱": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "API密钥/Token": r"(?:sk-|api_key|token|secret|key)[\w-]{16,}",
    "内网IP": r"(?:192\.168|10|172\.(?:1[6-9]|2[0-9]|3[01]))\.\d{1,3}\.\d{1,3}"
}

# 违规内容正则规则（优化版，避免误判，仅拦截高危可执行内容）
ILLEGAL_PATTERNS = [
    # 高危SQL执行语句（仅匹配完整可执行的注入语句，避免单符号误判）
    r"union\s+all\s+select", r"union\s+select",
    r"xp_cmdshell", r"exec\s+master\.", r"execute\s+sp_",
    r"drop\s+table", r"drop\s+database", r"truncate\s+table",
    r"alter\s+table", r"create\s+table",
    # 高危系统命令执行
    r"system\(", r"shell_exec\(", r"exec\(", r"passthru\(", r"popen\(",
    r"os\.system\(", r"subprocess\.", r"powershell\s+-", r"curl\s+.*\|\s*(sh|bash)",
    r"wget\s+.*\|\s*(sh|bash)", r"rm\s+-rf\s+/", r"chmod\s+777",
    # 黑产违规内容
    r"免杀", r"远控木马", r"钓鱼网站", r"脱壳破解", r"暴力破解"
]

# ---------------------- 核心函数 ----------------------
def detect_sensitive_info(text: str) -> tuple[bool, str]:
    """检测文本中的敏感信息"""
    result = []
    for name, pattern in SENSITIVE_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            unique = list(set(matches))
            masked = []
            for s in unique:
                s = str(s)
                if len(s) > 7:
                    masked.append(s[:3] + "****" + s[-4:])
                else:
                    masked.append("****")
            result.append(f"【{name}】{', '.join(masked)}")
    if not result:
        return False, "未检测到敏感信息"
    return True, "检测到敏感信息：\n" + "\n".join(result)

def mask_sensitive_info(text: str) -> str:
    """脱敏文本中的敏感信息"""
    for name, pattern in SENSITIVE_PATTERNS.items():
        text = re.sub(pattern, lambda m: (m.group()[:3] + "****" + m.group()[-4:]) if len(m.group())>7 else "****", text)
    return text

def check_output_compliance(text: str, is_rag_context: bool = False) -> tuple[bool, str]:
    """
    输出内容合规校验
    is_rag_context=True 时仅拦截完整可执行payload，允许安全文档中的描述性内容
    """
    text_lower = text.lower()

    if is_rag_context:
        # RAG/教育场景：仅拦截完整可执行payload和黑产关键词
        EDU_SAFE_PATTERNS = [
            r"xp_cmdshell", r"exec\s+master\.", r"execute\s+sp_",
            r"shell_exec\(", r"passthru\(", r"popen\(",
            r"os\.system\(", r"subprocess\.", r"curl\s+.*\|\s*(sh|bash)",
            r"免杀", r"远控木马", r"钓鱼网站", r"脱壳破解", r"暴力破解"
        ]
        patterns = EDU_SAFE_PATTERNS
    else:
        patterns = ILLEGAL_PATTERNS

    for pattern in patterns:
        if re.search(pattern, text_lower):
            return False, "[!] 输出内容不合规，包含高危操作代码/违规内容，已拦截"
    return True, "输出内容合规"
