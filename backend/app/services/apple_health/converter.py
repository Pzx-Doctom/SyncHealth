"""
HealthKit 数据类型转换器
负责 HealthKit 类型标识符到项目内部类型的映射，以及单位转换
"""
from datetime import datetime, timezone, timedelta
import hashlib


# ============================================================
# HealthKit 类型标识符 → 数据库 metric_type 映射
# ============================================================

ACTIVITY_TYPE_MAP = {
    "HKQuantityTypeIdentifierStepCount": "steps",
    "HKQuantityTypeIdentifierDistanceWalkingRunning": "distance_meters",
    "HKQuantityTypeIdentifierActiveEnergyBurned": "active_energy_kcal",
    "HKQuantityTypeIdentifierBasalEnergyBurned": "resting_energy_kcal",
    "HKQuantityTypeIdentifierAppleStandTime": "stand_hours",
    "HKQuantityTypeIdentifierFlightsClimbed": "flights_climbed",
    "HKQuantityTypeIdentifierAppleExerciseTime": "exercise_time",
}

HEART_RATE_TYPE_MAP = {
    "HKQuantityTypeIdentifierHeartRate": "heart_rate",
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_heart_rate",
    "HKQuantityTypeIdentifierWalkingHeartRateAverage": "walking_heart_rate_average",
}

# 睡眠阶段值映射（HealthKit XML 中的 value 属性）
SLEEP_STAGE_MAP = {
    "HKCategoryValueSleepAnalysisInBed": "in_bed",
    "HKCategoryValueSleepAnalysisAsleep": "asleep",
    "HKCategoryValueSleepAnalysisAwake": "awake",
    "HKCategoryValueSleepAnalysisAsleepCore": "core",
    "HKCategoryValueSleepAnalysisAsleepDeep": "deep",
    "HKCategoryValueSleepAnalysisAsleepREM": "rem",
    # 旧版/简化值
    "inBed": "in_bed",
    "Asleep": "asleep",
    "Awake": "awake",
    "Core": "core",
    "Deep": "deep",
    "REM": "rem",
}

# Workout 类型映射
WORKOUT_TYPE_MAP = {
    "HKWorkoutActivityTypeRunning": "running",
    "HKWorkoutActivityTypeCycling": "cycling",
    "HKWorkoutActivityTypeWalking": "walking",
    "HKWorkoutActivityTypeSwimming": "swimming",
    "HKWorkoutActivityTypeYoga": "yoga",
    "HKWorkoutActivityTypeTraditionalStrengthTraining": "strength_training",
    "HKWorkoutActivityTypeHighIntensityIntervalTraining": "hiit",
    "HKWorkoutActivityTypeDance": "dance",
    "HKWorkoutActivityTypeHiking": "hiking",
    "HKWorkoutActivityTypeRowing": "rowing",
}

# ECG 分类映射
ECG_CLASSIFICATION_MAP = {
    "HKECGClassificationSinusRhythm": "sinus_rhythm",
    "HKECGClassificationAtrialFibrillation": "atrial_fibrillation",
    "HKECGClassificationInconclusiveLowHeartRate": "inconclusive",
    "HKECGClassificationInconclusiveHighHeartRate": "inconclusive",
    "HKECGClassificationInconclusivePoorReading": "inconclusive",
    "HKECGClassificationInconclusiveOther": "inconclusive",
    "HKECGClassificationUnrecognized": "inconclusive",
}


# ============================================================
# 单位转换
# ============================================================

def convert_unit(value: float, from_unit: str, to_unit: str) -> float:
    """
    单位转换
    :param value: 数值
    :param from_unit: 原单位
    :param to_unit: 目标单位
    :return: 转换后的数值
    """
    # 距离转换
    if from_unit == "km" and to_unit == "m":
        return value * 1000
    if from_unit == "mi" and to_unit == "m":
        return value * 1609.344
    if from_unit == "cm" and to_unit == "m":
        return value / 100

    # 能量转换
    if from_unit == "kJ" and to_unit == "kcal":
        return value / 4.184
    if from_unit == "Cal" and to_unit == "kcal":
        return value / 1000

    # 温度转换
    if from_unit == "degF" and to_unit == "degC":
        return (value - 32) * 5 / 9

    # 时间转换
    if from_unit == "min" and to_unit == "s":
        return value * 60
    if from_unit == "hr" and to_unit == "s":
        return value * 3600

    # 血氧：HealthKit 存储为 0-1 比例，需要 ×100 转为百分比
    if from_unit == "fraction" and to_unit == "percent":
        return value * 100

    # 无法识别的转换，原样返回
    return value


