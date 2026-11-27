# 28 · Style-safe UI 重构交接（2026-11-28）

> owner: 霹雳马桶 · last_updated: 2026-11-28
> 给新会话：先读本文件，再读 `docs/agent/00-context.md` 与 `docs/product/04-design-system.md`。本文件记录一次被否掉的全站改版、回滚结果，以及当前只保留的“原风格内”改动。

## 1. 现在是什么状态

- PR 分支：`feat/style-safe-ui`，基于 `origin/main`（已含合并后的 PR #119 资产包）。
- 本地原分支：`feat/mascot-assets`，还有大量未提交 WIP；本 PR 只包含下列 style-safe 改动，不含那些 WIP。
- 前端页面视觉已经回到原版：冷灰底 `#F3F4F6`、8px 卡片圆角、10px frame 圆角、近零阴影、原 AppShell、原字体。
- 原 3x3 点阵 logo（`BrandMark.vue`）已保留，登录页、顶部栏、favicon 都是原版；**不要替换这个 logo**。
- 已完成：详情页 + 练习页的 style-safe（不改视觉语言）结构与交互调整；小纸最小接入（空状态 + 404）。
- 未完成：首页、错题本、录入/编辑、任务中心、统计、设置还没有做这一轮 style-safe 重构。
- 本 PR 已提交这些 style-safe 改动；本地原分支的其余 WIP 仍需单独处理。

## 2. 重要决策（不要重复踩坑）

### 2.1 不能改前端页面风格

用户明确要求：**不能改变原前端页面风格**。此前做过一版全站深度重构（暖纸、12/16px 圆角、阴影、sticky 顶栏、重排页面、金属小纸），被用户否掉，已整包回滚：

- 当前 `frontend/src/styles/tokens.css`、`global.css`、`arco-theme.css` 是原版，不要改。
- 不要引入暖纸背景、渐变大面积、重阴影、新圆角体系、侧边栏、sticky 重排。
- 新改动只做：信息层级、文案、空/错/加载/部分成功状态、任务进度表达、操作顺序、可访问性。
- 如要改布局，先让用户确认“允许改布局但仍保留原视觉”；未确认前只做内容/状态层。

### 2.2 小纸资产的正确口径

- 正式资产：PR #119 已合并到 main（`docs/product/drafts/mascot-kit/`，v1.0.0）。
  - 平面：`mascot-body.svg`、`mascot-mark.svg`、`states/state-{curious,thinking,happy,error}.svg`。
  - 应用副本：`frontend/src/assets/mascot/` 下同名 6 个文件（与 kit 的 blob 哈希一致）。
  - manifest：状态表情建议 ≥120px；≤48px 用 mark；平面透明、无投影/渐变。
- 实际 3D 样式页：`http://127.0.0.1:5182/docs/product/drafts/mascot-3d/index.html`（需静态服务器；源码在 `docs/product/drafts/mascot-3d/index.html`）。
  - 样式是 Three.js 挤出卡片：正面纯平纸面、蓝侧边/背面、粗墨线、无阴影。
  - 应用内没有引入 WebGL；用 `Mascot3D.vue`（正式前脸/状态 SVG + 蓝色硬 `drop-shadow`）模拟 3D 侧边，只出现在 `EmptyState` 和 404。
- 不要使用未跟踪的材质试验资产：`mascot-metal.svg`、`state-metal-*.svg`、`mascot-default.svg`、`mascot-celebrate.svg`、`mascot-skill-variant.svg`。
- 不要把 `docs/product/drafts/mascot-metal.html`、`mascot-preview.html`、`mascot-compare.html`、`page-map*` 当作应用资产提交。
- 仓库根目录有一个未跟踪的 `{const` 文件，是之前遗留的，不要提交。

### 2.3 被回滚的改版备份

完整改版（含首页/列表/任务/统计/设置的新布局、MascotNote、HomeHero 等）只存在于本机临时目录：

