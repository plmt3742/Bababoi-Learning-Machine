# 31 · 前端 Issue 专项计划（#105 / #107–#113）

> owner: 霹雳马桶 / agent · last_updated: 2026-11-28 · read_when: 处理 2026-11-27 外部评审的前端 issue / 演示前前端收口
> 范围：只覆盖前端可独立交付的部分。后端缺陷 #114（越权软删）、#115（搜索大小写）不在本文，按后端专项处理。
> 基线：当前工作区分支 `feat/mascot-assets`，含未提交的 UI 评审改动；本文行号以当前文件为准，issue 里的行号来自更早的 main，允许有偏移。
> 状态：W0 已实施并验证；W1 的 F-3/F-4/F-5/F-6 已实施并验证；W2 的 F-7/F-8 前端已实施（F-8 后端待 #126），见 §11.2；旧 issue 清理与后端任务派发见 §13。

## 1. 背景与判断

2026-11-27，外部账号 `dbinggo` 集中提交 9 条 issue（#107–#115），其中 7 条与前端有关。这些是评审建议，不是验收契约；做不做、什么时候做，按 PRD 范围与 11.29 演示路径判断。

三条硬约束决定了分批：

1. 演示截止 11.29，今天 11.28。仓库规则明确：演示前不扩大范围，只修缺陷。
2. 前端改动必须走短分支 + PR，合并前等确认；演示前不引入新依赖。
3. 统计「近 7 天」的空白天是后端按 21 号 §2.1 有意省略的契约，缺口应在展示层补，不改接口。

因此：

| 批次 | 内容 | 时间 | 允许范围 |
|---|---|---|---|
| W0 | #110、#113 的缺陷部分 | 11.28 | 只修缺陷，不新增功能 |
| W1 | #111、#112、#108（不含错因标签）、#105 渲染器 | 演示后第一周 | 体验增强；#105 需依赖决策 |
| W2 | #109、#107 | 演示后第二周起 | 功能；需产品确认与后端契约 |

## 2. 事实核验

| Issue | 关键位置 | 核验结论 |
|---|---|---|
| #110 填空题答案不渲染 | `components/question/GeneratedQuestionCard.vue` L16–18（`hasQa`）、L60–69（折叠体） | **确认**。卡片只渲染 `answer_md` / `explanation_md`；同页详情 `QuestionDetailView.vue` L539–544 与练习卡 L227–232 都已按 `blanks` 分空展示。`mocks/index.ts` L183–208 的 104 号题生成模板就是 `blank` + `blanks`，可直接做视觉验证。 |
| #113 趋势图不补空白日期 | 后端 `backend/app/services/stats_service.py` L70–87；前端 `views/StatsView.vue` L28–58、L201–209；`components/stats/TrendChart.vue` L63–102 | **部分确认**。后端只返回有记录的日期是按契约有意为之；前端直接遍历稀疏点，导致近 7 天只出现 1–2 列。另外 `StatsView` 的 `trendRange` 也用稀疏点，会和图表一起缩水。`mocks/index.ts` L495–524 的 mock 同为稀疏。 |
| #111 选择题高亮 + 快捷键 | `components/practice/PracticeQuestionCard.vue` L30（`revealed`）、L105–129（选项）、L179–199（自评）；`views/QuestionCreateView.vue` L243–246（已有 `correctLabelFromAnswer`） | **确认**。练习卡只有 `revealed` 布尔，无对错高亮、无键盘监听；录入页的答案字母解析可直接抽象复用。 |
| #112 LaTeX 快捷栏 + 分栏预览 | `views/QuestionCreateView.vue` L52（`editMode`）、L799–806（编辑/预览切换）、L809–845（编辑区 + 预览）、L812–825（`a-textarea`，`textarea-attrs` 已设 `id="content-md"`） | **确认**。当前是单栏切换，无公式快捷插入；文件已 1576 行，拆分属于重构，不能和功能混在一个 PR。 |
| #108 三阶提示 + 错因标签 | `views/PracticeView.vue` L127（已加载 `includeGenerated` 详情）、L429–438（传参）；`components/practice/PracticeQuestionCard.vue` L156–245（单一答案面板） | **确认可行（仅提示部分）**。`PracticeView` 已持有原题 `analysis`，可下传做 0–3 阶提示，零额外 LLM 成本。错因微标签要落库（`practice_records` 新字段 + 迁移），属于后端契约变更，本计划不实现。 |
| #109 打印 / 导出 PDF | `router/index.ts`（无打印路由）、`styles/global.css`（无 `@media print`）、`components/common/MarkdownRenderer.vue`（KaTeX 渲染已就绪） | **确认未实现**。可新增独立打印路由 + 打印样式，但批量取数需要产品确认范围（当前列表接口不返回生成题）。 |
| #107 今日待复习队列 | `views/PracticeView.vue` L338–375（无 id 时的引导态）、`views/HomeView.vue`；后端无 `/practice/due` | **确认未实现**。是这批里唯一需要新增 API 的项，必须先在 `05-architecture.md` 定义契约，再由后端实现，前端 mock 可先行。 |
| #105 Mermaid + 3 组字段 | `components/common/MarkdownRenderer.vue`；全仓无 `mermaid` 依赖；issue 指向的 `docs/agent/28-ui-v05-mermaid-handoff-20261122.md` 在当前工作区不存在 | **部分确认**。前端渲染器可以先做，但需要新增依赖与安全方案（ADR 级决策）；3 组展示字段依赖后端。issue 里引用的 28 号文档缺失，需要先补回或在 issue 里更正链接。 |

