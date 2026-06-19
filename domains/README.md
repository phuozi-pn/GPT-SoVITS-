# domains — 有界上下文（领域层）

与 [架构 §3.1](../../docs/architecture/sections/03-领域与交付分层.md#31-有界上下文) 对齐。

## 模块概览

| 模块 | 目录 | 上下文 | 责任 |
|------|------|--------|------|
| **platform** | | 平台横切 | |
| | `auth/` | 身份与会话 | 登录、JWT 签发 |
| | `jobs/` | 异步任务 | Job 查询、响应映射 |
| | `quota/` | 用量配额 | 月配额查询、预检 |
| | `watermark/` | 数字水印 | 水印检测 |
| | `fingerprint/` | 音频指纹 | 指纹注册、搜索 |
| | `emotion/` | 情感分析 | 中文文本情感识别 |
| **produce** | | 制作 | |
| | `synthesis/` | 语音合成 | 单条/批量合成 Job 提交 |
| | `script/` | 剧本解析 | 剧本分段与角色提取 |
| | `projects/` | 短剧项目 | 项目管理与 CSV |
| | `compliance/` | 合规 | 敏感词、Gateway、合规导出 |
| **voice** | | 音色 | |
| | `voices/` | 音色档案 | 音色与版本管理 |
| | `training/` | 训练 | 训练 Job 提交、素材解析 |
| | `assets/` | 素材 | 素材管理与质检 |
| | `consents/` | 授权书 | 授权书审核 |
| | `marketplace/` | 音色馆 | 上架、分类、搜索 |
| | `licensing/` | 授权凭证 | 授权购买、证书签发 |
| | `kyc/` | 实名认证 | 实名认证流程 |
| | `quality/` | 音质评测 | AB 评测 |
| | `payment/` | 支付 | 下单、Webhook、Mock 确认 |
| | `settlement/` | 结算 | 卖家钱包、流水、提现 |
| **social** | | 社区 | |
| | `social/` | 社交互动 | 关注、点赞 |
| | `community/` | 内容社区 | Feed 与私信 |
| **ops** | | 运营 | |
| | `developer/` | 开发者 | API Key 管理 |

## 架构纪律

1. `domains/<name>/service.py` 为用例入口；**禁止 routes 直接访问 `voice_platform/*/repository`**
2. 跨域编排经 `ComplianceGateway` 或显式应用服务，不绕过合规
3. `voice_platform/*` 仅承载 ORM、仓储、引擎适配，不含业务流程
4. 不 import `workers/*`
