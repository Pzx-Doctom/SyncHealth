"""
Apple Health 解析器 → SyncPayload 适配层

流式消费 parser.parse() 产出的中间 dict，按 type 分派到 SyncPayload 各数组，
睡眠阶段经 sleep_aggregator 聚合，每累积 BATCH_SIZE 条组装一个 SyncPayload 并 yield。

关键处理：
    - 剥离 parser 中间 dict 的内部标签（_counter_key / type / is_in_bed / is_asleep）
    - 为 workout / mindfulness 补 recorded_at = start_time（parser 未生成，SyncHealth 必填）
    - sleep_stage 全部缓冲，解析结束时一次性聚合为 sleep_session（数据量小，不影响内存）
    - 分批入库，避免单个 SyncPayload 过大
"""
import logging
from datetime import datetime
from typing import Any, Iterator

from app.schemas.health import (
    ActivitySampleIn,
    BloodOxygenSampleIn,
    BodyTemperatureSampleIn,
    ECGRecordIn,
    HRVSampleIn,
    HeartRateIn,
    MindfulnessSessionIn,
    NoiseExposureSampleIn,
    RespiratoryRateSampleIn,
    SleepSessionIn,
    WorkoutHRZoneIn,
    WorkoutRecordIn,
)
from app.schemas.sync import DeviceInfo, SyncPayload, SyncWindow
from app.services.apple_health.parser import create_parser
from app.services.apple_health.sleep_aggregator import aggregate_sleep_sessions

logger = logging.getLogger(__name__)

BATCH_SIZE = 5000

# parser 中间 dict 的 type → (SyncPayload 字段名, 对应 Pydantic In 类)
RECORD_TYPE_MAP: dict[str, tuple[str, type]] = {
    "heart_rate": ("heart_rates", HeartRateIn),
    "hrv": ("hrv_samples", HRVSampleIn),
    "activity": ("activity_samples", ActivitySampleIn),
    "blood_oxygen": ("blood_oxygen_samples", BloodOxygenSampleIn),
    "body_temperature": ("body_temperature_samples", BodyTemperatureSampleIn),
    "respiratory_rate": ("respiratory_rate_samples", RespiratoryRateSampleIn),
    "ecg": ("ecg_records", ECGRecordIn),
    "noise_exposure": ("noise_exposure_samples", NoiseExposureSampleIn),
    "mindfulness": ("mindfulness_sessions", MindfulnessSessionIn),
    "workout": ("workout_records", WorkoutRecordIn),
}

# parser 中间 dict 的内部字段，喂 Pydantic 前剥离
_INTERNAL_FIELDS = {"_counter_key", "type", "is_in_bed", "is_asleep"}


def parse_xml_to_payloads(xml_path: str) -> Iterator[SyncPayload]:
    """
    解析 Apple Health XML 文件，分批 yield SyncPayload。

    :param xml_path: XML 文件路径（已从 ZIP 解压）
    :return: SyncPayload 迭代器，每个 payload 包含至多 BATCH_SIZE 条非睡眠记录，
             睡眠会话在最后一个 payload 中一次性输出
    """
    adapter = _PayloadAdapter()
    parser = create_parser(xml_path)

    for record in parser.parse():
        adapter.consume(record)
        if adapter.batch_count >= BATCH_SIZE:
            yield adapter.flush_batch()

    # 结束时输出剩余记录 + 聚合后的睡眠会话
    final_payload = adapter.flush_final()
    if final_payload is not None:
        yield final_payload

    logger.info(
        "Apple Health 解析完成: total=%d, skipped=%d, errors=%d",
        parser.stats.get("total_records", 0),
        parser.stats.get("skipped", 0),
        parser.stats.get("errors", 0),
    )


