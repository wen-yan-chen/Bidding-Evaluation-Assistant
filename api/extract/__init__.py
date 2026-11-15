"""字段抽取包：确定性的结构化字段 + 溯源三元组（不经过模型）。"""

from api.extract.fields import FIELD_SPECS, extract_fields, field_values

__all__ = ["FIELD_SPECS", "extract_fields", "field_values"]