## 3. 分级与批次

| 批次 | Issue | 类型 | 演示影响 | 预估 |
|---|---|---|---|---|
| W0 | #110 | 缺陷 | 填空题相似题答案不可见 | 0.5 人时 |
| W0 | #113（补日） | 展示缺陷 | 趋势图看起来不像「近 7 天」 | 1.5 人时（含单测） |
| W1 | #111 | 体验增强 | 演示加分，非阻断 | 4–6 人时 |
| W1 | #112 | 编辑效率 | 非阻断 | 6–8 人时 |
| W1 | #108（仅提示） | 体验增强 | 非阻断 | 4 人时 |
| W1 | #105（渲染器） | 契约 v0.5 | 非阻断，需要依赖决策 | 6–10 人时 |
| W2 | #109 | 新功能（PRD P1） | 演示高价值，但需产品确认 | 6–8 人时 |
| W2 | #107 | 新功能 + 新接口 | 非阻断，依赖后端 | 12+ 人时 |
| — | #113 悬浮提示 | 体验增强 | 非阻断 | 2 人时 |

## 4. W0（演示前，已实施）

PR 建议：一个分支 `fix/frontend-issue-w0`，一个 PR 覆盖 F-1/F-2；改动文件只有 4 个（2 个源码 + 2 个测试/视图），便于回滚。

### F-1 · #110 相似题卡片渲染填空题 `blanks`

- 目标：填空题相似题展开「答案与解析」后，能看到每一空的答案。
- 改动：
  - `GeneratedQuestionCard.vue`：新增 `blanks` computed；`hasQa` 纳入 `blanks.length > 0`；折叠体内在「答案」之后、「解析」之前插入分空列表，标签用「第 N 空」。
  - 复用现有 `.gen-qa` 布局与 `MarkdownRenderer`，只补 `.gen-blanks*` 两条布局样式，不引入新 token。
- 测试：组件测试框架未安装（无 `@vue/test-utils`），不新增依赖；用 mock 104 号题的生成模板做浏览器验证。
- 验收：
  - 104 号题详情页任一生成题卡展开后显示「填空答案 / 第 1 空 / 公式」。
  - 只有 `answer_md` 的卡片渲染不变；三者都为空时仍显示「暂无答案与解析」。
- 风险：低。标签选择与详情页保持「分空」语义一致，不改数据结构。

### F-2 · #113 近 7 天趋势补齐空白日期

- 目标：无论近 7 天练了 1 天还是 7 天，横轴恒为连续 7 列，未练习日为 0；同时让标题右侧的日期范围与图表一致。
- 方案：在展示层归一化，而不是改后端契约，也不把归一化塞进 `TrendChart`：
  - `utils/stats.ts` 新增 `fillRecentSevenDays(points, now = new Date())`：以 **Asia/Shanghai** 的「今天」为锚点，向前生成 7 个日期键；按日期合并已有数据，缺失日补 `{practice_count: 0, correct_count: 0}`；不改原数组、忽略窗口外数据。
  - 为什么以上海时区为锚：后端 `_recent_trend` 用 `CHINA_TZ` 分桶，mock 也用 `shanghaiDayKey`；用浏览器本地时区会在跨日边界产生与后端不同的「今天」。实现用 `Intl.DateTimeFormat(..., { timeZone: 'Asia/Shanghai' })` + `formatToParts`，不硬编码 `+8`。
  - `StatsView.vue`：新增 `trendPoints = computed(() => fillRecentSevenDays(overview?.recent_trend ?? []))`；`week`、`trendRange`、`TrendChart :points` 全部改用 `trendPoints`。`TrendChart` 保持纯展示组件，不感知补日逻辑。
