# MVP+1 音色馆 + VoiceGrant（第一切片）

> 状态：**进行中** — 不含定价/支付/聊天

## 目标

让用户 **浏览精选音色** 并 **跨账号使用**，为后续交易市场打基础。

## 已实现（本切片）

| 能力 | API | 说明 |
|------|-----|------|
| 音色馆列表 | `GET /api/v1/catalog/voices` | 已发布、可合成；支持 `?tags=短剧,男声` |
| 标签索引 | `GET /api/v1/catalog/tags` | 已发布条目去重标签 |
| 发布到馆 | `POST /api/v1/catalog/voices` | 仅 owner；默认 `pending` 待审 |
| 我的发布 | `GET /api/v1/catalog/voices/mine` | owner 查看审核状态 |
| 待审列表 | `GET /api/v1/catalog/voices/pending` | 运营（`DEV_ADMIN_USER_ID`） |
| 审核通过 | `POST /api/v1/catalog/voices/{id}/approve` | 运营 |
| 审核驳回 | `POST /api/v1/catalog/voices/{id}/reject` | 运营 |
| 重生成样音 | `POST /api/v1/catalog/voices/{id}/generate-demo` | 运营；审核通过时也会自动触发 |
| 授权他人 | `POST /api/v1/voices/{id}/grants` | VoiceGrant |
| 我的授权 | `GET /api/v1/voice-grants` | 被授权方可见 |
| 撤销授权 | `DELETE /api/v1/voice-grants/{id}` | 授权方 |
| 我发出的授权 | `GET /api/v1/voice-grants/issued` | 授权方管理 |
| 合成权限 | 合成/批量门禁 | owner / 公开馆 / 有效 Grant |

Web：**/catalog** 音色馆页（发布 + VoiceGrant + 精选试听）

开发模式：Web 右上角切换 **用户 A / 用户 B**，API 走 `X-User-Id` 头。

## 数据模型

```
voice_catalog_entries
  voice_version_id, title, description, tags, featured, status

voice_grants
  voice_id, granter_user_id, grantee_user_id, expires_at, revoked_at
```

## 使用示例

### 发布 004 到音色馆

Web → **音色馆** → 选版本 → 发布

或 API：

```json
POST /api/v1/catalog/voices
{
  "voice_version_id": "...",
  "title": "蛊真人·龙宫",
  "description": "004 云端微调",
  "tags": ["短剧", "男声"],
  "featured": true
}
```

### 授权另一用户使用（非公开）

Web → **音色馆** → **音色授权** → 选音色 → 填被授权用户 ID → 授权合成

或 API：

```json
POST /api/v1/voices/{voice_id}/grants
{ "grantee_user_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" }
```

本地验证：

```powershell
python scripts/smoke_mvp1_grant.py
```

### Phase 0 运营只读（排障 / 值班）

| API | 说明 |
|-----|------|
| `GET /api/v1/admin/jobs` | 最近任务；`?status=failed&job_type=infer&limit=50` |
| `GET /api/v1/admin/stats` | `release`、队列中/运行中/24h 失败数 |

请求头：`X-User-Id: <DEV_ADMIN_USER_ID>`（与音色馆审核同一运营账号）。

```powershell
curl -H "X-User-Id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" http://127.0.0.1:8001/api/v1/admin/stats
```

Web：**/admin** 运营台（侧栏仅用户 C 可见）— 队列统计 + 失败任务排障。

### 创作者主页

| API | 说明 |
|-----|------|
| `GET /api/v1/catalog/creators/{owner_user_id}` | 创作者公开音色 + 脱敏展示名 |
| `GET /api/v1/catalog/voices?owner={uuid}` | 按创作者筛选（可选 `tags`） |

Web：**/creator/:userId** — 标签筛选与音色馆一致；音色馆卡片可点「创作者主页」。

音色馆 URL 支持 `?tags=短剧,男声` 与 `?pick={catalog_id}`（从创作者页跳回时自动选中）。

