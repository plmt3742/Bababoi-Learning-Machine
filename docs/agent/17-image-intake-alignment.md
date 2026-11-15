---
owner: 霹雳马桶 / 人机
last_updated: 2026-11-11
status: archived
read_when: 只在追溯 2026-11-06 图片录入接口对接时读；现行口径以 05 §6.8/§7.0 与 ADR-004 为准
---

# 图片录入 · 接口对齐结论（2026-11-06，已归档）

> 本文件整理自 2026-11-06 的图片录入接口对接记录，**保留原小节编号（§〇–§七）**，供 05 / ADR-004 按号引用。
> 现行契约以 `05-architecture.md`（§6.8 / §7.0）与 ADR-004 为准；标注「已被取代」的条目只作历史依据。

## 〇、一句话结论

主线前端（main）与当时的三段/识图后端完全对齐；脱节的只有 #38 新加的 `subject / chapter / difficulty` 三个字段。后端补齐这三个（按「建议值」语义）即可直连，前端不用改。

## 一、已对齐（逐项打勾，不用动）

| 能力 | 前端 | 后端 | 状态 |
|---|---|---|---|
| 上传 | `POST /uploads/images`，multipart 字段名 `file` | 同名端点、`File()` 接收 | ✅ |
| 上传返回 | `image_path, url, width, height` | `ImageUploadOut` 同四个字段 | ✅ |
| 提取入参 | `{ image_path, subject? }` | `FromImageRequest` 同字段 | ✅ |
| 提取返回 | `{ image_path, questions[], warnings[] }` | `ImageExtractionOut` 同字段 | ✅ |
| 题目条目 | `index, content_md, question_type, options, blanks, has_figure, warnings, incomplete?` | `ExtractedQuestionOut` 同字段 | ✅ |
| 生成入参 | `difficulties?` / `target_index?`（FE-023） | `GenerateQuestionsPayload` 同字段 | ✅ |
| 生成返回 | `{ tasks: [...] }`，旧 `{ task_id }` 兼容分支 | 只返回 `tasks` | ✅（前端兜底已于 2026-11-10 删除） |

## 二、唯一差异：#38 多出的三个字段

`frontend/src/api/types.ts` 在 `ExtractedImageQuestion` 上加了 `subject?` / `chapter?` / `difficulty?`，并在这些位置消费：

- `ImageIntakeFlow.vue`：用户没手选学科时用模型初判自动回填；
- `ImageItemCard.vue`：渲染「学科：xxx」「难度：xxx」标签 + 章节输入框；
- `utils/imageIntake.ts`：`question.subject?.trim() ?? ''`；
- `README.md`：写明提取结果包含这三个字段。

后端 `ExtractedQuestionOut` 当时没有这三个字段：合并不会崩（都是可选 + `v-if` + `?? ''`），但自动预填与两个标签会静默失效。

**决定**：后端在 `ExtractedQuestionOut` 增加三个可空字段，提取侧校验保持宽松——缺了就 `None`，不算失败；非法档位（如 `"中等"`）降级成 `null`，不丢条目。

> **difficulty 的后续**：初判难度在两次实拍里填充率只有 4/14 与 8/14，且会与 analysis 的正式难度抢真源，讨论过移除。截至 2026-11-11 字段仍在、只作展示（正式难度以 analysis 为准）；是否移除见 05 §6.8。

## 三、三条必须写死的规则

**规则 1：`subject` 的优先级**
请求里带了 `subject` → 所有条目回填该值（用户选过的值不能用模型猜的覆盖）；请求里没带 → 用模型初判，允许 `None`。已写死在 `extract_from_image`：校验后逐条覆写，不靠提示词的概率保证。

**规则 2：`chapter` 只作建议，不直接入库**
模型造的词（「导数与极值」）与标签体系不一定一致。前端把 `chapter` 当 placeholder（输入框灰字提示），用户点了才算。后端只照抄图上真实出现的标题，图上没有就 `None`，提示词明写「不要自己编章节名」。

**规则 3：analysis 不覆盖用户已确认的值**
`subject` / `chapter` 以用户确认为准；`difficulty` 以 analysis 为准（识图初判只用于卡片徽章，不进库）。否则「两套真源」会在详情页对撞。