- 测试：`frontend/tests/stats.test.ts` 新增 3 条：7 天连续且升序、缺失日补 0、窗口外数据被忽略且入参不被修改。
- 验收：
  - `/stats` 只有 2 天练习记录时仍显示 7 根柱、7 个日期；无记录日为 0 且高度 2px。
  - 标题右侧范围始终是「今天-6」到「今天」。
  - 空数据时仍进入空状态，不报错。
- 风险：时区口径。若未来后端改为按用户时区分桶，本函数需同步；已在函数注释写明假设。
- 未做：悬浮 tooltip 改为自绘浮层。演示前不改，避免引入交互回归；放入 W2。

## 5. W1（演示后第一周）

### F-3 · #111 练习页选择题高亮 + 桌面快捷键

- 目标：展开答案后一眼看出「正确答案 / 我选错了」；桌面端不离开键盘完成一轮练习。
- 数据层：
  - 在 `utils/practice.ts` 新增纯函数 `extractChoiceAnswerLabel(answerMd)`：兼容 `选 A`、`答案：A`、裸 `A`、前后中文标点；只取 A–F；返回大写字母或空串。
  - 单测覆盖前缀、全角冒号、无匹配、多字母干扰（如「AB 两点」不误判）。
- 交互层（`PracticeQuestionCard.vue`）：
  - `expectedChoiceLabel` computed，仅 `effectiveType === 'choice'` 时计算。
  - `revealed` 后：正确项加 `option--correct`（`--color-success-soft` / `--color-success-border`），用户选错的项加 `option--wrong`（`--color-danger-soft` / `--color-danger-border`）；仍保留手动「会 / 不会」。
  - 无障碍：选项内补 `sr-only` 文案（「正确答案」/「你的选择」），不只靠颜色。
  - 键盘：`onMounted` 注册 `window.keydown`，`onBeforeUnmount` 移除；忽略 `input` / `textarea` / `select` / `contentEditable` / 带修饰键 / 已 `defaultPrevented` 的事件；焦点在按钮上时不处理 Space，避免与原生点击双触发；A–F 选项、Space 展开、1=不会、2=会；`submitting` 时禁用评分快捷键。
  - 桌面显示 `<kbd>` 提示，`<768px` 隐藏；移动端行为不变。
- 验收：鼠标与键盘两条路径都能完成 3 题；无控制台报错；焦点顺序不破；`prefers-reduced-motion` 不受影响。
- 风险：键盘监听与浏览器快捷键、输入法组合键冲突；必须在真实浏览器手工验证。

### F-4 · #112 公式快捷插入栏 + 宽屏分栏预览

- 目标：录入理科题干时不用反复切「编辑/预览」，常用 LaTeX 一键插入且光标落在 `{}` 内。
- 拆分：
  - 新组件 `components/question/editor/LatexToolbar.vue`：只放 8–10 个模板（行内公式、分式、根号、积分、极限、求和、偏导、矩阵、块级公式），通过 `emit('insert', { template, caretOffset })` 交给父组件，不直接操作 DOM。
  - `utils/questionEditor.ts`（或现有 utils）新增纯函数 `insertAtSelection(value, start, end, template, caretOffset)`，返回新值与光标位置；单测覆盖选区替换、末尾插入、光标越界。
  - 父组件通过 `textarea-attrs` 已有的 `id="content-md"` 定位原生 textarea，`nextTick` 后 `focus()` + `setSelectionRange`；若取不到元素则只更新值，不抛错。
  - `editMode` 布尔升级为 `viewMode: 'edit' | 'split' | 'preview'`；`≥1200px` 显示「分栏」，窄屏按钮隐藏；窗口缩到窄屏时若当前是 `split`，回退到 `edit`（`matchMedia` 监听并在卸载时移除）。
- 不做：拆分 1576 行的 `QuestionCreateView`。拆草稿状态条/冲突面板是独立重构，单独开 PR，避免功能 PR 不可审。
- 验收：三种题型录入均可用；插入后撤销（Ctrl+Z）行为正常；分栏在 1440px 正常、1024px 不出现；KaTeX 预览无重复渲染。
- 风险：Arco `a-textarea` 内部结构变化导致取不到原生节点；实现前先在浏览器确认 DOM。输入法组合期间不触发插入。

