from pathlib import Path

src = Path("data/scoring/profile-a.yaml")
dst = Path("data/scoring/profile-a-calibrated.yaml")
text = src.read_text(encoding="utf-8")
text = text.replace("id: profile-a", "id: profile-a-calibrated")
text = text.replace(
    "name: 综合评分法（价格 40 / 技术 40 / 商务 20）",
    "name: 综合评分法·校准版（T2/B2/B3 实质响应）",
    1,
)
text = text.replace('version: "2026-11-15"', 'version: "2026-11-16-calibrated"', 1)
text = text.replace(
    '    patterns: ["实施方案", "实施计划", "进度计划"]\n',
    '    patterns: ["实施方案", "实施计划", "进度计划"]\n'
    '    content_patterns: ["里程碑", "横道图", "关键路径", "进度安排", "工期安排", "进度控制"]\n',
)
text = text.replace(
    '    patterns: ["项目负责人", "项目经理", "项目团队", "技术负责人"]\n',
    '    patterns: ["项目负责人", "项目经理", "项目团队", "技术负责人"]\n'
    '    content_patterns: ["项目管理机构", "人员配置表", "人员表", "项目团队表", "职称证书", "注册建造师", "建造师证书", "项目经理证书"]\n',
)
text = text.replace(
    '    patterns: ["售后服务", "运维服务", "质保期", "服务响应"]\n',
    '    patterns: ["售后服务", "运维服务", "质保期", "服务响应"]\n'
    '    content_patterns: ["小时内响应", "小时响应", "小时到场", "SLA", "服务级别", "响应时限", "解决时限"]\n',
)
dst.write_text(text, encoding="utf-8")
print("written", dst)
