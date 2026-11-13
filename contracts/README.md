# contracts

前后端共享的 **API 契约**，不是代码包。

## 为什么需要

前后端并行开发时，最容易出问题的是“字段名/类型/错误码不一致”。`contracts/` 是两个人共同看的“接口真相”：

- 后端用 Pydantic 定义请求/响应；
- FastAPI 自动生成 OpenAPI；
- 前端从 OpenAPI 生成 TypeScript 类型；
- Mock、测试、联调都用同一份示例。

## 目录

```text
contracts/
├── README.md
├── openapi/
│   ├── README.md
│   └── openapi.json          # 由后端导出，提交仓库
└── examples/
    ├── README.md
    ├── auth.json
    ├── question.json
    ├── analyze.json
    ├── generate.json
    └── practice.json
```

## 规则

1. **`openapi/openapi.json` 是契约事实**；后端改 schema 后重新导出。
2. 示例只放**合成数据**，不放真实学生题目、姓名、图片。
3. 前端不手写重复类型；优先从 OpenAPI 生成 `frontend/src/api/types.ts`。
4. 破坏性变更（删字段/改类型/改路径）必须先改 `docs/agent/05-architecture.md`，两人确认。
5. 错误码只加不改；前端按 `code` 分支，不按 message。

## 工作流

```text
后端改 Pydantic schema
  → 导出 contracts/openapi/openapi.json
  → 前端生成 api/types.ts
  → Mock/联调用 contracts/examples/
  → CI 检查 OpenAPI 能否生成类型
```

> `openapi/openapi.json` 由 `backend/scripts/export_openapi.py` 导出（BE-009），
> CI 会比对快照，改了 schema 必须同 PR 更新。