### F-5 · #108 三阶渐进提示（不含错因标签）

- 目标：把「查看答案」拆成 思路 → 答案 → 解析 三阶，减少直接看完整答案的挫败感。
- 数据：`PracticeView` 已有 `question.analysis`（L127），只加一个 prop 下传；不改接口。
- 交互（`PracticeQuestionCard.vue`）：
  - `revealStage: 0 | 1 | 2 | 3`，替换单一 `revealed`；`watch(question.id)` 重置。
  - 阶段 1：`analysis.knowledge_points` + `analysis.solution_summary`；阶段 2：`answer_md` + `blanks`；阶段 3：`explanation_md`。
  - 按钮文案：`看思路提示` → `看参考答案` → `看完整解析` → `收起`；保留「直接看完整解析」小字快捷入口。没有 `analysis` 时跳过阶段 1，不显示空面板。
  - 评分可用性仍以「是否已展开参考答案」为准，保持现有 `gradeAvailable` 语义。
- 验收：解析缺失、答案缺失、分析缺失三种组合都能正常降级；评分快捷键（W1 的 F-3）与新阶段状态不冲突。
- 不做：错因微标签。需要 `practice_records.error_reason` 字段 + 迁移 + 统计聚合，单独立后端 issue，前端等契约。

### F-6 · #105 Mermaid 渲染器（前端先行）

- 前置：依赖与安全决策。`mermaid` 体积大，必须动态 `import()`，只在检测到 ```mermaid 围栏时加载；引入前补一条 ADR（或在现有 ADR 中追加），确认包体积与许可。
- 方案：
  - `MarkdownRenderer.vue` 的 fence 渲染：识别 `mermaid` 语言，输出占位容器（保留原始源码作为 `pre` 兜底），渲染完成后替换为 SVG。
  - `mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' })`；渲染结果再过一次 DOMPurify 才插入；失败时保留源码 + 人话提示，不影响正文。
  - 序列化并发：同一组件内多个图顺序渲染；组件卸载后丢弃迟到结果。
- 验收：非法图、空图、超长图（>2000 字符）、外链/click 指令都被阻断并显示源码；答案/解析/解题摘要三个入口都能渲染。
- 依赖：issue #105 的 3 组展示字段仍由后端补；文档 28 号缺失需先修复链接。

## 6. W2（功能，需确认）

### F-7 · #109 错题巩固卷打印 / 导出 PDF

- 产品确认点：是否进演示；若进，冻结时间必须早于 11.28 18:00，否则只做演示后备选。
- 范围（Phase 1）：
  - 新路由 `/questions/print`（`requiresAuth`，不进导航），从列表页带当前筛选 query 进入。
  - 配置条：包含原题 / 包含相似题 / 答案统一附卷尾；`window.print()`。
  - 取数：先按筛选拉列表，再对前 N 道（建议 20，硬上限 50）并发 3 拉详情 `include=generated`；失败单题降级为占位，不阻断整卷。
  - 打印样式：隐藏 appbar / 底部导航 / 配置条；`@page` 边距；题目 `break-inside: avoid`；答案区 `break-before: page`；KaTeX 字体不裁切。
- 后续（Phase 2）：后端 `GET /questions/export` 一次返回，避免 N+1；需在 05 文档定义契约。
- 验收：Chrome 打印预览无截断、无空白页；iPad 另存 PDF 可读；20 题耗时与请求数符合预期。
- 风险：批量取数放大请求；打印引擎差异（Chrome/Safari）；公式跨页。
- 状态（2026-11-28）：已实现并验证。`/questions/print` + 列表入口 + 配置条 + 打印 CSS；1 道原题 + 3 道相似题导出为 2 页 PDF：第 1 页题目、第 2 页答案解析，appbar/配置条不进入打印、无截断。

### F-8 · #107 今日待复习队列

- 前置：后端契约。建议 `GET /api/v1/practice/due?limit=6&subject=`，返回扁平条目（生成题 + 父题摘要 + 到期原因），排序规则写入 `05-architecture.md`：未练过优先；`unmastered` 1 天、`reviewing` 3 天、`mastered` 7 天。
- 前端：
  - `PracticeView` 无 id 时先请求 due；有到期题显示「今日待复习 X 题」卡片与「开始混刷」，无到期题回退现有三步引导。
  - 混刷复用 `PracticeQuestionCard`，结算按 `parent_question_id` 分组更新掌握度（顺序 `updateQuestion`，失败可重试）。
  - `HomeView` 增加轻量入口（数字 + 跳转）。
