# ADR-011: 解析与答案中的 Mermaid 图形渲染

- 状态：Accepted
- 日期：2026-11-28
- 决策人：霹雳马桶
- 相关任务：#105（v0.5 对接）、前端专项计划 F-6
- 相关文档：`docs/agent/31-frontend-issue-plan.md`、`docs/product/10-design-draft-learning-desk.md`（v0.5）

## 1. 背景

v0.5 设计稿在 `answer_md`、`explanation_md`、`analysis.solution_summary` 等 Markdown 字段里加入 ```mermaid 关系图；#105 明确不新增 schema，后端原样保留围栏，由前端识别并渲染。需要决定是否引入运行时依赖、是否影响主包、以及如何控制恶意 Mermaid 源码的风险。

## 2. 决策

- 引入 `mermaid@12.3.0`（精确版本），**只在 Markdown 中出现 ```mermaid 围栏时动态 `import('mermaid')`**，主包不加载。
- `MarkdownRenderer` 把内容切成 markdown / mermaid 段：markdown 段继续走现有 KaTeX + DOMPurify 管线；mermaid 段交给 `MermaidDiagram.vue`。
- 渲染配置：`startOnLoad: false`、`securityLevel: 'strict'`、`theme: 'neutral'`、根级 `htmlLabels: false`（避免 `foreignObject` / HTML 标签注入面）、`useMaxWidth: true`。
- 渲染结果先用 DOMPurify（SVG profile，允许 `<style>`）清洗再插入；失败时保留源码 + `role="status"` 提示，不影响正文。
- 每个图使用模块级递增 id，避免多图 id 冲突；实例内用序号丢弃迟到结果；组件卸载后不再写入 DOM。
- 后端契约不变：围栏原样往返；图坏了不影响分析/答案正文。

## 3. 后果

- 主入口体积不变：构建产物 `index` 仍约 128.7 kB；Mermaid 被拆成独立 lazy chunk。
- 首次含图渲染需要异步加载：`mermaid.core` 86.10 kB（gzip 29.42 kB）+ `mermaid-parser.core` 16.44 kB（gzip 3.92 kB），再按图类型加载对应 diagram chunk（如 `sequenceDiagram` 117.7 kB、`cytoscape` 441.7 kB、`elk` 1.5 MB）。只有用到该类图时才下载，流程图/时序图不加载 `elk`。
- 构建会出现 Vite 的「chunk > 500 kB」提示，来源是 Mermaid 的可选 `elk` / `cytoscape` 懒加载 chunk；接受该提示，不用 `chunkSizeWarningLimit` 掩盖。
- 渲染前显示源码，避免空白；非法源码进入 error 态并清理 Mermaid 留在 `body` 的临时错误节点。
- strict + DOMPurify 禁用 `click` / 外链 / HTML 标签；复杂交互图不支持，符合 #105 的范围。
- `htmlLabels: false` 让标签走 SVG `<text>`，牺牲少量排版自由度换取更小的 XSS 面。
- 打印/导出 PDF 时图有 `break-inside: avoid`，不会被腰斩。

## 4. 备选

| 方案 | 不选原因 |
|---|---|
| 服务端渲染 SVG | 需要无头浏览器或 Node 渲染服务，增加部署复杂度；#105 明确不新增接口 |
| iframe sandbox | 隔离更强，但布局、尺寸、打印与主题继承复杂，且本需求不需要交互 |
| 静态图片 | 失去文本可编辑能力与源码兜底 |
| 全量打包 Mermaid | 主包显著增大；绝大多数页面没有关系图 |

## 5. 链接

- Issue #105：`[Design] v0.5 对接：解析/答案支持 Mermaid + 3 组字段`
- 前端实现：`frontend/src/components/common/MermaidDiagram.vue`、`frontend/src/utils/mermaid.ts`
- 专项计划：`docs/agent/31-frontend-issue-plan.md` §5 F-6、§11.1
