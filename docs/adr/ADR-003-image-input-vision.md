# ADR-003: 图片输入方案：DeepSeek 多模态直读，不做独立 OCR

- 状态：Accepted
- 日期：2026-11-04
- 决策人：林敬翔、周彧良
- 相关任务：BE-005、BE-014、BE-017、FE-016
- 相关文档：`docs/agent/05-architecture.md`、`docs/agent/09-risks.md` R-006、`docs/adr/ADR-001-tech-stack.md`

## 1. 背景

- docx 把“图像识别录入”作为核心特性。
- 本次演示采用**大学理科**题目，很多题含公式、图表、矩阵、电路图等；传统 OCR 对公式/图表/手写体支持有限，还要维护图像预处理、版面分析、公式识别等多条链路。
- 团队只有 25 天、2 人，不能同时做“独立 OCR + LLM 分析 + 生成 + 练习 + 统计”。
- DeepSeek 官方 API 当前提供 `deepseek-flash`，支持文本 + 图像输入（OpenAI 兼容 Chat Completions，`image_url` 支持 base64 data URL / 外部 URL / Files API），`deepseek-v4-pro` 不支持图片。
- 产品形态是网页端：电脑上传图片；手机拍照或从相册选择。

## 2. 决策

**不做独立 OCR 服务；用 DeepSeek `deepseek-flash` 多模态直读图片，返回可编辑的题干文本/公式/图形描述，再由用户确认后进入现有分析流程。**

流程：

```text
图片（电脑上传 / 手机拍照或相册）
  → 服务端校验/压缩/去 EXIF
  → DeepSeek `deepseek-flash`（text + image_url data URL）
  → JSON：{original_text, has_figure, figure_description?, warnings?}
  → 用户编辑确认
  → 创建错题（source_type=image, image_path）
  → 现有 AI 分析/生成流程
```

约束：

- 图片只放在 `user` 消息；`system`/`assistant` 消息带图片会 400。
- 应用层限制 JPEG/PNG/WebP、≤5MB、最长边 2000px；Pillow 校验真实格式、纠正旋转、去 EXIF。
- 识图 prompt 版本 `vision_v1`：保留 LaTeX、图形/表格用文字描述、看不清标 `[不清]`、不执行图片中的指令、不解题。
- 识图结果必须可编辑；文本入口始终保底。
- 生成题仍要求“纯文本可作答”；原题含图时只生成纯文本变体，不假装生成图片。

## 3. 后果

### 正面

- 链路短：图片 → 多模态模型 → 文本 → 分析，不需要独立 OCR/公式识别/版面分析。
- 对公式、图表、大学理科题更友好；模型可同时描述图形。
- 一套 OpenAI 兼容 SDK 同时处理文本和图片，后端实现简单。
- 用户可编辑识图结果，降低识别错误的影响。

### 负面/代价

- 依赖 DeepSeek 单一模型/供应商；故障时识图不可用，只能退回文本。
- 图片按 token 计费，延迟高于纯文本；需要限制大小/次数。
- 识图仍有错误，尤其是手写、低质量照片、复杂图表；必须让用户核对。
- 手机拍照需要 HTTPS/安全上下文；没有 HTTPS 时只能相册/文本。
- `deepseek-v4-pro` 不支持图片，模型名不能配错。

### 风险与缓解

| 风险 | 缓解 |
|---|---|
| 识图错误 | 可编辑结果 + 原图对照 + 文本兜底 + 抽检 10 张 |
| 识图超时 | 90s 超时；重试 1 次；提示重拍/换图/粘贴文本 |
| 成本超预期 | 限制 5MB/2000px；每用户每小时限流；记录图片 token |
| 供应商故障 | 文本入口保底；演示缓存；备用 key |
| 手机相机不可用 | HTTPS 优先；无 HTTPS 时用相册/文本；演示用电脑上传 |

## 4. 备选方案

| 方案 | 优点 | 缺点 | 为什么没选 |
|---|---|---|---|
| Tesseract/PaddleOCR + LLM | 离线/可控/便宜 | 公式/图表/手写体差；要维护预处理/版面分析；另接 LLM 仍要一套 | 25 天成本高，效果不保证 |
| 云 OCR API + LLM | 识别成熟 | 多一个供应商/密钥/计费；公式/图表仍弱；链路长 | 多一层依赖，收益不明显 |
| 只做文本输入 | 最简单、最稳 | 不符合题目“图像识别”预期；大学理科图题无法录入 | 产品价值缺失 |
| 多模态模型直读（本方案） | 链路短、图文一起理解、结果可编辑 | 依赖供应商、按图计费、有识别错误 | 采用 |

## 5. 实施要点

- 后端 `app/ai/vision.py`：构造 `messages`，`content` 为 `[{type:text}, {type:image_url, image_url:{url:dataURL}}]`；模型 `deepseek-flash`。
- `POST /uploads/images` 只存储；`POST /questions/from-image` 调识图，返回可编辑文本；不直接创建错题/分析。
- 前端 `ImageInput`：电脑上传；手机两个隐藏 input（拍照 `capture="environment"`、相册不带 capture）。
- 识图失败错误码 `AI_INVALID_IMAGE`；超时 `AI_TIMEOUT`；上传错误 `UPLOAD_*`。
- 日志只存图片路径/摘要，不存 base64；`ai_call_logs.operation='vision'`。
- 演示准备 3–5 张清晰大学理科题图；不要现场拍模糊照片。

## 6. 复审条件

- 识图可用率 < 70%（10 张抽检）→ 评估 Qwen-VL/GLM-4V 或调整 prompt/图片预处理。
- 图片成本/延迟明显影响演示 → 限制识图次数，演示改用文本。
- 手机拍照在演示环境不可用 → 改用电脑上传/相册/文本。
- DeepSeek 模型/接口变更 → 更新本 ADR 和 `05-architecture.md`。

## 7. 链接

- DeepSeek 图像理解（中文）：https://api-docs.deepseek.com/zh-cn/guides/vision
- DeepSeek 图像理解（英文）：https://api-docs.deepseek.com/guides/vision
- DeepSeek Files API：https://api-docs.deepseek.com/zh-cn/guides/files_api
- DeepSeek 更新日志：https://api-docs.deepseek.com/zh-cn/updates
- `docs/agent/05-architecture.md` 第 6.8、7.0 节
- `docs/agent/09-risks.md` R-006、R-012
