# Evasion Shield

`evasion_shield` 是 TP-02 的 deterministic 抗绕过归一化层。它把可能被混淆的文本转成可供后续检测使用的 `normalized_text`，同时输出 `evasion_tags`。

本包只做归一化和标签标注，不判断是否攻击、不阻断、不调用 LLM。
