# 支付订单台账（mock）

> 状态：**MVP+1 运营可见性**；REQ-028 分账/提现属 GA

## 能力

| 能力 | 说明 |
|------|------|
| 购买落单 | `POST /catalog/voices/{id}/purchase` 同时写入 `payment_orders` |
| 运营查询 | `GET /api/v1/admin/payments` |
| Web | `/admin` 近期订单表 |

## 表 `payment_orders`

- `authorization_id` / `buyer_user_id` / `seller_user_id`
- `amount_cents` / `currency`（默认 CNY）
- `status`：`paid`（mock 即时成功）
- `provider`：配置项 `PAYMENT_PROVIDER`（默认 `mock`）
- `provider_ref`：与授权 `payment_ref` 一致

## 异步结账（MVP+1 第五切片）

| 步骤 | API | 说明 |
|------|-----|------|
| 预下单 | `POST /catalog/voices/{id}/checkout` | 付费音色 → `pending` 订单 |
| Mock 确认 | `POST /payments/orders/{id}/mock-confirm` | 买家完成模拟支付 |
| Webhook | `POST /payments/webhooks/{provider}` | `X-Payment-Signature` HMAC-SHA256 |
| 轮询 | `GET /payments/orders/{id}` | 查询订单状态 |
| 即时购买 | `POST /catalog/voices/{id}/purchase` | 免费音色 / `PAYMENT_CHECKOUT_ASYNC=false` |

配置：

```env
PAYMENT_PROVIDER=mock
PAYMENT_WEBHOOK_SECRET=dev-payment-webhook-secret-change-me
# PAYMENT_CHECKOUT_ASYNC=true
```

Web 音色馆付费购买走 `checkout` + `mock-confirm`。

## 后续（REQ-028）

- 微信/支付宝预下单 + 回调 webhook
- 卖家结算与提现
