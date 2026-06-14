# MVP+1 音色馆 + VoiceGrant（第一切片）

> 状态：**进行中** — 不含定价/支付/聊天

## 目标

让用户 **浏览精选音色** 并 **跨账号使用**，为后续交易市场打基础。

## 已实现（本切片）

| 能力 | API | 说明 |
|------|-----|------|
| 音色馆列表 | `GET /api/v1/catalog/voices` | 已发布、可合成 |
| 发布到馆 | `POST /api/v1/catalog/voices` | 仅音色 owner |
| 授权他人 | `POST /api/v1/voices/{id}/grants` | VoiceGrant |
| 我的授权 | `GET /api/v1/voice-grants` | 被授权方可见 |
| 撤销授权 | `DELETE /api/v1/voice-grants/{id}` | 授权方 |
| 合成权限 | 合成/批量门禁 | owner / 公开馆 / 有效 Grant |

Web：**/catalog** 音色馆页

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

```json
POST /api/v1/voices/{voice_id}/grants
{ "grantee_user_id": "..." }
```

## 下一步（MVP+1 续）

- [ ] 审核流：发布需运营 approve
- [ ] 试听样音 URL（预生成 demo）
- [ ] 用户主页 / 搜索标签
- [ ] 定价与授权凭证（REQ-016–018）
- [ ] 侵权投诉下架（REQ-020）

## 相关

- 需求：`VoiceGrant` — SRS §6.1
- 运营 SOP：附录 C.2 跨用户共享
