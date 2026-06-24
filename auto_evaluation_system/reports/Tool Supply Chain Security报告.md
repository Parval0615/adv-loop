# Tool Supply Chain Security 报告

> 日期: 2026-05-08
> Phase: B.1 — Ed25519 工具完整性签名验证
> 验证: 6/6 测试通过 (签名/验签/篡改/伪造/缺失/审计集成)

---

## 1. 问题定义

### 1.1 AI 工具供应链威胁

在 Agent 系统中，工具是 Python 文件——可以被任何人修改：

```
攻击者修改 tool.py → 插入后门 → Agent启动时加载 → 工具运行时执行恶意代码
```

传统应用有代码签名（Windows Authenticode / macOS Gatekeeper / Linux package signing）。AI Agent 的工具没有等价保护机制。

### 1.2 威胁模型

| 攻击路径 | 示例 | 检测方式 |
|------|------|:---:|
| 工具文件被直接修改 | 在 `db_query.py` 末尾加后门 | SHA256 hash 不匹配 |
| manifest 被篡改 | 修改 `sha256` 字段使之匹配篡改后的文件 | Ed25519 签名无效 |
| 签名文件被替换 | 攻击者用自己的密钥重新签名 | 公钥不匹配（验签失败） |
| manifest 被删除 | 删除 `.manifest.json` 逃避检查 | 文件缺失检测 |
| 攻击者替换密钥对 | 同时替换公私钥和所有签名 | 外部锚定公钥（如硬编码或只读存储） |

**无法检测**：攻击者同时替换工具文件 + manifest + 签名 + 公钥（全链替换）。与审计日志哈希链的全链替换问题相同——需要外部锚定。

---

## 2. 架构设计

### 2.1 工作流

```
签名阶段 (开发者):
  工具源码 path
    → SHA256 hash
    → manifest.json {tool_name, version, sha256, signer, permission_scope}
    → Ed25519.sign(manifest) → signature.sig
    → 三个文件一起发布: tool.py + manifest.json + signature.sig

验证阶段 (Agent启动时):
  1. manifest.json 存在? → 否 → 拒绝加载
  2. signature.sig 存在? → 否 → 拒绝加载
  3. SHA256(tool.py) == manifest.sha256? → 否 → 拒绝加载 (篡改)
  4. Ed25519.verify(manifest, signature, public_key)? → 否 → 拒绝加载 (伪造)
  5. 全部通过 → 加载工具
```

### 2.2 Manifest 格式

```json
{
  "tool_name": "db_query",
  "version": "1.0.0",
  "sha256": "d4b44e4cdf54f09d...",
  "signer": "security-team",
  "permission_scope": ["db_query.execute"],
  "signed_at": "2026-05-08T14:30:00",
  "tool_path": "db_query.py"
}
```

### 2.3 Ed25519 选型理由

| 算法 | 密钥长度 | 签名长度 | 速度 | 安全性 |
|------|:---:|:---:|------|:---:|
| RSA-2048 | 256B | 256B | 慢 | 128-bit |
| ECDSA P-256 | 32B | 64B | 中 | 128-bit |
| **Ed25519** | **32B** | **64B** | **快** | **128-bit** |
| HMAC-SHA256 | 32B | 32B | 最快 | 需共享密钥 |

选择 Ed25519 的原因：小密钥、快签名、无随机数依赖（确定性签名）、广泛采用（SSH/GPG/TLS 1.3）。

---

## 3. 验证结果

### 3.1 完整测试矩阵

| # | 测试场景 | 预期 | 实际 | 检测机制 |
|---|------|:---:|:---:|------|
| 1 | 合法工具 + 正确签名 | PASS | PASS | 4 检查全通过 |
| 2 | 工具代码被篡改 (加后门) | FAIL | FAIL | hash_mismatch |
| 3 | 签名被替换为伪造签名 | FAIL | FAIL | signature_invalid |
| 4 | manifest.json 被删除 | FAIL | FAIL | manifest_missing |
| 5 | signature.sig 被删除 | FAIL | FAIL | signature_missing |
| 6 | verify_and_load 审计集成 | FAIL→审计 | FAIL→审计 | audit.log写入 |

### 3.2 篡改检测示例

```
原始 db_query.py:  sha256=d4b44e4cdf54f09d...
修改后 (+后门):    sha256=0862615bc55c19a6...

verify_tool_integrity:
  checks.hash_match = False
  failures = ['hash_mismatch: expected=d4b44e4c..., actual=0862615bc...']
  valid = False
```

---

## 4. 失败案例分析

### 4.1 失败案例1：公钥存储不安全

