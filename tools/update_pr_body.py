import subprocess
import requests

BODY = """【课题】8 招投标评审助手（政务民生 / 中级）

【智能体目录】
行业智能体/政务/招投标评审助手/

【源码 / 过程仓库】
https://github.com/wen-yan-chen/Bidding-Evaluation-Assistant

【agent.json 关键配置】
- display_name：招投标评审助手
- 模型：导入后由目标环境选择（agent.json 不写死模型名）
- 默认评分细则：profile-a-calibrated（T2/B2/B3 要求实质响应）；profile-a / profile-b 保留作对照
- Skills：bid-rule-cards、missing-qualification、bid-risk-selfcheck、summary-compiler
- MCP：bid-review（8 个工具：parse_tender / check_qualification / score_item / scan_risks / locate_span / export_report / list_documents / parse_attachment）
- 知识库：40 条规则索引（导入时按目标环境替换 index_names，规则文档在 knowledge/rules-full.md）

【依赖安装】
1. 导入 agent.json；
2. 依次导入 skills/ 下 4 个 SKILL.md；
3. 按 DEPLOY.md 启动完整后端与 MCP（app 18080 / MCP 8765），在 MCP 配置中填实际地址；mcps/bid_review_mcp.py 不是独立服务；
4. 导入 knowledge/rules-full.md，确认 index_names 可用。

【自测结论】
- 解析 25/25；6 字段基线 146/146；8 字段扩展样本 14/14；
- 资格性人工标注 25 份 / 250 项 = 100%；
- 风险 TP 15 / FN 0 / FP 0；
- 规则覆盖 40 = 27 自动 + 10 人工 + 3 未实现（R25/R32/R33 需多家比价）；
- N01–N10 盲评：校准版 10/10 在 ±5 内，平均偏差 0.00；旧版 4/10；
- 本地 pytest 66 passed, 1 skipped；容器 pytest 67 passed。

【已知限制】
- N01–N08 的 T1/T3/T4 文本相同，样本对这三项区分力有限；N09/N10 已加入“有/无”对照；
- R25/R32/R33 单份不可判定；
- n=10 仍属小样本，不能外推；
- 全部演示数据为自造虚构，不输出中标/废标结论；
- 演示视频尚未录制。

【截图】
screenshots/01-评审看板.png、screenshots/02-报告预览.png（当前界面）
"""


def main() -> None:
    cred = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=gitcode.com\n\n",
        text=True,
        capture_output=True,
        check=True,
    )
    data = dict(line.split("=", 1) for line in cred.stdout.splitlines() if "=" in line)
    token = data["password"]
    resp = requests.patch(
        "https://gitcode.com/api/v5/repos/ModelEngine/AgentsHub/pulls/170",
        headers={"PRIVATE-TOKEN": token, "Content-Type": "application/json"},
        json={"body": BODY},
        timeout=20,
    )
    print(resp.status_code)
    print(resp.json().get("html_url"))
    print(resp.json().get("state"))


if __name__ == "__main__":
    main()
