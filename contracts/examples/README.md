# examples

放**合成**的请求/响应示例，给 Mock、测试、联调共用。

建议文件：

```text
auth.json          # 注册/登录/me
question.json      # 创建/列表/详情
analyze.json       # AI 分析结果
generate.json      # 3 道生成题
practice.json      # 练习记录/统计
```

规则：

- 只用虚构学生、虚构题目、虚构图片路径。
- 字段必须与 `docs/agent/05-architecture.md` 一致。
- 不放真实 API Key、JWT、数据库密码。
- 示例变更随契约 PR 一起更新。