class _PayloadAdapter:
    """内部状态管理：缓冲记录、分批组装 SyncPayload"""

    def __init__(self) -> None:
        # 各类型缓冲：field_name -> list[Pydantic 实例]
        self._buffers: dict[str, list[Any]] = {}
        self._sleep_stages: list[dict[str, Any]] = []
        self._batch_count: int = 0
        # 当前 batch 的时间范围
        self._min_time: datetime | None = None
        self._max_time: datetime | None = None

    @property
    def batch_count(self) -> int:
        return self._batch_count

    def consume(self, record: dict[str, Any]) -> None:
        """消费一条 parser 产出的中间 dict"""
        record_type = record.get("type")
        if record_type is None:
            return

        # sleep_stage 特殊处理：缓冲，最后聚合
        if record_type == "sleep_stage":
            self._sleep_stages.append(record)
            return

        mapping = RECORD_TYPE_MAP.get(record_type)
        if mapping is None:
            logger.debug("未知的记录类型，跳过: %s", record_type)
            return

        field_name, model_cls = mapping
        cleaned = _clean_record(record)
        try:
            instance = model_cls(**cleaned)
        except Exception as e:
            logger.warning("构造 %s 失败: %s | data=%s", model_cls.__name__, e, cleaned)
            return

        self._buffers.setdefault(field_name, []).append(instance)
        self._batch_count += 1
        self._update_time_range(cleaned.get("recorded_at"))

    def flush_batch(self) -> SyncPayload:
        """输出当前缓冲并重置（不含睡眠，睡眠在 flush_final 输出）"""
        payload = self._build_payload(self._buffers, include_sleep=False)
        self._buffers = {}
        self._batch_count = 0
        self._min_time = None
        self._max_time = None
        return payload

    def flush_final(self) -> SyncPayload | None:
        """输出剩余记录 + 聚合后的睡眠会话；无内容时返回 None"""
        has_remaining = bool(self._buffers) or self._batch_count > 0
        sleep_sessions = aggregate_sleep_sessions(self._sleep_stages)
        self._sleep_stages = []

        if not has_remaining and not sleep_sessions:
            return None

        buffers = dict(self._buffers)
        if sleep_sessions:
            buffers["sleep_sessions"] = [
                SleepSessionIn(**s) for s in sleep_sessions
            ]
            for s in sleep_sessions:
                self._update_time_range(s.get("recorded_at"))

        self._buffers = {}
        self._batch_count = 0
        return self._build_payload(buffers, include_sleep=True)

    def _build_payload(
        self, buffers: dict[str, list[Any]], include_sleep: bool
    ) -> SyncPayload:
        """从缓冲字典构建 SyncPayload"""
        # 确保所有字段都存在
        kwargs: dict[str, Any] = {
            "heart_rates": [],
            "hrv_samples": [],
            "activity_samples": [],
            "sleep_sessions": [] if include_sleep else [],
            "blood_oxygen_samples": [],
            "body_temperature_samples": [],
            "workout_records": [],
            "ecg_records": [],
            "respiratory_rate_samples": [],
            "noise_exposure_samples": [],
            "mindfulness_sessions": [],
        }
        kwargs.update(buffers)

        # sync_window：用当前 batch 的时间范围
        if self._min_time and self._max_time:
            kwargs["sync_window"] = SyncWindow(
                start=self._min_time, end=self._max_time
            )
        else:
            # 兜底：无记录时（理论上不应发生）
            now = datetime.now()
            kwargs["sync_window"] = SyncWindow(start=now, end=now)

        kwargs["device_info"] = DeviceInfo(
            model="Apple Health Export",
            app_version="vendor-parser",
        )
        return SyncPayload(**kwargs)

    def _update_time_range(self, ts: Any) -> None:
        if ts is None:
            return
        if self._min_time is None or ts < self._min_time:
            self._min_time = ts
        if self._max_time is None or ts > self._max_time:
            self._max_time = ts


def _clean_record(record: dict[str, Any]) -> dict[str, Any]:
    """
    清理单条中间 dict：
    - 剥离内部标签字段
    - 为缺少 recorded_at 的记录补 recorded_at = start_time
    """
    cleaned = {k: v for k, v in record.items() if k not in _INTERNAL_FIELDS}

    # workout / mindfulness 的中间 dict 没有 recorded_at，补为 start_time
    if "recorded_at" not in cleaned and "start_time" in cleaned:
        cleaned["recorded_at"] = cleaned["start_time"]

    # workout 的 hr_zones：parser 产出为 [] 或 dict 列表，转成 WorkoutHRZoneIn
    if cleaned.get("hr_zones"):
        cleaned["hr_zones"] = [
            WorkoutHRZoneIn(**z) if isinstance(z, dict) else z
            for z in cleaned["hr_zones"]
        ]

    return cleaned
