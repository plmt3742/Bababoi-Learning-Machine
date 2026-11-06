---
owner: 霹雳马桶（前端）/ 人机（后端处置）
last_updated: 2026-11-07
status: active
read_when: 图片录入联调、#38/#39/#40 合并顺序、识图出参字段取舍
---

> **来源与真相源**：原件是 2026-11-06 的《接口对齐清单-图片录入-20261106.md》
> （出具人写的是「林敬翔」，即前端 霹雳马桶），正文 §〇–§七 原文未改动照录；
> 文末「附：后端逐条处置」由后端（人机）追加。`05-architecture.md` v0.6.3 与 ADR-004 §6.1
> 引用本文小节号时，以这份仓库内的副本为准。

# 图片录入 · 前后端接口对齐清单

> 出具：前端（林敬翔） · 2026-11-06
> 目的：**确保 #38 前端能接上 #40 后端**。清单只描述"哪边改什么"，不重复设计讨论。
> 核对依据：`backend/app/schemas/image.py`、`backend/app/api/v1/images.py`、`frontend/src/api/types.ts`、PR #38 diff

---

## 〇、一句话结论

**主线前端（main）与 #40 后端是完全对齐的**；脱节的只有 #38 新加的 `subject / chapter / difficulty` 三个字段。补上这三个（按"建议值"语义），#38 就能接上，前端不用改。

---

## 一、已对齐（逐项打勾，不用动）

| 能力 | 前端 | 后端 | 状态 |
|---|---|---|---|
| 上传 | `POST /uploads/images`，multipart 字段名 `file` | 同名端点、`File()` 接收 | ✅ |
| 上传返回 | `image_path, url, width, height` | `ImageUploadOut` 同四个字段 | ✅ |
| 提取入参 | `{ image_path, subject? }` | `FromImageRequest` 同字段 | ✅ |
| 提取返回 | `{ image_path, questions[], warnings[] }` | `ImageExtractionOut` 同字段 | ✅ |
| 题目条目 | `index, content_md, question_type, options, blanks, has_figure, warnings, incomplete?` | `ExtractedQuestionOut` 同字段 | ✅ |
| 生成入参 | `difficulties?` / `target_index?`（FE-023） | `GenerateQuestionsPayload` 同字段 | ✅ |
| 生成返回 | `{ tasks: [...] }`，兼容旧 `{ task_id }` | #39 返回 `tasks` | ✅ |

---

## 二、唯一差异：#38 多出的三个字段

`frontend/src/api/types.ts` 在 `ExtractedImageQuestion` 上加了：

```ts
subject?: string | null
chapter?: string | null
difficulty?: Difficulty | null
```

前端还实际用了它们：

- `ImageIntakeFlow.vue`：用户没手选学科时，`emit('update:subject', detectedSubject)` 自动回填
- `ImageItemCard.vue`：渲染「学科：xxx」「难度：xxx」标签 + 章节输入框
- `utils/imageIntake.ts`：`question.subject?.trim() ?? ''`
- `README.md`：写明「提取结果包含 subject、chapter、difficulty」

**后端 `ExtractedQuestionOut` 没有这三个字段**，所以现在合并的话：不会崩（都是可选 + `v-if` + `?? ''`），但**自动预填和两个标签会静默失效**。

### 决定：后端补上，前端不动

在 `ExtractedQuestionOut` 增加：

```python
subject: str | None = None
chapter: str | None = None
difficulty: Literal["easy", "medium", "hard"] | None = None
```

提取侧校验保持宽松：**缺了就 None，不算失败**。

---

## 三、三条必须写死的规则（否则又会打架）

**规则 1：`subject` 的优先级**
请求里带了 `subject` → 三题都回填这个值（用户已经选过，别用模型猜的覆盖）；
请求里没带 → 用模型判的，允许 None。

**规则 2：`chapter` 只作建议，不直接入库**
模型造的词（"导数与极值"）和标签体系里的词不一定一致。前端把 chapter 当 **placeholder**（输入框灰字提示），用户点了才算，**不自动写入**。

**规则 3：analysis 不覆盖用户已确认的值**
`subject` / `chapter` 以用户确认为准；`difficulty` 以 analysis 为准（模型预填只用于卡片徽章）。
否则"两套真源"会在详情页对撞。

---

## 四、我改过方案、前端要跟着改的四处

