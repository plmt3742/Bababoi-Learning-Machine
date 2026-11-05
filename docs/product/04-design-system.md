# 04 · 设计系统

> 目标：用一套 tokens + 组件清单，让前端不用每个页面重新决定颜色/间距/状态。优先复用 Arco Design Vue，不造轮子。

## 1. 设计原则

1. **可读性优先（第一原则）**：题干/公式/解析是主角；1366×768 投影下正文 ≥ 14px，对比度 ≥ 4.5:1；长公式自身横向滚动，不挤爆布局；不为视觉牺牲可读性。
2. **整体流畅（第二原则）**：一屏一个主操作；关键路径尽量 ≤ 3 步；加载/空/错/部分成功都有明确反馈；减少无意义跳转和弹窗；键盘与移动端操作顺手。
3. **内容优先**：题目/解析是主角，UI 不抢戏。
4. **层级清楚**：标题/正文/辅助文字三级足够。
5. **状态完整**：默认/悬停/焦点/禁用/加载/错误/空。
6. **克制用色**：1 个主色 + 语义色（成功/警告/错误）+ 中性色。
7. **Arco 优先**：能用 Arco 组件就不自研；自定义组件保持简单。

### 1.1 视觉语言评审基准（2026-11-05 确认）

所有风格变体、页面方案和组件方案按以下顺序评审：

1. **可读性**：题干、公式、答案、解析、标签在 1366×768 与 375px 下清晰；不截断关键信息；公式可横向滚动。
2. **整体流畅**：主操作路径清楚，状态反馈及时，减少无意义跳转/弹窗；键盘和移动端可用。
3. **一致性**：tokens、组件、间距、圆角、状态色统一。
4. **美感**：在前三项成立后加分，不用视觉 novelty 换可读性。

> 可读性/流畅性不达标的方案不进入定稿；风格评审先看 1/2，再看 3/4。
>
> 2026-11-05 已确认：详情页难度/删除只保留页头入口；录入页使用底部吸底操作栏；未掌握状态用红色；移除 M0 开发标识。

### 1.2 最终视觉方向（2026-11-06 更新：全量 Calm Academic）

以 `calm-academic/index.html` 为唯一视觉基准，前端整体覆写，不再做变体混搭：

- **AppShell**：桌面顶部 appbar + 1140px 纸面 frame + 32px 内边距，无侧边栏；移动端 52px appbar + 底部 4 项快捷导航。
- **页面结构**：Calm 的 kicker + 28px 标题 + 15/24 描述 + 右侧主操作；纸张面板用 1px hairline、8px 圆角、近零阴影。
- **列表**：可折叠筛选面板、卡片列表、mono 元数据、自定义分页。
- **录入**：1fr + 320px 两栏、题干编辑/预览、右侧题目信息与保存说明、sticky 操作卡。
- **详情**：主列 + 300px 右侧「处理进度」；原题/AI 分析/相似题为纸张面板；AI 分析 3 列元信息、编号错误原因、浅色解题摘要；生成题使用 01/02/03 大号编号 + 单条答案/解析折叠。
- **任务中心**：5 列纸面列表（任务/题目、阶段、状态、时间、操作），失败行 tinted + 行内错误/重试；筛选不吸顶。
- **色彩**：单一 Arco 蓝强调色；语义色使用低饱和深色 ink（success `#1B6E43`、warning `#8A5A00`、danger `#B42318`）。
- **不采用**：Studio 深色侧栏/全局高密度/编号步骤/sticky 筛选；Editorial 暖纸背景/衬线标题。

## 2. 颜色 Tokens

| Token | 建议值 | 用途 |
|---|---|---|
| `--color-primary` | `#165DFF`（Arco 蓝） | 主按钮、链接、选中 |
| `--color-primary-hover` | `#0E42D2` | 悬停（Calm 只加深，不提亮） |
| `--color-primary-active` | `#0E42D2` | 按下 |
| `--color-primary-soft` | `#EDF3FF` | 选中背景/浅蓝 wash |
| `--color-success` | `#1B6E43` | 正确、完成 |
| `--color-warning` | `#8A5A00` | 警告、待处理 |
| `--color-danger` | `#B42318` | 错误、删除 |
| `--color-bg` | `#F3F4F6` | 页面背景 |
| `--color-surface` | `#FFFFFF` | 卡片/面板 |
| `--color-text-1` | `#1B1F24` | 标题/正文 |
| `--color-text-2` | `#414A57` | 次要文字 |
| `--color-text-3` | `#5F6775` | 辅助/占位；小字号对比度 ≥ 4.5:1 |
| `--color-border` | `#E4E6EA` | 分割线/边框 |
| `--color-border-strong` | `#CFD3DA` | 输入/强调边框 |
| `--color-fill` | `#F3F4F6` | 标签/次级背景 |

