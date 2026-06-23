"""
Apple Health 数据解析子包

提供 Apple HealthKit 导出 XML 的流式解析能力，支持 Legacy 与 CDA 两种格式。
核心资产 vendor 自外部仓库 AppleHealth-DB（仅解析层，零 ORM 依赖）。

公共接口：
    create_parser(xml_path) -> parser 实例
    detect_format(xml_path) -> "cda" | "legacy" | "unknown"
"""
from app.services.apple_health.parser import (
    create_parser,
    detect_format,
    CDAHealthXMLParser,
    LegacyHealthXMLParser,
    HealthXMLParser,
    parse_cda_datetime,
)
from app.services.apple_health.converter import (
    ACTIVITY_TYPE_MAP,
    HEART_RATE_TYPE_MAP,
    SLEEP_STAGE_MAP,
    WORKOUT_TYPE_MAP,
    ECG_CLASSIFICATION_MAP,
    convert_unit,
    parse_iso_datetime,
    parse_duration_seconds,
    generate_uuid,
    get_sleep_stage,
    get_workout_type,
    get_heart_rate_measurement_type,
    infer_motion_context,
)

__all__ = [
    # parser
    "create_parser",
    "detect_format",
    "CDAHealthXMLParser",
    "LegacyHealthXMLParser",
    "HealthXMLParser",
    "parse_cda_datetime",
    # converter
    "ACTIVITY_TYPE_MAP",
    "HEART_RATE_TYPE_MAP",
    "SLEEP_STAGE_MAP",
    "WORKOUT_TYPE_MAP",
    "ECG_CLASSIFICATION_MAP",
    "convert_unit",
    "parse_iso_datetime",
    "parse_duration_seconds",
    "generate_uuid",
    "get_sleep_stage",
    "get_workout_type",
    "get_heart_rate_measurement_type",
    "infer_motion_context",
]