## 四、前端要跟着改的四处

| # | 变更 | 前端要做什么 |
|---|---|---|
| 1 | 题型从硬约束改为软约束 | 卡片不能假设三题同类型，每张卡按自己的 `question_type` 渲染。**已被取代**：BE-026/ADR-008 起由用户开关控制，strict（默认开）下 prompt 写死同题型、版本 `generate_v3`；soft 仍允许换题型。 |
| 2 | 生成从一次 3 题改为三段并发（`{tasks:[...]}`） | FE-023 已适配；旧 `{task_id}` 兜底分支已于 2026-11-10 删除。 |
| 3 | 图片 `url` 是鉴权路径（`/api/v1/uploads/{uid}/{file}`） | 显示服务端图必须 `fetch` + `createObjectURL`，不能 `<img src>`（带不上 Authorization）。 |
| 4 | `incomplete=true` 的条目允许空答案 | 确认步骤必须让用户补完才能 `POST /questions`。**口径已升级**（v0.6.3）：结构不自洽的条目整条降级成纯文本（`question_type=solve`、`options`/`blanks` 为 `null`），所以「填空条目一定带 blanks」这个隐含假设不再成立。 |

## 五、联调验收（用真实请求，不看 mock）

- [ ] `POST /uploads/images` 传一张真图 → 返回四个字段，`url` 形如 `/api/v1/uploads/42/xxxx.jpg`
- [ ] `GET` 该 `url`（带 JWT）→ 200 + 图片字节；不带 JWT → 401；换成别人的 uid → **404**
- [ ] `POST /questions/from-image` → `questions` 1..N，`index` 从 1 连续，`incomplete` 字段存在
- [ ] 三张样本图（密页 4 题 / 稀疏 / 混排）都能返回
- [ ] 提取结果里 `subject/chapter/difficulty` 存在或为 `null`，前端不报错
- [ ] 用户改过 subject 后，`POST /questions` 存的是用户值，不是模型值
- [ ] analysis 完成后，`subject/chapter` 不被覆盖
- [ ] `POST /questions/{id}/generate`（不带 `target_index`）→ 返回 3 条 `tasks`，各有 `target_index` + `difficulty`

## 六、合并顺序（历史）

当时的顺序是「先合三段（#39）→ #40 rebase 到 main → 合 #40 → #38 去掉 backend 后合」。这些 PR 已全部关闭/取代（#38 由 #49 替代，#39/#40 由 #42 承接），仅作历史记录。

## 七、结论

三个字段按「可能存在、可空」对接即可直连；后端保证「用户值优先、analysis 不覆盖」。

## 附录：后端处置记录（2026-11-07）

| 本文条目 | 后端处置 | 落点 |
|---|---|---|
| §二 补三字段 | 已补，条目级、三项皆可空；非法档位（`"中等"`）降级成 `null`，不丢条目 | `ai/validator.py::ExtractedQuestion` |
| §三 规则 1 | 写死在代码里：`extract_from_image` 在校验后逐条覆写 `subject` 为请求值 | `services/extraction_service.py`（05 v0.6.3） |
| §三 规则 2 | `chapter` 只照抄图上真实标题，图上没有就 `null`，提示词明写不要自编 | `ai/prompts.py` 第 9 条 |
| §三 规则 3 | analysis 不写 `subject`/`chapter`；`difficulty` 正式值只来自 analysis，识图初判不进库 | 05 §6.8「初判」条 |
| §四-4 | 口径升级：`incomplete` 分两类——题干残缺原样返回；结构不自洽整条降级成纯文本（`question_type=solve`、两项置空 + warning） | 05 §6.8/§7.0、ADR-004 §6.1 |
| §一 条目字段对齐 | 字段名对齐成立；补一句：`options`/`blanks` 的**可空是承重的**，不是「一般会有的附加字段」（ADR-004 §5，按 §6 复审条件落地） | ADR-004 §5/§6.1 |

**验收口径的一处修正**：联调不要求「样本图的题目数与人工判断一致」——条目数是模型的概率行为（两次实拍都是 5/5/4，但拆分/合并行为不可由接口契约保证）。验收看「文字有没有到手」（实测 14/14），条数不符走裁剪重传，不算接口缺陷。
