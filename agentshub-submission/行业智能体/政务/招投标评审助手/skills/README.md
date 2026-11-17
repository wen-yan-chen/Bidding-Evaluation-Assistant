# skills/ — 自定义 Skill（D9 已上传，agent v5 已发布）

四个 Skill 各一个 zip，`SKILL.md` 只写四段（When to use / Inputs / Outputs / Hard rules），
**只放流程，不放判定逻辑**（判定在 MCP）。

| Skill | 触发时机 | 作用 | 包 |
| --- | --- | --- | --- |
| `bid-rule-cards` | 判断某条内容是否违规前 | 按类别取规则卡，取不到不得判定 | `bid-rule-cards.zip` |
| `missing-qualification` | 资格性审查时 | 缺失/效力不足/已提供三态判定 | `missing-qualification.zip` |
| `bid-risk-selfcheck` | 输出与导出之前 | 逐条核对溯源，不通过就删（降误报） | `bid-risk-selfcheck.zip` |
| `summary-compiler` | 生成摘要与报告时 | 六要素摘要 + 九章报告成文 | `summary-compiler.zip` |

每个 zip 的根目录只有一个 `SKILL.md`（已校验）。平台按 `SKILL.md` 的 **YAML frontmatter** 读取
`name` / `description`，缺任意一个会报「技能文件中未找到 name 或 description 字段」；四个包都已补：

```yaml
---
name: bid-rule-cards
description: 判断某条投标内容是否违反审查规则前，按类别取规则卡；取不到规则卡不得判定。
allowed-tools:
  - knowledge_base_search
  - scan_risks
  - locate_span
---
```

上传前可用 Nexent 自带解析器自检：

```bash
# 在 nexent-runtime 容器内
/opt/backend/.venv/bin/python -c \
  "from nexent.skills.skill_loader import SkillLoader; print(SkillLoader.load('/tmp/bid-rule-cards.SKILL.md'))"
```

上传流程：

1. 登录 Nexent（本机 `http://127.0.0.1:3000`）→ Skill / 技能 → 上传 4 个 zip；
2. 重新导入 `agent.json`（`skill_names` 四个名字必须与包内标题一致）；
3. 在对话里验证：问“这条违反哪条规则”应触发 `bid-rule-cards`；问“缺什么材料”应触发
   `missing-qualification`；导出前应触发 `bid-risk-selfcheck`；要报告时触发 `summary-compiler`；
4. 平台侧上传完成后，把 `/api/health` 的 `skills` 开关置 true，并在 D9 自测记录留截图（已完成）。

> 当前状态：4 个包已上传到 Nexent（`bid-rule-cards` / `missing-qualification` /
> `bid-risk-selfcheck` / `summary-compiler`），`SkillLoader` 解析通过；智能体 `招投标评审助手`
> （agent_id=7）已于 2026-11-16 10:02 保存并发布 **v5**（`招投标评审助手-2611161002`），
> `agent.json.skill_names` 与平台四个技能名一致；`/api/health` 的 `skills` 已置 true。
> 平台已有来自 32 题 contract-review 的 `risk-selfcheck`，本项目使用唯一名 `bid-risk-selfcheck`，未覆盖它。
