# voice_platform — 横切平台能力

Python 包名 **`voice_platform`**（避免与标准库 `platform` 冲突）。架构文档中的「基础设施层」指本包。

## 模块目录

| 目录 | 说明 |
|------|------|
| `auth/` | JWT、Redis OTP、User 模型、Repository |
| `community/` | Feed/私信 ORM 模型、Repository |
| `developer/` | API Key 模型、Repository |
| `emotion/` | 中文文本情感分析（关键词词库） |
| `engine/` | 训练数据集、引擎路径适配 |
| `fingerprint/` | 音频指纹编码（频谱峰值哈希） |
| `job/` | Job 模型、Redis 队列、Repository、Pydantic 契约 |
| `kyc/` | 实名认证、身份证 OCR 适配 |
| `licensing/` | 授权证书 PDF 生成 |
| `observability/` | 日志、Trace、告警 |
| `payment/` | 支付订单模型、Webhook 验签 |
| `quality/` | 音质评估、说话人嵌入 |
| `quota/` | 用量记录、月配额预检/实扣 |
| `script/` | 剧本解析契约 |
| `settlement/` | 卖家钱包、流水、提现 |
| `social/` | 关注/点赞 ORM 模型 |
| `storage/` | 本地文件存储、公开 URL |
| `watermark/` | 数字水印嵌入/提取（LSB 隐写） |
| `config.py` | 环境配置、DB Session |
| `audio_util.py` | WAV 音调变换工具 |

## 架构纪律

- 本层仅承载 ORM 模型、仓储、引擎适配、底层工具，**不含业务流程**
- 业务流程位于 `domains/` 层
- API 路由通过 `domains/*/service` 调用用例，禁止直接依赖 `voice_platform/*/repository`
- Worker 消费 `voice_platform/job` 队列契约；配额在 Job `succeeded` 后实扣

历史占位目录 `platform/` 仅作说明，请以本包为准。