| # | 变更 | 前端要做什么 |
|---|---|---|
| 1 | 题型从**硬约束**改**软约束**（不一致入 warnings） | 卡片**不能假设三题同类型**，每张卡按自己的 `question_type` 渲染（选择题才渲选项） |
| 2 | 生成从"一次 3 题"改**三段并发**（`{tasks:[...]}`） | FE-023 已适配，确认旧 `{task_id}` 兼容分支还在即可 |
| 3 | 图片 `url` 是**鉴权路径**（`/api/v1/uploads/{uid}/{file}`） | 目前前端只用本地预览，还没真正取过服务端图；**以后要显示必须 `fetch` + `createObjectURL`，不能 `<img src>`**（带不上 Authorization） |
| 4 | `incomplete=true` 的条目允许空答案 | 前端确认步骤必须让用户补完才能 `POST /questions`，否则 400 |

---

## 五、联调验收（用真实请求，不看 mock）

- [ ] `POST /uploads/images` 传一张真图 → 返回四个字段，`url` 形如 `/api/v1/uploads/42/xxxx.jpg`
- [ ] `GET` 那个 `url`（带 JWT）→ 200 + 图片字节；不带 JWT → 401；换成别人的 uid → **404**
- [ ] `POST /questions/from-image` → `questions` 1..N，`index` 从 1 连续，`incomplete` 字段存在
- [ ] 三张样本图（密页 4 题 / 稀疏 / 混排）都能返回，且题目数与人工判断一致
- [ ] 提取结果里 `subject/chapter/difficulty` **存在或为 null**，前端不报错
- [ ] 用户改过 subject 后，`POST /questions` 存的是用户值，不是模型值
- [ ] analysis 完成后，`subject/chapter` 不被覆盖
- [ ] `POST /questions/{id}/generate`（不带 `target_index`）→ 返回 3 条 `tasks`，各有 `target_index` + `difficulty`

---

## 六、合并顺序（不改这条，前面都白搭）

```
1. 合 #39（三段）          ← #40 的 base 是它
2. #40 rebase/改 base 到 main → 合
3. #38 去掉 backend/ 那 7 个文件 → 合
```

**先合 #38 的话**，它改的 `validate_quiz` / `task_worker` 在 #39 之后是死路径，等于白合一次还要解一轮冲突。

---

## 七、一句话给前端

> 你按"这三个字段可能存在"写的代码不用改；后端补上、并保证"用户值优先、analysis 不覆盖"，就能直连。

---

## 附：后端逐条处置（2026-11-07，人机）

| 本文条目 | 后端做了什么 | 落在哪 |
|---|---|---|
| §二 补三字段 | 已补，条目级、三项皆可空；非法档位（`"中等"`）降级成 `null`，不丢条目 | `ai/validator.py::ExtractedQuestion`（`11c9378`） |
| §三 规则 1 | **写死在代码里**：`extract_from_image` 校验后逐条覆写 `subject` = 请求值。提示词那句"沿用 subject"只是概率保证，不作为交付口径 | `services/extraction_service.py`（v0.6.3） |
| §三 规则 2 | 后端配合：`chapter` 只照抄图上真实出现的标题，图上没有就 `null`，提示词明写"不要自己编章节名" | `ai/prompts.py` 第 9 条 |
| §三 规则 3 | 后端本来就不让 analysis 写 `subject`/`chapter`；`difficulty` 的正式值只来自 analysis，识图初判不进库、只出现在这一次响应里 | 05 §6.8「初判」条 |
| §四-4 | **口径升级了，前端要再看一眼**：`incomplete` 现在分两类——题干残缺的仍原样返回；**结构不自洽的整条降级成纯文本**（`question_type=solve`、`options`/`blanks` 都是 `null` + 一句 warning）。所以卡片按 `question_type` 渲染这条规则不用改，但**"填空条目一定带 blanks"这个隐含假设现在彻底不成立了** | 05 §6.8/§7.0、ADR-004 §6.1 |
| §一 表格里「题目条目 ✅」 | 字段名对齐仍然成立；补充一句：`options`/`blanks` 的**可空是承重的**，不是"一般会有的附加字段"。ADR-004 §5 早写成可选，这次是按 §6 的复审条件（结构化成功率 86% < 90%）把它落到实现上 | ADR-004 §5/§6.1 |

**没有照抄清单的一处**：清单 §五 第 4 项要"三张样本图的题目数与人工判断一致"。这一条后端只能部分背书——
实拍三张的条目数在两次运行里都是 5/5/4，但模型会不会把两小题并成一条、或把一道拆成两条，
是概率行为，不是接口契约能保证的。验收时按"文字有没有到手"看（实测 14/14），
条数对不上属于识别质量问题，走裁剪重传，不算接口缺陷。