# ============================================================
# 时间解析
# ============================================================

def parse_iso_datetime(dt_str: str) -> datetime | None:
    """
    解析 HealthKit XML 中的日期时间字符串
    格式示例: "2024-01-01 08:00:00 +0800"
    """
    if not dt_str:
        return None
    try:
        # 处理格式: "2024-01-01 08:00:00 +0800"
        # 去掉时区中的空格
        cleaned = dt_str.strip()
        # 尝试解析带时区的格式
        for fmt in (
            "%Y-%m-%d %H:%M:%S %z",
            "%Y-%m-%d %H:%M:%S.%f %z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
        ):
            try:
                return datetime.strptime(cleaned.replace(" ", "T"), fmt)
            except ValueError:
                try:
                    # 去掉时区部分的冒号
                    cleaned_no_tz_colon = cleaned.replace("+", "+").replace("-", "-")
                    return datetime.strptime(cleaned_no_tz_colon, fmt)
                except ValueError:
                    continue

        # 尝试解析不带时区的格式
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
        ):
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue

        return None
    except Exception:
        return None


def parse_duration_seconds(start_str: str, end_str: str) -> float | None:
    """计算两个时间字符串之间的秒数差"""
    start = parse_iso_datetime(start_str)
    end = parse_iso_datetime(end_str)
    if start and end:
        return (end - start).total_seconds()
    return None


# ============================================================
# UUID 生成（当 HealthKit 未提供 HKObjectUUID 时使用）
# ============================================================

def generate_uuid(record_type: str, start_date: str, value: str, source: str = "") -> str:
    """
    根据记录内容生成唯一 ID
    用于 HealthKit XML 中没有 HKObjectUUID 的记录
    """
    content = f"{record_type}|{start_date}|{value}|{source}"
    return hashlib.md5(content.encode("utf-8")).hexdigest()


# ============================================================
# 睡眠阶段解析辅助
# ============================================================

def get_sleep_stage(value: str) -> str | None:
    """
    将 HealthKit 睡眠阶段的 value 转换为内部 stage 值
    """
    if not value:
        return None
    return SLEEP_STAGE_MAP.get(value)


def is_sleep_in_bed(value: str) -> bool:
    """判断是否为'在床'状态"""
    return get_sleep_stage(value) == "in_bed"


def is_sleep_asleep(value: str) -> bool:
    """判断是否为'睡眠'状态（包括各阶段）"""
    stage = get_sleep_stage(value)
    return stage in ("asleep", "core", "deep", "rem")


def get_sleep_stage_name(value: str) -> str | None:
    """获取睡眠阶段名称"""
    return get_sleep_stage(value)


# ============================================================
# Workout 类型解析
# ============================================================

def get_workout_type(activity_type: str) -> str | None:
    """将 HealthKit workoutActivityType 转换为内部 workout_type"""
    if not activity_type:
        return None
    return WORKOUT_TYPE_MAP.get(activity_type)


# ============================================================
# 心率相关
# ============================================================

def get_heart_rate_measurement_type(record_type: str) -> str:
    """根据 HealthKit 类型标识符获取心率测量类型"""
    return HEART_RATE_TYPE_MAP.get(record_type, "heart_rate")


def infer_motion_context(metadata: dict) -> str:
    """
    根据元数据推断运动上下文
    HealthKit 可能包含 HKMetadataKeyHeartRateMotionContext
    """
    context = metadata.get("HKMetadataKeyHeartRateMotionContext", "")
    if context == "1":
        return "sedentary"
    elif context == "2":
        return "active"
    return "unset"
