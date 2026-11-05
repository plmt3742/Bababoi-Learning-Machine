# frontend/src/components/common

放**与业务无关、可复用**的 UI 组件。

## 什么放这里

| 组件               | 用途                         | 关键状态        |
| ------------------ | ---------------------------- | --------------- |
| `PageHeader`       | 页面标题 + 描述 + 主操作     | 默认            |
| `EmptyState`       | 无数据 + 主操作              | 空              |
| `ErrorState`       | 错误 + 重试                  | error           |
| `LoadingSkeleton`  | 列表/详情/题卡骨架           | loading         |
| `ConfirmDialog`    | 删除/重新生成确认            | 默认            |
| `TagList`          | 标签展示/溢出 +N             | 默认/溢出       |
| `StatCard`         | 数字 + 标签 + 趋势           | 默认/空/loading |
| `SearchInput`      | 搜索 + 防抖                  | 默认/loading    |
| `Pagination`       | 分页                         | 默认/禁用       |
| `MarkdownRenderer` | Markdown + KaTeX + DOMPurify | 默认/超长       |
| `ResultFeedback`   | 对/错 + 解析                 | 正确/错误       |

## 什么不放这里

- 页面级数据请求 → `views/` 或 `composables/`
- 错题业务组件 → `components/question/`
- AI 生成面板 → `components/ai/`
- 图片上传/相机入口 → `components/upload/`
- 布局壳 → `components/layout/`

## 规则

1. `common/` 不 import `stores/`、`api/`、`router/`，只收 props / emit events。
2. 所有异步组件至少支持 loading / empty / error / success；AI 组件加 partial。
3. 优先用 Arco 已有组件；只有 Arco 没有且演示必需才自研。
4. 样式用 `styles/tokens.css` 的变量，不写死颜色/间距。
5. 可访问性：label、键盘、焦点、对比度。
6. 组件名 PascalCase，文件名与组件名一致。

## 领域组件

| 目录                   | 组件                                                          |
| ---------------------- | ------------------------------------------------------------- |
| `components/layout/`   | `AppShell`、`Sidebar`、`TopBar`                               |
| `components/question/` | `QuestionCard`、`QuestionForm`、`QuestionDetail`              |
| `components/ai/`       | `AIGenerationPanel`、`StageProgress`、`GeneratedQuestionCard` |
| `components/upload/`   | `ImageInput`、`ImagePreview`、`MobileImagePicker`             |

## 共享逻辑

| composable       | 用途                              |
| ---------------- | --------------------------------- |
| `useAuth`        | 登录态、token、401 跳转           |
| `useSSE`         | 阶段级 SSE、AbortController、重试 |
| `useImagePicker` | 电脑上传 / 手机拍照 / 相册        |
| `usePagination`  | 列表分页/筛选                     |
| `useAsyncState`  | loading/error/data 三态           |

> 当前是目录骨架，组件在 FE-001 / FE-012 里开始实现。