### 定价与授权（REQ-016–018）

| API | 说明 |
|-----|------|
| 发布时带 `license_type` / `price_cents` / `included_chars` / `prohibited_domains` | 上架即配置 LicensePolicy |
| `PATCH /catalog/voices/{id}/license` | Owner 更新定价（已购订单快照不变） |
| `POST /catalog/voices/{id}/purchase` | 模拟支付，生成 `voice_authorizations` |
| `GET /authorizations` | 买家我的授权 |
| `GET /authorizations/{id}/certificate` | JSON 授权凭证（含 HMAC 签章） |
| `GET /authorizations/{id}/verify` | 公开验真 |

付费音色（`price_cents > 0`）未购买时 `can_use=false`；合成成功按字符扣减授权额度。

### 侵权投诉（REQ-020）

| API | 说明 |
|-----|------|
| `POST /api/v1/complaints` | 用户提交工单 |
| `GET /api/v1/admin/complaints` | 运营待处理列表 |
| `POST /api/v1/admin/complaints/{id}/takedown` | 下架音色 + 撤销全部购买授权 |
| `POST /api/v1/admin/complaints/{id}/dismiss` | 驳回投诉 |

Web：音色馆底部「侵权投诉」；运营台 `/admin` 投诉队列 + 任务 Owner 筛选 + 一键复制 trace。

### 本地验收脚本

```powershell
# VoiceGrant 跨账号
python scripts/smoke_mvp1_grant.py

# 付费购买 → 凭证验真 → 投诉下架（需 platform + 用户 A 已有音色版本）
python scripts/smoke_mvp1_purchase.py
```

公开验真页：`/verify/{authorization_id}`（无需登录）。

## MVP+1 第一切片（已完成）

音色馆 + VoiceGrant + 定价/购买/凭证 + 投诉下架 + 运营台 + 创作者主页。

- [x] 审核流：发布 → `pending`，运营 approve/reject（Web 用户 C）
- [x] 标签搜索：`GET /catalog/tags` + `?tags=` 多标签 AND 筛选
- [x] 试听样音 URL：审核通过后自动排队生成 `demo_audio_url`（不占用户配额）
- [x] **Phase 0 运营只读 API**：`GET /api/v1/admin/jobs`、`GET /api/v1/admin/stats`
- [x] **用户主页 / 标签搜索**：`/creator/:userId`、音色馆 `?tags=` / `?pick=` URL 同步
- [x] **运营 Web**：`/admin` 任务台 + 投诉队列
- [x] **定价与授权（REQ-016–018）**：模拟购买、JSON 凭证、公开验真页 `/verify/:id`
- [x] **侵权投诉下架（REQ-020）**：`POST /complaints`、运营下架 + 撤销授权

## 下一步（MVP+1 第三切片候选）

- [x] REQ-006 相似度测评 / AB 试听（mock + `/quality` 页）
- [x] 授权凭证 PDF 导出
- [x] 真实 speaker embedding 评测管线（mel cosine + 引擎合成，`QUALITY_MOCK=false`）
- [x] REQ-002 三方 KYC（mock + 人工审核 + 训练门禁）
- [x] 支付订单台账（mock，`payment_orders` + 运营台）
- [x] 预下单 + webhook 回调骨架（mock confirm）
- [x] 卖家结算 / 提现骨架（REQ-028 mock 分账 + 运营审批）
- [x] REQ-030 对外 Open API（API Key + `/open/synthesis`）

## 本地 Smoke 速查

```powershell
.\scripts\platform_start.ps1
python scripts/smoke_mvp1_open_api.py
python scripts/smoke_mvp1_checkout.py
python scripts/smoke_mvp1_kyc.py
python scripts/smoke_mvp1_purchase.py
```

## 相关

- 需求：`VoiceGrant` — SRS §6.1
- 运营 SOP：附录 C.2 跨用户共享
