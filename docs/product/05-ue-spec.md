# 05 · UE 稿与交互地图

> 目标：把“要点来点去才看得懂”的前端 Demo，整理成产品/研发/测试能一起看的 UE 稿。
> 使用时机：**前端 Demo 跑起来之后**（建议 11.21 后），不是现在。

## 1. 它解决什么

前端是交互性的，截图只能展示一个状态；业务方/评审看不到：

- 从哪里进入；
- 点击后去哪；
- 空/加载/失败/部分成功分别是什么样；
- 数据在哪一步写入。

UE 稿把这些整理成一张**可缩放、可搜索的页面地图**，并补充布局/入口/交互说明。

## 2. 参考 Skill

- 来源：GitHub `BadbotAI/BadGoods` → `skills/frontend-to-ue`（v4.1）
- 能力：读取前端源码/HTML/可访问地址 → 提取页面/状态/跳转 → 生成可缩放 HTML 页面地图 → 逐页导出 PNG
- 可选：明确要求时才生成 Figma；默认不生成
- **许可**：仓库未选定开源许可证；只在本地个人使用，**不要把 Skill 代码提交到本项目仓库**

> 已在本机安装到 `~/.config/opencode/skills/frontend-to-ue`；重启 OpenCode 后可用。

## 3. 输出

| 产物 | 说明 |
|---|---|
| HTML 页面地图 | 一张可平移/缩放的画布，按模块平铺关键页面/状态 |
| 页面 PNG | 只含当前页面，不含画布/工具栏 |
| UE 标注 PNG | 页面 + 布局/入口/交互/状态说明 |
| Figma（可选） | 只有明确要求时做；需要可编辑能力 |

默认输出目录建议：

```text
docs/product/ue/
├── ue-spec.json
├── map.html
├── screens/
└── exports/
```

> 如果截图中含真实题目/账号/路径，先把 `docs/product/ue/` 加入 `.gitignore`，只提交脱敏版。

## 4. 最小 UE 模型（`ue-spec.json`）

```json
{
  "schemaVersion": "1.1",
  "source": { "label": "frontend local demo", "sha256": "...", "runtime": "local" },
  "viewport": { "width": 1440, "height": 900 },
  "screens": [
    {
      "id": "QNEW-01",
      "module": "错题",
      "title": "录入错题",
      "kind": "page",
      "state": "default",
      "entry": "首页 / 录入",
      "purpose": "文本或图片录入错题",
      "evidence": { "level": "observed", "anchor": "src/views/QuestionCreateView.vue" },
      "preconditions": ["已登录"],
      "reads": ["Question"],
      "writes": ["Question"],
      "annotation": {
        "layout": ["顶部标题", "输入区", "学科/标签", "底部主按钮"],
        "entries": ["首页 → 录入"],
        "rules": ["题干必填", "图片 ≤5MB"]
      },
      "capture": "screens/QNEW-01.png",
      "view": "screens/QNEW-01.html"
    }
  ],
  "transitions": [
    {
      "id": "TR-01",
      "from": "QNEW-01",
      "to": "QDETAIL-01",
      "trigger": "点击“开始分析”并成功",
      "effect": "进入错题详情",
      "evidence": "observed"
    }
  ],
  "entities": [],
  "dataFlows": [],
  "coverage": {},
  "limitations": []
}
```

证据等级：

| 等级 | 含义 |
|---|---|
| `observed` | 实际点击/运行验证 |
| `source` | 源码可见，未运行 |
| `fixture` | 人工构造的测试状态 |
| `inferred` | 推断，需复核 |
| `proposed` | 建议，不是已实现 |

## 5. 本项目的页面 ID

| ID | 页面 | 关键状态 |
|---|---|---|
| `AUTH-01` | 登录/注册 | 默认/错误/loading |
| `HOME-01` | 首页 | 最近错题/任务入口/空 |
| `QLIST-01` | 错题列表 | 有数据/空/筛选无结果 |
| `QNEW-01` | 录入/编辑 | 三种题型/草稿/图片裁剪/多题条目/提取中/失败 |
| `TASK-01` | 任务中心 | 排队/生成中/完成/失败/草稿行 |
| `QDETAIL-01` | 错题详情 | 分析完成/生成中/partial/error |
| `PRACTICE-01` | 练习 | 未答/已答/揭晓/提交失败 |
| `STATS-01` | 统计/概览（P1） | 有数据/空/loading |

> 只拆“业务差异”导致的页面/状态，不要按 DOM 或 if 分支机械拆页。

## 6. 工作流

```text
1. 启动前端 Demo（本地）
2. 走核心路径：登录 → 录入 → 分析 → 生成 → 练习 → 统计
3. 记录页面/状态/跳转/数据读写；标记 observed/source/fixture/inferred
4. 脱敏：虚构学生、虚构题目、去掉真实路径/账号/图片
5. 写 ue-spec.json
6. 生成 HTML 地图 / PNG
7. 实际打开地图，检查平移/缩放/搜索/跳转/导出
8. 把覆盖范围、未验证项、已知限制写入报告
```

## 7. 验收清单

- [ ] 关键页面/状态都有成稿，合并/排除有理由
- [ ] 每条跳转的 from/to 都存在，没有悬空目标
- [ ] 页面地图可平移、缩放、搜索、复位
- [ ] 选中页面能看到布局/入口/交互
- [ ] 两类 PNG 实际下载并打开检查
- [ ] 证据等级标注清楚，未验证不冒充已实现
- [ ] 已脱敏：无真实姓名/账号/路径/密钥
- [ ] 不把截图说成“可编辑 Figma”
- [ ] 不把“前端转换”说成“后端已接入”

## 8. 提示词模板

```text
使用 frontend-to-ue，把 frontend/ 的本地 Demo 转成 UE 稿。

范围：只覆盖 P0 的 8 个页面和关键状态（见 docs/product/05-ue-spec.md）。
输出：默认生成可本地打开的 HTML 页面地图 + 两类 PNG；不要生成 Figma。
要求：
- 用虚构学生/虚构题目，先脱敏；
- 标注证据等级（observed/source/fixture/inferred）；
- 补充布局、入口、交互、数据读写；
- 不修改原前端代码；
- 最后给覆盖范围、未验证项和已知限制。
```

## 9. 不要做什么

- 不要在前端还没跑起来时硬做 UE 稿。
- 不要用真实学生数据/截图。
- 不要把 Skill 代码/许可文件提交到本项目仓库。
- 不要用 UE 稿证明后端已接入。
- 不要为了好看改业务规则。