`%TEMP%\bababoi-redesign-backup\`（`frontend-src`、`docs`、`frontend` 等）

它不在仓库里，可以被当作“信息架构参考”，但**不要直接复制它的样式**。如果用户允许改布局，可以从中取结构，再套回原版 tokens/组件外观。

## 3. 本次已改文件（style-safe）

- `frontend/src/components/common/Mascot3D.vue`（新增）
  - 正式小纸前脸/状态 SVG + 蓝色硬挤出；不做动画、不引入 WebGL。
- `frontend/src/components/common/EmptyState.vue`
  - 默认插图从通用文档图标换成 `Mascot3D`（32px，仍在原 40px 浅色方框内）。
- `frontend/src/views/NotFoundView.vue`
  - 404 卡片顶部加入 44px `Mascot3D`（curious）；原 404 文案、按钮、卡片样式不变。
- `frontend/src/views/QuestionDetailView.vue`
  - H1 从“错题详情”改为章节名（如“导数与极值”），回退到 subject/分析考点；副标题补题型。
  - 其余布局、样式、轮询、重试、删除逻辑未动。
- `frontend/src/components/question/GeneratedQuestionCard.vue`
  - 每道相似题增加题型 `.tag`（解答题/选择题/填空题），与难度并列。
- `frontend/src/views/PracticeView.vue`
  - 入口按钮文案改为“去错题本挑一道”。
  - 进度条下增加一行“已答 N 题 · 答对 N · 待复习 N”（有已答记录时才显示）。
- `frontend/src/components/practice/PracticeQuestionCard.vue`
  - 自评改为“先查看答案，再自评”；未看答案时“会/不会”禁用；没有参考答案的题仍可直接自评。
  - 原有提交/失败/重试、选项、填空、计时逻辑未动。
- `frontend/src/components/practice/PracticeResultPanel.vue`
  - 结果头部按成绩给下一步：全对 / 全错 / 部分正确三种文案；原有统计、逐题记录、掌握度同步未动。

- `frontend/src/types/components.d.ts`
  - 构建自动补充 `Mascot3D` 声明；随本 PR 一起提交，避免本地与 CI 生成差异。

本 PR 只包含上述文件；本地原分支的其他未提交 WIP 不会进入本 PR。

## 4. 已验证

在 `frontend/` 下执行：

- `pnpm typecheck`：通过。
- `pnpm lint`：通过，0 warning。
- `pnpm test`：11 个测试文件、55 项全部通过。
- `pnpm build`：通过。
- 手工验证：详情页 → 去练习 → 看答案 → 自评 → 下一题 → 结果页；空状态；404。
- 预览：`pnpm dev` 后默认 `http://127.0.0.1:5173`；本次运行在 `http://127.0.0.1:5190`。演示账号 `student01 / password123`。

## 5. 未完成 / 下一步

1. **首页**：保持原布局；可做数据驱动的“下一步”描述（草稿/失败任务/首次录入），不要新增视觉块。
2. **错题本**：保持筛选/卡片/分页原样；可补筛选结果与掌握状态的文案、空状态说明。
3. **录入/编辑**：保持原两栏、原面板；可做区块编号、字段顺序、校验提示、保存后说明等结构层调整。
4. **任务中心**：保持 5 列纸面列表；可补状态摘要、失败原因与重试引导、分段展开说明。
5. **统计**：保持 KPI/表格/趋势原样；可把薄弱知识点做成可点击的筛选链接、补数据口径说明。
6. **设置**：保持原表单；可补 AI Key 状态说明、修改密码注意事项、分区锚点（需用户确认是否算布局改动）。
7. **关键待拍板**：是否允许“改布局但不改视觉”。如果不允许，只做文案/状态/交互；如果允许，可参考临时备份的结构，但必须套回原版 tokens。
8. **3D 小纸**：当前是静态 SVG + 蓝色挤出；如果要真正嵌入 Three.js 交互，需要单独确认（会增加 WebGL/体积，且可能影响页面观感）。

## 6. 新会话启动提示词

把下面这段直接贴给新会话：

```text
继续 Bababoi Learning Machine 前端 style-safe UI 重构。
先读 docs/agent/28-style-safe-ui-handoff-20261128.md。

硬约束：
- 保留原 Calm Academic 视觉、原 3x3 点阵 logo、原 tokens/AppShell/布局骨架。
- 不改配色、字号、圆角、阴影；不引入暖纸背景、重阴影、新卡片语言。
- 小纸只用 PR #119 的正式平面资产（mascot-body/mark/state-*）；不要用 metal/default/celebrate/skill 未跟踪试验文件。
- 空状态/404 可以用 Mascot3D；其他位置先不要扩散。
- 不要整包回滚工作区；提交时只挑本次相关文件。

已完成：详情页、练习页的 style-safe 调整；小纸空状态/404 接入；typecheck/lint/test/build 全过。
下一步：先做首页/错题本/录入/任务中心/统计/设置，逐页先给“只改信息层级/状态/交互”的方案，再实现。
如果某页需要改布局，先问我是否允许“改布局但不改视觉”。
每步运行 pnpm typecheck / pnpm lint / pnpm test / pnpm build。
```
