# REQ-028 卖家结算与提现（GA 骨架）

> 状态：**mock 分账 + 运营提现审批**

## 能力

| 能力 | API | 说明 |
|------|-----|------|
| 销售入账 | 支付订单 `paid` 时自动 | 扣除平台费（默认 15%）计入卖家钱包 |
| 卖家钱包 | `GET /seller/wallet` | 可提现 / 待打款 / 累计收入 |
| 账本 | `GET /seller/ledger` | 销售入账、提现冻结/打款/驳回 |
| 申请提现 | `POST /seller/payouts` | 最低金额 `SETTLEMENT_MIN_PAYOUT_CENTS` |
| 运营审批 | `POST /admin/payouts/{id}/approve` | mock 打款 |
| 运营驳回 | `POST /admin/payouts/{id}/reject` | 余额退回 |

## 配置

```env
SETTLEMENT_PLATFORM_FEE_BPS=1500
SETTLEMENT_MIN_PAYOUT_CENTS=10000
```

## Web

- 音色馆「卖家钱包」面板：余额 + 申请提现
- 运营台「卖家提现队列」

## 本地验证

```powershell
python scripts/smoke_mvp1_checkout.py
# 卖家用户打开 /catalog 查看钱包
# 运营 /admin 审批提现
pytest tests/test_settlement_api.py -q
```

## 后续

- 对接微信/支付宝企业付款
- 税务发票与对账报表
