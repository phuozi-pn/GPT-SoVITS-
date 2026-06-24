# 支付宝沙箱联调指南（无自有域名）

**日期**: 2026-06-22  
**适用**: 本地开发 + ngrok 穿透，尚未购买正式域名

## 你需要准备

| 项 | 说明 |
|----|------|
| 支付宝开放平台账号 | [open.alipay.com](https://open.alipay.com/) |
| ngrok（或同类穿透） | 给本地 API 一个 HTTPS 公网地址 |
| 沙箱买家账号 | 开放平台 → 开发工具 → 沙箱 |

无需正式域名、无需 ICP 备案即可在沙箱扫码测试。

---

## 第一步：获取沙箱密钥

1. 登录 [支付宝开放平台](https://open.alipay.com/)
2. **开发工具 → 沙箱**
3. 记录：
   - **沙箱 APPID**（形如 `9021...`）
   - **沙箱买家账号 / 登录密码**（用于 App 付款）
4. **沙箱应用 → 开发信息 → 接口加签方式**
   - 选择 **RSA2**
   - 使用 [支付宝密钥工具](https://opendocs.alipay.com/common/02kipk) 生成密钥对
   - 上传 **应用公钥**
   - 保存 **应用私钥** 到本机，例如 `C:/secrets/alipay_sandbox_private.pem`
   - 下载 **支付宝公钥**（后续接 notify 验签用，当前可留存）

---

## 第二步：ngrok 暴露本地 API

```powershell
# 终端 1：启动平台 API（默认 8001）
.\scripts\platform_start.ps1 -Background

# 终端 2：穿透（需先安装 ngrok 并 login）
ngrok http 8001
```

复制 Forwarding 地址，例如：`https://abc123.ngrok-free.app`

> ngrok 免费版地址每次重启会变，变了要同步改 `.env` 和支付宝沙箱配置。

---

## 第三步：配置 `.env`

在项目根目录 `.env` 增加或修改：

```env
PAYMENT_PROVIDER=alipay
PAYMENT_NOTIFY_BASE_URL=https://abc123.ngrok-free.app
PAYMENT_WEBHOOK_SECRET=dev-sandbox-webhook-secret-change-me

WEB_PUBLIC_BASE_URL=https://abc123.ngrok-free.app

ALIPAY_APP_ID=你的沙箱APPID
ALIPAY_PRIVATE_KEY_PATH=C:/secrets/alipay_sandbox_private.pem
ALIPAY_GATEWAY=https://openapi-sandbox.dl.alipaydev.com/gateway.do
```

重启 API 使配置生效：

```powershell
.\scripts\platform_start.ps1 -Background
```

---

## 第四步：支付宝沙箱里填「网址」

在 **沙箱应用** 配置页（若字段存在）：

| 字段 | 填写 |
|------|------|
| 应用首页 / 网关 | `https://abc123.ngrok-free.app` |
| 服务器异步通知 | `https://abc123.ngrok-free.app/api/v1/payments/webhooks/alipay` |

我们每次预下单也会在 `notify_url` 里带上完整路径，与上表一致即可。

---

## 第五步：Web 端购买测试

```powershell
# 终端 3：前端
.\scripts\web_dev.ps1
```

1. 浏览器打开 `http://127.0.0.1:5173`
2. 切换买家账号：**用户 B**（`aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa`）
3. 音色馆 → 选择付费演示音色（¥99）→ **购买**
4. 弹窗显示 **支付宝二维码**
5. 手机安装 **支付宝沙箱版 App**（开放平台沙箱页有下载链接）
6. 用 **沙箱买家账号** 登录沙箱 App → 扫码付款

---

## 第六步：支付成功后确认订单

付完款后执行（将 UUID 换成 checkout 返回值）：

```powershell
python scripts/confirm_payment_webhook.py `
  --order-id "订单UUID" `
  --provider-ref "chk_xxxxxxxx" `
  --provider alipay
```

成功后 Web 购买弹窗会在轮询中变为 **已授权**（每 3 秒查一次订单状态）。

---

## 仅测 API 出码（不出 Web）

```powershell
python scripts/smoke_alipay_sandbox_checkout.py
```

输出 `qr_code_url` 后，用沙箱 App 扫码；付完再按第六步 webhook 确认。

---

## 常见问题

| 现象 | 处理 |
|------|------|
| `ALIPAY_NOT_CONFIGURED` | 检查 APPID、私钥路径、`PAYMENT_NOTIFY_BASE_URL` |
| `Alipay precreate rejected` | 沙箱未签约当面付；检查 APPID 是否沙箱、网关是否沙箱地址 |
| 付完款页面仍「待支付」 | 正常：notify 未接；执行第六步 webhook |
| ngrok 502 | 确认 `platform_start` 在 8001 运行 |
| 不能买自己的音色 | 换用户 B 购买，用户 A 是卖家 |

---

## 与正式环境的差异

| | 沙箱 | 正式 |
|--|------|------|
| 网关 | `openapi-sandbox.dl.alipaydev.com` | `openapi.alipay.com` |
| APPID | 沙箱 APPID | 正式应用 APPID |
| 公网地址 | ngrok 临时域名 | 备案域名 + HTTPS |
| 收款 | 虚拟金额 | 真实资金 |

---

## 相关

- 预下单实现：`voice_platform/payment/providers/alipay.py`
- Mock 结账 smoke：`scripts/smoke_mvp1_checkout.py`
- 架构索引：[MVP+1 音色馆](./2026-06-18-MVP+1音色馆与VoiceGrant.md)