**场景**：公钥文件 `tool_signing_key.pub` 和工具文件在同一目录。攻击者获得目录写权限后，替换公钥 + 重新签名所有工具。

**根因**：Ed25519 验签依赖公钥的真实性。如果公钥本身可以被替换，签名链整体失效。这与审计日志哈希链的"全链替换"问题同源。

**缓解**：
- 公钥硬编码在 Agent 启动代码中（编译时嵌入）
- 公钥存储在只读文件系统（攻击者无写权限）
- 使用硬件安全模块 (HSM) 存储私钥，公钥通过证书链分发

### 4.2 失败案例2：manifest 的 permission_scope 不强制

**场景**：manifest 中声明 `permission_scope: ["db_query.read"]`，但工具实际实现了 `DROP` 操作。签名验证通过（因为 manifest 是开发者签的），运行时策略引擎拦截了 DROP——但这不是签名验证的功劳。

**根因**：签名验证保证 **manifest 未被篡改**，不保证 **manifest 内容准确反映了工具的实际能力**。如果开发者说谎（或在 manifest 中低估了工具权限），签名不会发现。

**分类**：这是信任根问题——签名验证对开发者是信任的（signer 字段），但如果 signer 本身恶意，签名只是证明了"这个人签的"，而不是"这个工具是安全的"。

### 4.3 失败案例3：依赖库的传递性供应链攻击

**场景**：`db_query.py` 本身未被篡改，但它 import 的第三方库（如 `sqlparse`）被投毒。签名验证只检查 `db_query.py` 的 hash，不检查依赖。

**根因**：签名验证是文件级别的——每个文件独立签名。依赖传递性不在覆盖范围内。

**缓解**：对整个虚拟环境做 hash snapshot（`pip freeze --hash`），或使用 SBOM (Software Bill of Materials) + 依赖签名。

---

## 5. 面试速查卡

### 30秒回答："AI 工具供应链安全怎么做？"

"我实现了 Ed25519 签名验证的 Tool Integrity 系统。每个工具有三个文件：源码 `.py`、manifest `.json`（含 sha256）、Ed25519 签名 `.sig`。Agent 启动时做三级校验：hash 匹配（防篡改）→ Ed25519 验签（防伪造）→ manifest 存在性（防删除）。任意一步失败→拒绝加载→写 critical 审计日志。6/6 测试通过。"

### 追问第一层："Ed25519 为什么选它？"

"32字节小公钥、64字节小签名、确定性签名无随机数风险、曲线安全强度 128-bit。对比 RSA（256B密钥/慢）和 ECDSA（随机数漏洞历史），Ed25519 是现代密码学的最佳实践——SSH/GPG/TLS 1.3 都在迁移到它。"

### 追问第二层："公钥被替换了怎么办？"

"这是全链替换问题——攻击者同时替换工具+manifest+签名+公钥，本地签名验证无法检测。解决方法是外部锚定：公钥硬编码在 agent 启动代码中，或者从只读证书链获取。和审计日志哈希链需要外部 last_hash 锚定是同一个原理。"

### 追问第三层："签名验证能防什么、防不住什么？"

"能防：工具文件篡改 / manifest 伪造 / 签名伪造 / manifest 删除。防不住：公钥被替换（需要外部锚定）、开发者恶意签名（信任根问题）、依赖库传递攻击（需要 SBOM）、运行时内存篡改（需要 TEE/HSM 级别的保护）。"

---

## 6. API 参考

```python
from security.tool_integrity import *

# 生成密钥对
priv_key, pub_bytes = generate_keypair(save_dir="./keys")

# 签名工具
manifest = sign_tool("tools/db_query.py", priv_key,
                     signer="security-team", version="1.0.0",
                     permission_scope=["db_query.read"])

# 验证工具
result = verify_tool_integrity("tools/db_query.py", pub_bytes)
# {valid: True/False, checks: {hash_match, signature_valid, manifest_valid}, failures: [...]}

# 加载时校验（含审计日志）
allowed, reason = verify_and_load("tools/db_query.py", pub_bytes)
# (True, "Tool 'db_query' integrity verified.") OR (False, "TOOL_INTEGRITY_FAILED: ...")

# 批量校验
results = batch_verify_tools(["tools/db_query.py", "tools/api_call.py"], pub_bytes)
```

---

> **报告完成。** Tool Supply Chain Security 是 AI 安全面试中容易被忽略的差异化话题——大多数候选人讲 Prompt 注入，少有人讲工具签名。Ed25519 + manifest 的设计展示了密码学工程能力，与 Phase 4.3 的审计日志哈希链形成呼应。
