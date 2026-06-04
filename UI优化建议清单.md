# 伊家人 UI优化建议清单

检查日期: 2026-06-04
检查范围: 管理后台(http://43.163.5.90) + 小程序(~10页WXML/WXSS)
设计规范: 暖金色#c8a052主题 · PingFang SC字体 · 适老化×1.4

---

## 一、高优先级（影响核心体验/规范合规）

### 1. 管理后台与小程序的暖金色不一致 【规范问题】

- 管理后台: 严格使用 #c8a052 (rgb 200,160,82)，CSS变量为 --gold:#c8a052
- 小程序全局: 使用 #C8A96E (rgb 200,169,110)，比规范色偏黄偏亮约 +28 蓝色通道
- 影响范围: 小程序所有页面，包括header渐变、按钮、标签、选中态、价格等
- 建议: 小程序全局替换 #C8A96E → #c8a052，辅助色 #D4B896 → #e0c882，深色 #A8894E → #9a7a32

### 2. Dashboard营收图表仅占位未实现 【功能缺失】

- dashboard.html 第108行: 图表区域显示"📊 营收图表API开发中"
- 近7天营收趋势是仪表盘核心指标，当前无法展示
- 建议: 接入 /api/dashboard/revenue-history 或等价接口，用CSS bar chart已有样式渲染

### 3. 门店切换使用粗暴的iframe强制刷新 【交互缺陷】

- index.html 第86行: `iframe.src = iframe.src` 导致白屏闪烁
- Dashboard页面未处理 hotelChange postMessage，切换门店后数据不过滤
- 建议: 
  - 去掉强制刷新，仅发送 postMessage
  - Dashboard接收消息后，将hotelId作为参数传给 /api/dashboard/stats?hotel_id=xxx
  - 添加切换过渡动画（淡入淡出）

### 4. 小程序字体大小普遍未达到适老化标准 【无障碍】

- 设计规范要求 ×1.4 字体缩放
- 当前基准 28rpx (≈14px)，适老应 ≥ 39rpx (≈19.6px)
- 实测大量文本远低于此标准:

| 元素 | 当前 | ×1.4 后应达到 |
|------|------|--------------|
| 房型标签 .room-tag-item | 20rpx | 28rpx |
| 特色描述 .feature-desc | 20rpx | 28rpx |
| 筛选标签 .filter-tag | 24rpx | 34rpx |
| 表单项文字 .form-label | 26rpx | 36rpx |
| 搜索框 .search-input | 26rpx | 36rpx |
| 菜单徽标 .menu-badge | 20rpx | 28rpx |
| 库存提示 .room-stock | 22rpx | 31rpx |
| 日期标签 .date-label | 22rpx | 31rpx |

- 建议: 
  - app.wxss 中 page 添加 `font-size: 39rpx` (28×1.4) 作为适老基准
  - 所有字号统一上调1.4倍
  - 或提供"大字版"开关，通过CSS变量动态缩放
  - 优先处理 20-24rpx 的极小字体

### 5. 管理后台多处字体过小不符合适老标准 【无障碍】

- 管理后台基准 font-size:14px，适老应 ≥ 19.6px
- 问题元素:
  - 门店选择器 #storeSelector: font-size:12px → 应 17px
  - 运营概览标签 .summary-item .lbl: font-size:11px → 应 15px
  - 表格文字 table: font-size:13px → 应 18px
  - 按钮 .btn: font-size:13px → 应 18px
  - 侧边栏页脚 .sidebar-footer: font-size:12px → 应 17px
  - 面包屑 .breadcrumb: font-size:14px → 应 20px
- 建议: 在 :root 添加 --font-scale: 1.4 变量，所有 font-size 通过 calc 引用该变量

---

## 二、中优先级（影响信息清晰度/视觉品质）

### 6. 小程序低对比度文字不符合WCAG AA 【可读性】

- app.wxss 定义 .text-light { color: #8B7E6A }，在 #FAF7F2 背景上的对比度约 3.5:1
- #B0A492 文字在暖色背景上对比度约 2.5:1，远低于 WCAG AA 要求的 4.5:1
- 受影响: 筛选标签默认态、特色描述、空状态文字、日期标签等
- 建议: 将辅助文字色从 #B0A492 加深至 #8A7D6A，确保对比度 ≥ 4.5:1

### 7. 管理后台侧边栏导航项间距拥挤 【布局】

- nav-item 使用 margin:2px 12px，视觉上各导航项紧贴
- 导航组标题 .nav-group-title padding 仅 8px 8px 4px，与下一组区分弱
- 建议: 
  - nav-item margin 改为 4px 12px
  - nav-group-title 增加 margin-top: 16px
  - 导航组之间增加 1px 分割线或更大间距

### 8. 小程序门店切换入口不明显 【交互】

- 首页门店卡片中有"切换门店"按钮(.btn-ghost)，但视觉权重低
- 顶部header-bar的城市定位区域可点击但无明确引导
- 建议: 
  - header-bar 定位区域增加"切换 ▾"文字标签
  - .btn-ghost 加深背景色至 rgba(200,160,82,0.15)

### 9. 管理后台登录页设计过于朴素 【品牌感知】

- 登录页背景纯黑渐变(#1e1c18→#2c2416)，与系统内暖金米色风格割裂
- 登录卡片仅360px宽，logo只有emoji 🏨
- 建议: 
  - 背景改用暖金色渐变或米色系
  - 添加品牌logo图片替代emoji
  - 卡片宽度增至400px，增加阴影层次

### 10. 小程序Banner轮播无实际图片 【内容缺失】

- index.wxml 第70行: swiper使用 .img-placeholder 占位
- 所有房型卡片图片区也是占位符
- 建议: 优先上传3-5张酒店实景图，占位符仅做fallback

---

## 三、低优先级（细节打磨/未来迭代）

### 11. 管理后台缺少全局字体缩放控件 【功能建议】

- 当前无任何字体大小调节入口
- 建议: 在 header-actions 增加 A-/A+ 按钮，切换 --font-scale 变量(1.0/1.2/1.4)

### 12. 小程序缺少TabBar图标自定义 【视觉】

- 未见自定义tabBar图标配置(app.json未检查但代码中未见)
- 建议: 使用暖金色系定制底部导航图标

### 13. 管理后台table hover色与选中色区分弱 【反馈】

- table tr:hover 背景 #fdfbf6 与默认白色区别微小
- 建议: hover色加深至 #faf5ea 或添加左侧金色细线指示

### 14. 小程序btn-primary与全局.btn-primary重复定义 【代码质量】

- app.wxss 全局定义 .btn-primary (font-size:30rpx)
- booking.wxss 再次定义 .btn-primary (font-size:30rpx) 覆盖
- 建议: 各页面只定义局部覆盖，删除完全一致的重复规则

### 15. 管理后台移动端(≤768px)门店选择器隐藏 【响应式】

- 移动端 sidebar 收缩至48-56px时，header中的storeSelector仍然存在但字体12px
- 建议: 移动端考虑将门店选择放入汉堡菜单或独立操作栏

---

## 汇总统计

- 高优先级: 5项 (规范不一致、功能缺失、交互缺陷、无障碍)
- 中优先级: 5项 (可读性、布局、交互、品牌感知、内容缺失)
- 低优先级: 5项 (功能建议、视觉打磨、代码质量、响应式)

共15条建议，预估核心修复工作量约 3-5 人天。
