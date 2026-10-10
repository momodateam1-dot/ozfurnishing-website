# ozfurnishing.com — OZ International 独立站

静态外贸独立站，托管在 **Cloudflare Pages**，源码在 **GitHub**，图片走 **Cloudflare R2**，域名在 **Namecheap**（DNS 托管给 Cloudflare）。

站点无构建步骤：Cloudflare Pages 直接拉取仓库根目录并分发。

## 技术栈

| 层        | 选型                                                       |
| -------- | -------------------------------------------------------- |
| 源码       | GitHub `momodateam1-dot/ozfurnishing-website`（分支 `main`） |
| 托管 / CDN | Cloudflare Pages（无构建命令，输出目录 `.`）                         |
| 询盘接口     | Cloudflare Pages Functions（`functions/api/inquiry.js`）   |
| 对象存储     | Cloudflare R2：`oz-assets`（公开图片）、`oz-inquiries`（私有询盘）     |
| 域名       | Namecheap 注册 → Cloudflare DNS 托管                         |

## 目录结构

```
/
├─ index.html            首页
├─ c-sourcing.html       C 端小额定购
├─ b2b-procurement.html  B2B / 工程采购
├─ process.html          四步流程
├─ about.html            关于我们
├─ inquiry.html          询盘表单 + FAQ
├─ privacy.html          隐私政策（不披露注册名/注册地址）
├─ legal.html            法律声明 / 使用条款
├─ 404.html              自定义 404
├─ assets/
│  ├─ style.css          样式（唯一源）
│  ├─ main.js            交互（唯一源）
│  ├─ favicon.svg
│  └─ img/               hero-1..6.jpg
├─ functions/
│  └─ api/inquiry.js     POST /api/inquiry → R2 + 邮件通知
├─ tools/
│  └─ switch-cdn.py      本地图片 ↔ R2 CDN 域名切换
├─ _headers              缓存与安全响应头
├─ _redirects            www / http → HTTPS 主域
├─ wrangler.toml         本地 `wrangler pages dev` 配置
├─ robots.txt
├─ sitemap.xml
└─ r2-cors.json          oz-assets 桶的 CORS 策略模板
```

## 本地预览

```bash
# 纯静态预览（不含 Functions）
python -m http.server 8080

# 完整预览（含 /api/inquiry，需要 R2 绑定）
npx wrangler pages dev .
```

> 图片使用根相对路径 `/assets/img/...`，所以必须通过 HTTP 服务器访问，直接双击 `index.html`（`file://`）图片会加载不到。

## 询盘接口

`POST /api/inquiry`，JSON body：

```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "company": "Example Ltd",
  "country": "Germany",
  "messenger": "+49 ...",
  "inquiryType": "B2B / bulk procurement",
  "quantity": "500 sets",
  "timeline": "Within 3 months",
  "details": "Outdoor sofa set, aluminium frame...",
  "reference": "https://..."
}
```

行为：

- 校验 `name` / `email` / `details` 必填，邮箱格式，字段长度上限；
- 写入 R2 私有桶 `oz-inquiries`，键名 `inquiries/YYYY-MM-DD/<timestamp>-<rand>.json`；
- 若配置了 `RESEND_API_KEY` + `NOTIFICATION_EMAIL_TO`，同时发邮件通知；
- 两者都没配置时返回 `503`，前端自动降级到「打开邮件 App / 复制详情」。

前端在 `assets/main.js` 中提交，任何网络或服务端失败都会回退到邮件方式，不会丢单。

## 图片与 R2

1. 现在图片在仓库内 `assets/img/`，已可正常上线。
2. 把 `assets/img/*` 上传到 R2 桶 `oz-assets`，并给桶绑定自定义域名 `cdn.ozfurnishing.com`。
3. 执行切换脚本，把引用改为 CDN：

```bash
python tools/switch-cdn.py cdn.ozfurnishing.com   # 切到 CDN
python tools/switch-cdn.py --local                # 切回本地
```

## 联系方式（已配置）

| 渠道 | 值 |
|---|---|
| 邮箱 | `807735000@qq.com` |
| WhatsApp / 电话 | `+86 180 2586 5699`（[wa.me/8618025865699](https://wa.me/8618025865699)） |
| 微信 | `guozai077885`（页脚可点击复制） |
| WhatsApp 二维码 | `assets/img/whatsapp-qr.png`，询盘页可展开查看 |

## 发布前必做

- [ ] 确认 `807735000@qq.com` 能正常收信
- [ ] 确认 WhatsApp / 电话 `+86 180 2586 5699` 可接通，二维码与号码一致
- [ ] 确认微信号 `guozai077885` 可被搜索添加
- [ ] 替换 `assets/img/hero-*.jpg` 为公司自有版权图片（当前为 Unsplash 下载，商用需授权）
- [ ] 核对 `<24h` 响应、`100%` 出货前检验、支持文件格式等业务承诺
- [ ] 补充公司注册名称、地址、隐私政策与法律声明

完整分步操作见 `DEPLOYMENT.md`。
