# OZ International 独立站完整部署指南
## 技术栈：GitHub + Vercel + Cloudflare R2 + Namecheap

---

### 一、架构总览与分工

```
[Namecheap 域名购买]
       ↓ (将 NS 修改指向 Cloudflare DNS)
[Cloudflare 全球边缘网络]
   ├── 主站域名 (oz-international.com / www) ──> [Vercel 托管前端 & Serverless 询盘 API]
   └── 媒体资源 (cdn.oz-international.com)  ──> [Cloudflare R2 存储桶 (图片/PDF/大文件)]
```

---

### 二、步骤一：将代码推送到 GitHub

1. 在 GitHub 上新建一个 Repository（例如：`oz-international-site`，选择 **Private** 或 **Public**）。
2. 在本地进入该项目目录并执行以下命令：

```bash
cd "C:\Users\cnkik\Desktop\WINK\独立站\OZ_International_Trading_Website_v3.0\OZ_International_Website_v3.0"

# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 提交初始版本
git commit -m "feat: initial commit for OZ International Website v3.0"

# 关联远程仓库并推送
git branch -M main
git remote add origin https://github.com/你的GitHub用户名/oz-international-site.git
git push -u origin main
```

---

### 三、步骤二：在 Vercel 导入并一键部署

1. 打开 [Vercel 控制台](https://vercel.com/)，使用 GitHub 账号登录。
2. 点击 **"Add New..." -> "Project"**。
3. 在列表中找到刚刚创建的 `oz-international-site`，点击 **"Import"**。
4. **Project Settings** 配置：
   - **Framework Preset**: 选择 `Other`（纯静态 + Serverless API 架构）；
   - **Root Directory**: 保持根目录 `./`；
   - **Build Command**: 留空（纯静态无需编译，即时秒级部署）；
   - **Output Directory**: 留空。
5. （可选）在 **Environment Variables** 添加：
   - `NOTIFICATION_EMAIL_TO`: 你的询盘接收邮箱（如 `sales@oz-international.com`）；
   - `RESEND_API_KEY`: （如果需要免费邮件即时提醒，可在 resend.com 申请）。
6. 点击 **"Deploy"**，等待 10~20 秒即可获得一个 `*.vercel.app` 临时测试地址。

---

### 四、步骤三：配置 Cloudflare R2 对象存储

1. 登录 [Cloudflare 控制台](https://dash.cloudflare.com/)，进入 **R2 Object Storage**。
2. 点击 **"Create bucket"**，命名为 `oz-assets`。
3. **设置 CORS（允许跨域加载）**：
   - 进入存储桶 -> **Settings** -> **CORS Policy**；
   - 点击 **Add CORS Policy**，直接将项目中的 `r2-cors.json` 内容粘贴进去保存。
4. **绑定自定义域名（享受全球免费 CDN 加速）**：
   - 在存储桶 Settings -> **Custom Domains**；
   - 点击 **Connect Domain**，输入例如 `cdn.oz-international.com`；
   - Cloudflare 会自动为你创建 SSL 证书和 CDN 加速。
5. 上传高清产品图、公司资质 PDF 或视频至 R2，在网页中即可直接通过 `https://cdn.oz-international.com/文件名` 引用。

---

### 五、步骤四：Namecheap 域名解析与上线

#### 推荐方案：将 Namecheap 域名托管给 Cloudflare DNS（性能最优、免费 SSL、最不易出错）

1. **在 Cloudflare 添加站点**：
   - 在 Cloudflare 首页点击 **"Add a Site"**，输入你在 Namecheap 购买的域名（例如 `oz-international.com`），选择 **Free** 计划。
   - Cloudflare 会分配 2 个 Nameservers（例如：`amy.ns.cloudflare.com` / `dave.ns.cloudflare.com`）。
2. **在 Namecheap 修改 DNS**：
   - 登录 Namecheap -> **Domain List** -> 点击你的域名后的 **Manage**；
   - 找到 **Nameservers** 项，选择 **Custom DNS**；
   - 将 Cloudflare 提供的 2 个 Nameservers 填入并保存（通常 5~30 分钟内全球生效）。
3. **在 Cloudflare 配置 DNS 解析到 Vercel**：
   - 进入 Cloudflare 该域名的 **DNS -> Records**，添加以下两条记录：
     - **记录 1 (根域名)**：
       - Type: `CNAME` (或 `A`)
       - Name: `@`
       - Target: `cname.vercel-dns.com` (若用 A 记录填 `76.76.21.21`)
       - Proxy status: `DNS only` (灰色云朵，由 Vercel 自动颁发 SSL)
     - **记录 2 (www 子域名)**：
       - Type: `CNAME`
       - Name: `www`
       - Target: `cname.vercel-dns.com`
       - Proxy status: `DNS only`
4. **在 Vercel 绑定自定义域名**：
   - 进入 Vercel 项目 -> **Settings** -> **Domains**；
   - 输入你的域名 `oz-international.com` 和 `www.oz-international.com`；
   - Vercel 验证 DNS 成功后，自动生成全球 HTTPS 证书。

---

### 六、完成上线与验证清单

- [ ] 打开 `https://你的域名`，测试首页及各导航子页面访问是否正常；
- [ ] 提交 Inquiry 询盘表单，测试 `/api/inquiry` 接口响应与状态反馈；
- [ ] 检查测试 404 页面（访问 `https://你的域名/not-found-test`）；
- [ ] 检查 R2 上的图片或资源链接加载速度。