- 验收：到期规则与后端一致；跨题混刷不串题；掌握度按父题正确聚合；空状态与加载失败可恢复。
- 风险：接口未定稿前不合并；mock 与真接口必须同形。
- 状态（2026-11-28）：契约已写入 `05-architecture.md` §6.5；后端任务已拆到 #126 并派给 @zhouyuliang0606；前端 mock `/practice/due`、今日待复习卡、混刷、Home 入口已实现并验证。真接口未上线前只走 mock，不把 mock 当后端完成。

## 7. 工程约束与验证矩阵

- 依赖：W0/W1 不新增运行时依赖；#105 的 `mermaid` 例外，先决策后引入，动态加载。
- 样式：只用 `tokens.css` 变量；不改 Arco 主题；移动端断点沿用 767px/600px。
- 无障碍：颜色不是唯一信息；键盘可达；`aria-live` / `aria-expanded` 保持；`prefers-reduced-motion` 不破坏。
- 契约：W0/W1 不改 API；#107 必须先改 05 文档 + OpenAPI；#105 只加字段不加 schema。
- 验证命令：

```bash
cd frontend
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

- 手工冒烟清单：
  - `/questions/104`：展开填空题生成卡（W0）；选择/键盘（W1）。
  - `/stats`：稀疏数据 7 列（W0）；375/768/1440 三档宽度。
  - `/questions/new`：公式插入、分栏、窄屏回退（W1）。
  - `/practice/104`：三阶提示、评分（W1）。
  - 打印预览（W2）。
- 证据留存：W0 记录命令结果与页面截图路径；W1/W2 每个 PR 附 1440px + 375px 截图。

## 8. 排期与 PR 拆分

| 时间 | 动作 |
|---|---|
| 11.28 | W0 分支 + PR；演示冻结后不再合前端功能 |
| 11.29 | 只做演示保障与回滚预案 |
| 12.01–12.05 | W1：F-3 (#111) → F-4 (#112) → F-5 (#108) → F-6 (#105) |
| 12.08–12.12 | W2：F-7 (#109) 与 F-8 (#107)，按后端就绪度排序 |

PR 拆分：W0 一个；W1 每项一个；#112 的组件拆分单独 PR；#107 后端契约、前端 mock、前端接线分三个 PR。

## 9. 风险与回滚

| 风险 | 影响 | 缓解 |
|---|---|---|
| 当前工作区有大量未提交改动 | W0 diff 与他人 WIP 混在一起 | 只改 4 个文件；评审用 `git diff -- <路径>`；不提交无关文件 |
| 时区口径不一致 | 补日窗口与后端差一天 | 以 Asia/Shanghai 为锚；函数注释写明；后续若改按用户时区需同步 |
| #111 键盘与原生控件冲突 | 双触发/误评分 | 忽略可编辑元素、按钮上的 Space、修饰键、`defaultPrevented` |
| #112 取不到 Arco 内部 textarea | 插入无效 | 先浏览器确认 DOM；取不到时只更新值，不抛错 |
| #105 Mermaid XSS / 体积 | 安全与首屏性能 | `securityLevel: 'strict'` + DOMPurify + 动态 import + 失败兜底 |
| #109 批量取数放大请求 | 后端压力 | 上限 20/50 + 并发 3；长期改 export 接口 |
| #107 契约漂移 | 前后端不一致 | 先写 05 文档与 OpenAPI，再实现；mock 字段同形 |

回滚：W0 单 PR 可整体 revert；W1/W2 每项独立 PR，路由级功能（打印、混刷）可通过移除入口快速回退。

## 10. 待拍板

1. #109 是否进 11.29 演示。建议：不进；演示后做，避免最后一天引入新路由与批量取数。
2. #105 是否接受 `mermaid` 依赖（动态加载后仍会增加可观的 chunk）。**已确认（2026-11-28）**：接受，按 ADR-011 只在检测到围栏时动态加载；主入口体积不变。
3. #107 后端排期与 `GET /practice/due` 口径。**已确认（2026-11-28）**：契约写入 05 §6.5，后端任务 #126 已派给 @zhouyuliang0606；前端 mock-first。
4. #108 错因微标签是否立项（需 `practice_records` 新字段与迁移）。**已立项（2026-11-28）**：后端任务 #127，前端字段上线后再接，不提交假数据。
5. issue 里引用的 `docs/agent/28-ui-v05-mermaid-handoff-20261122.md` 在当前工作区缺失。**已在 #105 评论中请后端确认分支或更正链接。**

## 11. W0 验收记录

| 检查 | 结果 |
|---|---|
| #110 代码路径 | `GeneratedQuestionCard.vue` 新增 `blanks` computed，`hasQa` 纳入 `blanks.length`，折叠体在答案与解析之间渲染「填空答案 / 第 N 空」。浏览器实测：/questions/104 生成 2 张填空相似题，展开后 `.gen-blanks__item` 命中 1 条（文本「第 1 空 5」），`gen-qa-empty` 未出现。截图：`C:\Users\ADMINI~1\AppData\Local\Temp\opencode\w0-question-blanks.png` |
| #113 代码路径 | `utils/stats.ts` 新增 `fillRecentSevenDays`（Asia/Shanghai 锚点）；`StatsView.vue` 的 `week`、`trendRange` 与 `TrendChart :points` 改用 `trendPoints`。浏览器实测：今日 2 次练习、其余 6 天空白时，桌面与 375px 宽度均渲染 7 列（计数 `0,0,0,0,0,0,2`，空白柱高 2px），范围显示 `11-22 — 11-28`。截图：`w0-stats-desktop.png`、`w0-stats-mobile.png`（同目录） |
| `pnpm lint` | 通过，0 warning |
| `pnpm typecheck` | 通过 |
| `pnpm test` | 通过：11 个测试文件 / 58 个用例（新增 3 条 `fillRecentSevenDays` 用例） |
| `pnpm build` | 通过：1407 modules transformed，4.38s |
| 浏览器验证 | 无页面错误；console 仅有 Vite 连接日志。预览地址：`http://127.0.0.1:5199/`（mock 模式，本地临时服务器） |

