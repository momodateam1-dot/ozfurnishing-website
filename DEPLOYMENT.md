# 部署指南：GitHub + Cloudflare Pages + Cloudflare R2 + Namecheap

目标域名：**ozfurnishing.com**（www 与 http 全部 301 到 `https://ozfurnishing.com`）

---

## 架构

```
Namecheap (注册商, NS 指向 Cloudflare)
        ↓
Cloudflare DNS
   ├── ozfurnishing.com / www ──► Cloudflare Pages (静态站点 + Functions)
   │                                    └── /api/inquiry ──► R2 私有桶 oz-inquiries
   │                                                    └──► Resend (邮件通知)
   └── cdn.ozfurnishing.com ─────► R2 公开桶 oz-assets (图片)
```

---

## 一、GitHub 仓库

仓库：`https://github.com/momodateam1-dot/ozfurnishing-website.git`（分支 `main`）

站点文件已整理到**仓库根目录**（此前嵌套在两层子目录里，会导致 Pages 找不到入口）。

```bash
git add .
git commit -m "..."
git push origin main
```

推送后 Cloudflare Pages 会自动触发部署。

---

## 二、Cloudflare Pages 构建配置

Pages 已连接 GitHub 仓库，请在 **Settings → Builds & deployments** 确认：

| 项 | 值 |
|---|---|
| Framework preset | **None** |
| Build command | 留空 |
| Build output directory | `/` （根目录） |
| Root directory | 留空 |
| Production branch | `main` |

> 如果之前填过子目录路径（如 `OZ_International_Trading_Website_v3.0/...`），必须清空，否则部署会失败。

---

## 三、Pages Functions：环境变量与 R2 绑定

**Settings → Environment variables**（Production 与 Preview 都加）：

| 变量 | 说明 |
|---|---|
| `RESEND_API_KEY` | Resend API key（resend.com 免费额度足够），用于邮件通知 |
| `NOTIFICATION_EMAIL_TO` | 接收询盘的邮箱，如 `sales@ozfurnishing.com` |

**Settings → Functions → R2 bucket bindings**：

| Binding name | Bucket |
|---|---|
| `INQUIRY_BUCKET` | `oz-inquiries` |

两者都配置好后 `/api/inquiry` 才会返回 200。都不配置时返回 503，前端自动降级到邮件方式。

> 修改环境变量或绑定后需要**重新部署**一次才会生效（Deployments → Retry deployment）。

建议同时在 **WAF → Rate limiting rules** 给 `/api/inquiry` 加一条限流（如 10 次 / 分钟 / IP），防止刷单。

---

## 四、Cloudflare R2 配置

### 1. 公开桶 `oz-assets`（图片）

1. **R2 → Create bucket** → 名称 `oz-assets`
2. **Settings → Custom Domains → Connect Domain** → 填 `cdn.ozfurnishing.com`
   - Cloudflare 会自动签发 SSL 并接入 CDN
3. **Settings → CORS Policy** → 粘贴 `r2-cors.json` 内容
4. 上传 `assets/img/` 下的 6 张图（`hero-1.jpg` … `hero-6.jpg`）
5. 回到仓库执行：

```bash
python tools/switch-cdn.py cdn.ozfurnishing.com
```

这会把 CSS / HTML / 404 页里的 `/assets/img/hero-N.jpg` 全部替换为
`https://cdn.ozfurnishing.com/hero-N.jpg`，提交推送即可。

> 不上传也能上线 —— 图片本来就在仓库里。切 CDN 只是把流量从 Pages 挪到 R2。

### 2. 私有桶 `oz-inquiries`（询盘留档）

1. **R2 → Create bucket** → 名称 `oz-inquiries`
2. **保持私有**，不要开 Public Access、不要绑自定义域名
3. 在 Pages 里按上一节绑定为 `INQUIRY_BUCKET`

> ⚠️ 两个桶必须分开。如果把询盘写进 `oz-assets`，而该桶又绑了 `cdn.ozfurnishing.com`，
> 客户姓名、邮箱、采购需求会被公开下载。

---

## 五、Namecheap → Cloudflare DNS

### 1. Cloudflare 添加站点

**Cloudflare 首页 → Add a site** → 输入 `ozfurnishing.com` → 选 Free 计划。
Cloudflare 会给出两个 Nameservers，例如：

```
amy.ns.cloudflare.com
dave.ns.cloudflare.com
```

### 2. Namecheap 修改 NS

**Domain List → 域名右侧 Manage → Nameservers** → 选 **Custom DNS** → 填入上面两个 NS → 保存。

生效时间通常 5–30 分钟，最长 24 小时。

### 3. Cloudflare DNS 记录

进入 **DNS → Records**：

| Type | Name | Target | Proxy |
|---|---|---|---|
| `CNAME` | `@` | `ozfurnishing-website.pages.dev` | Proxied（橙色云） |
| `CNAME` | `www` | `ozfurnishing-website.pages.dev` | Proxied |
| `CNAME` | `cdn` | R2 自动创建（绑定自定义域名时生成） | Proxied |

> 把 `ozfurnishing-website.pages.dev` 换成 Pages 项目实际的 `*.pages.dev` 地址。
> 根域名用 CNAME 依赖 Cloudflare 的 CNAME Flattening，免费版支持。
> 若 Pages 提示需要验证，可在 Pages → Custom domains 里添加，Cloudflare 会自动写入记录。

### 4. SSL

**SSL/TLS → Overview** → 加密模式选 **Full (strict)**；
**Edge Certificates** 开启 **Always Use HTTPS** 和 **Automatic HTTPS Rewrites**。

---

## 六、上线验证清单

- [ ] `https://ozfurnishing.com` 首页正常，`https://www.ozfurnishing.com` 301 跳到主域
- [ ] 6 个页面导航全部可达，无 404
- [ ] 访问 `https://ozfurnishing.com/no-such-page` 显示自定义 404 页
- [ ] Hero 轮播、移动端抽屉菜单、FAQ 手风琴正常
- [ ] 提交询盘表单 → 页面显示绿色成功提示
- [ ] R2 桶 `oz-inquiries` 里出现 `inquiries/<日期>/...json`
- [ ] 销售邮箱收到 Resend 通知邮件
- [ ] `tel:` 链接在手机上能唤起拨号，号码为 `+86 180 2586 5699`
- [ ] WhatsApp 卡片跳转到 `wa.me/8618025865699`，二维码可正常展开
- [ ] 页脚微信 `guozai077885` 点击可复制
- [ ] `https://ozfurnishing.com/sitemap.xml` 与 `robots.txt` 可访问
- [ ] 响应头含 `Strict-Transport-Security`、`X-Content-Type-Options`（`_headers` 生效）
- [ ] 断网 / 停止 Functions 时提交表单，会降级显示邮件面板（不丢单）

---

## 七、回滚

Cloudflare Pages 保留全部历史部署：**Deployments** → 选任一历史版本 → **Rollback to this deployment**，即时生效，无需重新构建。

Git 侧用 `git revert <commit>` 后推送即可触发新部署。