> 不要超过 1 个主色 + 3 个语义色；不要用渐变做主背景。教育产品优先“干净、可信”，不是“炫酷 AI”。

## 3. 字体 Tokens

| Token | 值 | 用途 |
|---|---|---|
| `--font-sans` | `-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif` | 正文/UI |
| `--font-mono` | `"SFMono-Regular", Consolas, "Liberation Mono", monospace` | ID/时间/代码 |
| `--font-math` | `"Cambria Math", Cambria, "Times New Roman", "Songti SC", serif` | 讲义式数学/编号 |
| `--text-xs` | 14px / 22px | 标签/辅助（UI 下限） |
| `--text-sm` | 14px / 22px | 正文/表格/按钮 |
| `--text-base` | 16px / 28px | 题干/主要正文 |
| `--text-lg` | 18px / 28px | 小标题 |
| `--text-xl` | 22px / 32px | 卡片标题 |
| `--text-2xl` | 28px / 36px | 页面标题 |
| `--text-3xl` | 34px / 42px | 展示型数字 |

> 数学公式用 KaTeX 字体；不要给公式单独设中文字体。

## 4. 间距/圆角/阴影

| Token | 值 | 用途 |
|---|---|---|
| `--space-1` | 4px | 图标/文字间隙 |
| `--space-2` | 8px | 标签/紧凑 |
| `--space-3` | 12px | 表单内 |
| `--space-4` | 16px | 卡片内/常规 |
| `--space-5` | 20px | 区块间距 |
| `--space-6` | 24px | 面板内边距 |
| `--space-7` | 32px | 页面区块 |
| `--space-8` | 40px | 大区块 |
| `--space-9` | 48px | 页面留白 |
| `--space-10` | 64px | 展示型留白 |
| `--radius-sm` | 4px | 标签/筛选项 |
| `--radius-md` | 6px | 按钮/输入 |
| `--radius-lg` | 8px | 纸张面板/生成题卡 |
| `--radius-frame` | 10px | 纸面 frame/登录卡/弹窗 |
| `--shadow-card` | none | 纸张卡片只靠 border，不用阴影 |
| `--shadow-frame` | `0 1px 2px rgba(20,28,45,.05), 0 14px 40px rgba(20,28,45,.05)` | App frame/登录卡 |
| `--shadow-bar` | `0 4px 20px rgba(20,28,45,.09)` | sticky 操作卡 |
| `--shadow-pop` | `0 8px 24px rgba(20,28,45,.12)` | 弹窗/下拉 |

### 4.1 布局 Tokens（Calm）

| Token | 值 | 用途 |
|---|---|---|
| `--layout-frame-max` | 1140px | 桌面 App frame 最大宽度 |
| `--layout-content-max` | 1188px | 文档/内容最大宽度 |
| `--layout-frame-gutter` | 32px | frame 内边距（桌面） |
| `--layout-frame-gutter-mobile` | 16px | frame 内边距（移动） |
| `--layout-topbar-height` | 56px | 桌面 appbar |
| `--layout-mobile-header-height` | 52px | 移动 appbar |
| `--layout-bottom-nav-height` | 60px | 移动底部导航 |
| `--control-height` | 42px | 输入/选择 |

## 5. 断点

| Token | 宽度 | 布局 |
|---|---|---|
| `--bp-sm` | 375px | 单列；移动 appbar + 底部 4 项导航；拍照/相册入口明显 |
| `--bp-md` | 768px | 单列纸面 frame；sticky 操作卡在底栏上方 |
| `--bp-lg` | 1024px | 详情/任务等窄桌面降为单列（详情进度栏置顶） |
| `--bp-xl` | 1440px | 1140px App frame 居中，两侧留白 |

## 6. 组件清单