### 11.1 W1 执行记录（F-3 / F-4 / F-5）

| 项 | 结果 |
|---|---|
| F-3 #111 解析函数 | `utils/practice.ts` 新增 `extractChoiceAnswerLabel`；新增 `tests/practice.test.ts` 覆盖 `选 A` / `答案：B` / `**C**` / `小写 d.` / `AB 两点` 不误判。 |
| F-3 #111 交互 | 选项在展开后加 `option--correct` / `option--wrong`，配 `sr-only` 文案；键盘 A–F 选择、Space 逐阶展开、1/2 自评，忽略输入框、按钮上的 Space、修饰键与 `defaultPrevented`；桌面显示 `<kbd>` 提示，移动端隐藏。实测 103 号题：选 B 后展开，A 正确绿、B 所选红；Space 0→1→2→3；按 2 记为答对并进入第 2 题。无头浏览器 CLI 的 `press` 未把按键送达页面，键盘路径改用向 `window` 派发同构 `KeyboardEvent` 验证，走的是同一个监听器。 |
| F-5 #108 三阶提示 | `PracticeView` 下传原题 `analysis`；卡片改为 `revealStage` 0–3：思路提示（知识点 + `solution_summary`，KaTeX 渲染）→ 答案 → 解析；`直接看完整解析` 仅在阶段 0/1 出现；评分仍要求答案已展开。实测 103：阶段 1 出现知识点与公式，阶段 2 出现答案且评分启用。 |
| F-4 #112 公式栏 | 新增 `components/question/editor/LatexToolbar.vue`（8 个模板，emit 插入参数）；`utils/questionEditor.ts` 新增 `insertLatexTemplate` 并补单测。实测在光标处插入 `\frac{}{}`，光标落在 `{}` 内（19→25），预览实时更新。 |
| F-4 #112 分栏 | `editMode` 升级为 `viewMode: edit / split / preview`；`≥1200px` 显示「分栏」，1440px 实测两列（334px + 334px）；缩到 1024px 按钮消失并自动回退 `edit`；375px 工具栏两行换行、无横向溢出。截图：`w1-editor-split.png`、`w1-editor-mobile-toolbar.png`。 |
| `pnpm lint` | 通过，0 warning |
| `pnpm typecheck` | 通过 |
| `pnpm test` | 通过：13 个测试文件 / 64 个用例（新增 `practice.test.ts` 2 条、`insertLatexTemplate` 1 条、`splitMermaidFences` 3 条） |
| `pnpm build` | 通过：2954 modules，主入口 128.65 kB；Mermaid 懒加载 chunk 见 F-6 行。pnpm 9.15.9 对当前 lockfile 的 `--frozen-lockfile` 校验通过（CI 使用 pnpm 9）。 |
| 浏览器验证 | 无页面错误。截图：`w1-practice-highlight.png`、`w1-editor-split.png`、`w1-editor-mobile.png`、`w1-editor-mobile-toolbar.png`、`w1-mermaid-preview.png`、`w1-mermaid-mobile.png`（临时目录 `C:\Users\ADMINI~1\AppData\Local\Temp\opencode\`） |
| F-6 #105 | 已实施（依赖决策：接受，ADR-011）。`utils/mermaid.ts` 切分围栏并补 3 条单测；`MermaidDiagram.vue` 动态 `import('mermaid')`、`securityLevel: strict`、`htmlLabels: false`、DOMPurify 清洗、失败保留源码并清理临时错误节点；模块级唯一 id 修复多图冲突。实测：两个图同时渲染，标签正确（错题/AI 分析/生成相似题/练习；Alice/Bob），无 `<script>` / `onerror` / `javascript:`，非法源码进入 error 态且 body 无残留节点。构建后主入口仍 128.65 kB；mermaid 独立 lazy chunk（core 86.10 kB / gzip 29.42 kB，parser 16.44 kB / gzip 3.92 kB），图示类型 chunk 按需加载；构建出现一条 >500 kB 警告（elk 1.5 MB / cytoscape 441.7 kB 懒加载 chunk），未用 `chunkSizeWarningLimit` 掩盖。截图：`w1-mermaid-preview.png`。 |

PR 拆分修正：F-3（#111）与 F-5（#108）都要改 `PracticeQuestionCard.vue`，实际按一个「练习页增强」PR 提交；F-4（#112）独立一个 PR；F-6（#105）独立一个 PR（依赖 + ADR-011 + 渲染器）。这些改动都建立在当前工作区已有的 UI 评审 WIP 之上，提交前需要按文件核对差异。

### 11.2 W2 与复检记录（2026-11-28）

| 项 | 结果 |
|---|---|
| W0/W1 复检 | 复跑 #110/#113/#111/#112/#108/#105 的代码与浏览器路径，未发现回退；详情页普通 KaTeX、任务中心 `task-row__question` attrs 透传均正常。 |
| #113 悬浮提示 | `TrendChart` 去掉原生 `title`，改为自绘 tooltip：列可聚焦、`:hover` / `:focus-visible` 显示日期/练习/答对/正确率；实测焦点后 opacity 1、文本正确。 |
| #111 快捷键复检 | 把保护条件抽成 `resolvePracticeShortcut` 纯函数，补 3 组单测（A–F、Space、1/2、可编辑/按钮/修饰键）；组件监听器只剩分发。 |
| F-8 #107 契约 | `05-architecture.md` §6.5 已写 `GET /practice/due` 形状/规则；后端任务 #126 已派给 @zhouyuliang0606。 |
| F-8 #107 前端 | mock `/practice/due`、今日待复习卡、混刷（按父题分组同步掌握度）、Home 入口已实现；实测 2 道到期混刷完成并同步 2 道错题；混刷父题 `analysis` 现按需加载，三阶提示可用。真接口上线前只走 mock。 |
| #108 错因标签 | 后端字段/契约已拆到 #127 并派给后端；前端不提交假数据，等接口后接。 |
| #105 缺失文档 | 已在 issue #105 评论请后端确认 `28-ui-v05-mermaid-handoff` 所在分支或更正链接。 |
| 根 README | 已把 M0 阶段、FE-001~024、前端脚手架待办等过时信息更新为 2026-11-28 现状。 |
| F-7 #109 打印 | `/questions/print` + 列表「导出打印卷」入口（实测带当前 `subject` 筛选）+ 原题/相似题/答案位置三个开关；`utils/printWorksheet.ts` 上限 20、详情并发 3、单题失败降级；打印 CSS 隐藏 appbar/配置条、`@page A4`、题目与答案块避免腰斩。实测 1 原题 + 3 相似题导出 2 页 PDF：第 1 页题目、第 2 页答案解析，无 app 导航、无截断；375px 无横向溢出。截图/PDF：`w2-print.png`、`w2-print-mobile.png`、`w2-print.pdf`、`w2-print-p1.png`、`w2-print-p2.png`。 |
| #105 前端可先行部分 | `StatsOverview` 增加可选 `total_duration_seconds` / `average_duration_seconds`，`StatsView` 有数据时显示「累计练习 / 平均每题」；`GeneratedQuestion` 增加可选 `practice_count` / `correct_count` / `last_practiced_at`，`GeneratedQuestionCard` 显示练习状态。字段缺失时完全隐藏，不对真后端造假数据。mock 实测：`07:05 / 03:33`；三张卡分别为 `1/1`、`1/0`、`0/0`。知识点页与 `mastery_history` 仍缺（当前无该页面/路由，需产品确认范围）。 |
| 当前测试 | 14 个测试文件 / 75 个用例通过（含 due reason、快捷键纯函数、print 工具）。 |
| 最终验证 | `pnpm lint` 0 warning；`pnpm typecheck` 通过；`pnpm test` 14 / 75 通过；`pnpm build` 通过（2961 modules；保留 Mermaid 可选 chunk 的 >500 kB 提示）。 |

## 12. 变更记录

| 日期 | 变更 | 变更人 |
|---|---|---|
| 2026-11-28 | 新建：前端 issue 专项计划，W0/W1/W2 分批与验收口径 | 霹雳马桶 / agent |
| 2026-11-28 | W1 开工：完成 #111（高亮 + 快捷键）、#108（三阶提示）、#112（公式栏 + 分栏）；#105 等待依赖决策 | 霹雳马桶 / agent |
| 2026-11-28 | 接受 Mermaid 依赖：完成 #105 前端渲染器，新增 ADR-011；W1 全部收口 | 霹雳马桶 / agent |
| 2026-11-28 | W2 开工：完成 #109 打印卷与 #107 前端 mock/混刷；补 #113 tooltip、快捷键纯函数测试、README；后端任务 #114/#115/#126/#127 已派发 | 霹雳马桶 / agent |
| 2026-11-28 | 旧 issue 审计收口：#45/#46/#32/#13/#11/#48 已带证据关闭；#47 保留待一步回退决策；#128 跟踪 BYOK 边界 | 霹雳马桶 / agent |

## 13. 后端派发与旧 Issue 处理（2026-11-28）

### 13.1 已派给 @zhouyuliang0606

| Issue / 任务 | 内容 | 状态 |
|---|---|---|
| #114 | 整组生题先软删后校验归属（跨用户数据破坏） | 已 assign + 复检评论；P0 |
| #115 | 搜索查询串未 lower + `/static` 开关 + README | 已 assign + 复检评论；P0 |
| #105 | 前端渲染器已完成；后端剩 `mermaid_v1` prompt + 3 组字段 | 已评论；待后端 |
| #126 | `GET /practice/due` 今日待复习契约与实现 | 新建并 assign；前端 mock-first |
| #127 | `practice_records.error_reason` 错因微标签字段 | 新建并 assign；前端等字段 |
| #128 | BYOK 边界：`AI_INVALID_KEY` + GET 503 口径 | 新建并 assign；来自 #32 审计 |

### 13.2 旧 Issue 审计结果

| Issue | 结论 | 动作 |
|---|---|---|
| #45 BE-013 统计 | 已实现：rich shape/稀疏 7 天/掌握度/薄弱点/updated_at，测试覆盖 | 评论证据 + 关闭 |
| #46 BE-018 草稿 | 已实现：GET/PUT/DELETE、256KB、409、隔离，测试覆盖 | 评论证据 + 关闭 |
| #32 BYOK | 核心已实现：加密/mask/白名单/隔离/503(PUT)/回退；两个非阻断边界（无 `AI_INVALID_KEY`；GET 不 503）已拆到 #128 | 评论 + 关闭 |
| #13 图片录入 v2 | 已实现：上传 + from-image 多题、无 bbox；前端裁剪 + 逐条确认完成；旧提示词/3 道上限已被后续口径取代 | 评论 + 关闭 |
| #11 BE follow-up | 主体完成（健康检查/错误信封/JWT/代理/限流/pymysql）；本轮补 README 与 OPS-005 状态；MySQL 实跑归 BE-011，format 暂不进 CI | 评论 + 关闭 |
| #48 seed/OpenAPI/staging | 三项均完成；04-todos OPS-005 已标 DONE、根 README 已更新；口令注入与 HTTP staging 为已记录取舍 | 评论 + 关闭 |
| #47 BE-024 两步识图 | 核心/缓存/force_refresh/冷却均完成；原验收要求的一步回退开关缺失 | 保持 open，已评论请后端补开关或明确取消 |

本轮收口：前端可独立完成的需求已全部落地并验证；剩余为后端实现（#105 后半 / #114 / #115 / #126 / #127 / #128 / #47 回退）与当前工作区改动的评审/提交。
