# domains — 有界上下文（领域层）

与 [架构 §3.1](../../docs/architecture/sections/03-领域与交付分层.md#31-有界上下文) 对齐。

| 目录 | 上下文 | 模块 | W1 |
|------|--------|------|-----|
| `auth/` | 登录、JWT 签发 | A | ✅ |
| `compliance/` | 授权、敏感词、训练/合成门禁 | B, G | ✅ Gateway |
| `synthesis/` | 单条合成 Job 提交 | F | ✅ |
| `training/` | 训练 Job 提交、素材解析 | D | ✅ |
| `jobs/` | Job 查询响应映射 | 022 | ✅ |
| `voice_asset/` | 素材、质检 | C | 占位（DB 种子） |
| `production/` | 项目、角色、CSV | E | W2 |
| `export/` | 合规导出、ZIP | F | W3 |

**纪律**：不 import `workers/*`。