| 组件 | 用途 | 优先级 | Arco 对应 |
|---|---|---|---|
| `AppShell` | 顶部 appbar + 纸面 frame + 移动底栏 | P0 | Layout（自建 Calm 壳） |
| `BrandMark` | 3×3 点阵品牌标记 | P0 | 自建 SVG |
| `PageHeader` | kicker + 标题 + 描述 + 主操作 | P0 | 自建（简单） |
| `StatCard` | 数字 + 标签 + 趋势 | P1 | Card/Statistic |
| `QuestionCard` | 题干摘要 + 标签 + mono 元数据 | P0 | 自建 article + MarkdownRenderer |
| `QuestionEditor` | 三种题型编辑 + 渲染切换 | P0 | 自建 |
| `EditorToolbar` | LaTeX/编号/表格/插图 | P0 | 自建 |
| `ImageCropper` | 上传前裁剪图片 + 重置原图 | P0 | 自建（canvas/cropper） |
| `RecognizedQuestionList` | 多题提取结果 ① ② ③ … 列表 + 选择 | P0 | 自建 + List/Checkbox |
| `RecognizedQuestionItem` | 单题条目：编辑/删除/含图提示 | P0 | 自建 + Card |
| `TaskCenter` | 5 列纸面任务列表 + 状态 + 重试 | P0 | 自建 list（非 Table） |
| `DraftBar` | 草稿行 + 继续编辑 | P0 | Alert/Card |
| `TagList` | 知识点/自定义标签 | P0 | Tag |
| `FilterBar` | 学科/标签/搜索 | P0 | Select/Input/Tag |
| `AIGenerationPanel` | 阶段进度 + 题卡列表 | P0 | 自建 |
| `StreamStatus` | 阶段文案 + 进度 | P0 | Progress/自建 |
| `MarkdownRenderer` | Markdown + LaTeX | P0 | 自建 |
| `EmptyState` | 无数据 + 主操作 | P0 | Empty |
| `ErrorState` | 错误 + 重试 | P0 | Result |
| `LoadingSkeleton` | 骨架屏 | P0 | Skeleton |
| `ConfirmDialog` | 删除/重新生成确认 | P0 | Modal |
| `PracticeCard` | 题干 + 作答 + 计时 | P0 | Card/Input |
| `ResultFeedback` | 对/错 + 解析 | P0 | Result/Alert |
| `SearchInput` | 搜索 + 防抖 | P0 | Input |
| `Pagination` | 分页 | P0 | Pagination |
| `ImageInput` | 电脑粘贴/拖入/上传 + 手机拍照/相册 | P0 | Upload + 自定义 input |
| `ImagePreview` | 原图预览/删除/重拍 | P0 | Image/自建 |
| `MobileActionSheet` | 拍照 / 相册选择 | P0 | Drawer/ActionSheet |

## 7. 状态矩阵

| 组件 | default | hover | focus | active | disabled | loading | error | empty |
|---|---|---|---|---|---|---|---|---|
| Button | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| Input | ✓ | ✓ | ✓ | — | ✓ | — | ✓ | — |
| Select | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — |
| Card | ✓ | ✓ | — | — | — | ✓ | — | ✓ |
| Tag | ✓ | ✓ | — | — | — | — | — | — |
| Table/List | ✓ | ✓ | — | — | — | ✓ | ✓ | ✓ |
| AI Panel | ✓ | — | — | — | ✓ | ✓ | ✓ | ✓ |
| ImageInput | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ |
| ImageCropper | ✓ | ✓ | ✓ | — | ✓ | — | ✓ | — |
| RecognizedQuestionList | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ |

> 设计稿至少要画：按钮 loading、输入 error、列表 empty、AI error/partial、图片上传/识图失败。

## 8. 可访问性

- 正文对比度 ≥ 4.5:1；大字号 ≥ 3:1。
- 所有表单有 label；错误信息与字段关联。
- 键盘可达：Tab 顺序合理；焦点可见（不要 `outline: none` 不补）。
- 图标按钮有 `aria-label`/tooltip。
- 不要只靠颜色表达对错（加图标/文字）。
- 动效尊重 `prefers-reduced-motion`（可选）。

## 9. Arco 使用规范

- 用官方 Vite 插件按需引入；不要全量引入。
- 主题优先 CSS 变量/官方 token；少用深层选择器覆盖。
- 不自研已有组件（Button/Form/Table/Modal/Upload/Skeleton/Empty）。
- Arco Vue 缺聊天/流式组件：`AIGenerationPanel` 自建，但保持简单（阶段 + 卡片）。
- Arco Upload 没有文档化 `capture` 属性：手机拍照/相册用两个隐藏 `<input type="file" accept="image/*">`，不要硬改 Upload 内部。
- 图表用 ECharts；不要用 Arco 做图表。
- 不引入 Tailwind 与 Arco reset 混用；如必须，严格 scoped。
- 暗色模式不做；tokens 预留即可。

## 10. 交付检查

- [ ] tokens 落到 `frontend/src/styles/tokens.css`。
- [ ] Arco 主题变量映射完成。
- [ ] 组件清单每个都有负责人/状态。
- [ ] 状态矩阵覆盖 P0 组件。
- [ ] 375/768/1366/1920 检查。
- [ ] 与 `calm-academic/index.html` 的 list/create/detail/tasks 四屏逐页对照（结构、间距、字号、状态）。
- [ ] 对比度/焦点/键盘检查。
- [ ] 设计稿与 Arco 组件一致；自定义组件注明原因。
- [ ] 前端能照着建样式文件，不需要再问颜色/间距。
