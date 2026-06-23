"""
Apple Health 解析集成端到端测试

验证全链路：parser → adapter → SyncPayload
覆盖：类型分派、单位转换、睡眠会话合并、recorded_at 补全、内部字段剥离、ECG metadata 提取。

运行：
    cd backend
    python -m pytest tests/test_apple_health.py -v
    # 或直接运行
    python tests/test_apple_health.py
"""
import os
from datetime import datetime

try:
    import pytest
except ImportError:
    # 无 pytest 时提供 stub，允许直接 python tests/test_apple_health.py 运行
    class _PytestStub:
        @staticmethod
        def approx(expected, **kwargs):
            abs_ = kwargs.get("abs", 0)
            rel = kwargs.get("rel", 1e-6)

            class _Approx:
                def __init__(self, v):
                    self.v = v

                def __eq__(self, other):
                    if abs_:
                        return abs(other - self.v) <= abs_
                    if self.v == 0:
                        return abs(other) <= rel
                    return abs(other - self.v) <= rel * abs(self.v)

                def __repr__(self):
                    return f"approx({self.v})"

            return _Approx(expected)

    pytest = _PytestStub()

approx = pytest.approx

from app.services.apple_health import detect_format
from app.services.apple_health.adapter import parse_xml_to_payloads
from app.services.apple_health.sleep_aggregator import aggregate_sleep_sessions

FIXTURE_XML = os.path.join(os.path.dirname(__file__), "fixtures", "sample_export.xml")


def _collect_payloads(xml_path: str = FIXTURE_XML):
    """解析样本 XML，收集所有 SyncPayload"""
    return list(parse_xml_to_payloads(xml_path))


# ------------------------------------------------------------------
# 格式检测
# ------------------------------------------------------------------

def test_detect_format_legacy():
    assert detect_format(FIXTURE_XML) == "legacy"


# ------------------------------------------------------------------
# adapter 产出 SyncPayload
# ------------------------------------------------------------------

def test_produces_single_payload():
    """样本数据量小（<5000），应产出 1 个 payload（含全部非睡眠 + 聚合睡眠）"""
    payloads = _collect_payloads()
    assert len(payloads) == 1


def test_payload_has_sync_window():
    payloads = _collect_payloads()
    payload = payloads[0]
    assert payload.sync_window.start is not None
    assert payload.sync_window.end is not None
    assert payload.sync_window.start <= payload.sync_window.end


# ------------------------------------------------------------------
# 心率
# ------------------------------------------------------------------

def test_heart_rate_fields():
    payloads = _collect_payloads()
    hr = payloads[0].heart_rates
    assert len(hr) == 2  # 普通心率 + 静息心率

    normal = next(h for h in hr if h.sample_uuid == "test-hr-001")
    assert normal.bpm == 72
    assert normal.measurement_type == "heart_rate"
    assert normal.source_device == "Apple Watch"
    assert normal.recorded_at is not None
    # 内部字段不应作为属性存在
    assert not hasattr(normal, "_counter_key")
    assert not hasattr(normal, "type")

    resting = next(h for h in hr if h.sample_uuid == "test-resting-hr-001")
    assert resting.bpm == 58
    assert resting.measurement_type == "resting_heart_rate"


# ------------------------------------------------------------------
# 活动 + 单位转换
# ------------------------------------------------------------------

def test_activity_types_and_unit_conversion():
    payloads = _collect_payloads()
    activities = payloads[0].activity_samples
    by_metric = {a.metric_type: a for a in activities}

    assert by_metric["steps"].value == 8432
    # 5.2 km → 5200 m
    assert by_metric["distance_meters"].value == pytest.approx(5200, abs=0.01)
    assert by_metric["active_energy_kcal"].value == 420
    assert by_metric["resting_energy_kcal"].value == 1800
    assert by_metric["stand_hours"].value == 8
    assert by_metric["flights_climbed"].value == 12
    assert by_metric["exercise_time"].value == 30


# ------------------------------------------------------------------
# HRV / 血氧 / 体温 / 呼吸 / 噪声
# ------------------------------------------------------------------

def test_hrv():
    payloads = _collect_payloads()
    hrv = payloads[0].hrv_samples
    assert len(hrv) == 1
    assert hrv[0].sdnn_ms == pytest.approx(42.5)
    assert hrv[0].sample_uuid == "test-hrv-001"


def test_blood_oxygen_fraction_to_percent():
    """血氧 0.98 (fraction) → 98.0 (percent)"""
    payloads = _collect_payloads()
    spo2 = payloads[0].blood_oxygen_samples
    assert len(spo2) == 1
    assert spo2[0].spo2_percent == pytest.approx(98.0)


def test_body_temperature():
    payloads = _collect_payloads()
    temp = payloads[0].body_temperature_samples
    assert len(temp) == 1
    assert temp[0].temperature_celsius == pytest.approx(36.8)


def test_respiratory_rate():
    payloads = _collect_payloads()
    rr = payloads[0].respiratory_rate_samples
    assert len(rr) == 1
    assert rr[0].breaths_per_minute == pytest.approx(16)


def test_noise_exposure():
    payloads = _collect_payloads()
    noise = payloads[0].noise_exposure_samples
    assert len(noise) == 1
    assert noise[0].decibels == pytest.approx(65)
    assert noise[0].duration_seconds == pytest.approx(1800)


# ------------------------------------------------------------------
# ECG（含 metadata 提取 average_heart_rate）
# ------------------------------------------------------------------

def test_ecg_metadata_extraction():
    payloads = _collect_payloads()
    ecg = payloads[0].ecg_records
    assert len(ecg) == 1
    assert ecg[0].classification == "sinus_rhythm"
    assert ecg[0].average_heart_rate == pytest.approx(72.0)
    assert ecg[0].sample_uuid == "test-ecg-001"


# ------------------------------------------------------------------
# 睡眠会话合并
# ------------------------------------------------------------------

def test_sleep_session_aggregation():
    """5 个睡眠阶段（同晚，间隔 <2h）应合并为 1 个会话"""
    payloads = _collect_payloads()
    sessions = payloads[0].sleep_sessions
    assert len(sessions) == 1

    session = sessions[0]
    # 会话 UUID 取首阶段（in_bed）的 UUID
    assert session.sample_uuid == "test-sleep-inbed-001"
    # 5 个阶段
    assert len(session.stages) == 5
    # start = 23:00, end = 次日 07:30
    assert session.start_time.hour == 23
    assert session.end_time.hour == 7
    assert session.end_time.minute == 30
    # 总时长 8.5h = 510 min
    assert session.total_duration_minutes == pytest.approx(510, abs=1)
    # in_bed 阶段时长 = 23:00-07:30 = 510 min
    assert session.in_bed_duration_minutes == pytest.approx(510, abs=1)
    # recorded_at 补全为 start_time
    assert session.recorded_at == session.start_time
    # 阶段值
    stage_names = {s.stage for s in session.stages}
    assert stage_names == {"in_bed", "core", "deep", "rem", "awake"}


def test_sleep_aggregator_empty():
    assert aggregate_sleep_sessions([]) == []


# ------------------------------------------------------------------
# recorded_at 补全（workout / mindfulness 的中间 dict 无 recorded_at）
# ------------------------------------------------------------------

def test_workout_recorded_at_backfilled():
    payloads = _collect_payloads()
    workouts = payloads[0].workout_records
    assert len(workouts) == 1

    w = workouts[0]
    assert w.workout_type == "running"
    assert w.duration_seconds == pytest.approx(1800)
    # distance 5.2 km → 5200 m
    assert w.distance_meters == pytest.approx(5200, abs=0.01)
    assert w.active_energy_kcal == pytest.approx(420)
    # recorded_at 应补为 start_time
    assert w.recorded_at == w.start_time
    assert w.recorded_at is not None


def test_mindfulness_recorded_at_backfilled():
    payloads = _collect_payloads()
    mind = payloads[0].mindfulness_sessions
    assert len(mind) == 1

    m = mind[0]
    assert m.duration_minutes == pytest.approx(15)
    # recorded_at 应补为 start_time
    assert m.recorded_at == m.start_time
    assert m.recorded_at is not None


# ------------------------------------------------------------------
# 内部字段剥离
# ------------------------------------------------------------------

def test_internal_fields_stripped():
    """所有 Pydantic 实例不应含 parser 内部标签字段"""
    payloads = _collect_payloads()
    payload = payloads[0]

    all_items = (
        payload.heart_rates + payload.hrv_samples + payload.activity_samples
        + payload.blood_oxygen_samples + payload.body_temperature_samples
        + payload.ecg_records + payload.respiratory_rate_samples
        + payload.noise_exposure_samples + payload.mindfulness_sessions
        + payload.workout_records + payload.sleep_sessions
    )
    for item in all_items:
        # Pydantic v2 实例不含未声明字段；检查 model_dump 无内部键
        dumped = item.model_dump()
        assert "_counter_key" not in dumped
        assert "type" not in dumped
        assert "is_in_bed" not in dumped
        assert "is_asleep" not in dumped


# ------------------------------------------------------------------
# 可直接运行
# ------------------------------------------------------------------

if __name__ == "__main__":
    # 不依赖 pytest 也能快速验证
    payloads = _collect_payloads()
    print(f"Payloads: {len(payloads)}")
    p = payloads[0]
    print(f"  heart_rates: {len(p.heart_rates)}")
    print(f"  hrv_samples: {len(p.hrv_samples)}")
    print(f"  activity_samples: {len(p.activity_samples)}")
    print(f"  sleep_sessions: {len(p.sleep_sessions)}")
    print(f"  blood_oxygen_samples: {len(p.blood_oxygen_samples)}")
    print(f"  body_temperature_samples: {len(p.body_temperature_samples)}")
    print(f"  workout_records: {len(p.workout_records)}")
    print(f"  ecg_records: {len(p.ecg_records)}")
    print(f"  respiratory_rate_samples: {len(p.respiratory_rate_samples)}")
    print(f"  noise_exposure_samples: {len(p.noise_exposure_samples)}")
    print(f"  mindfulness_sessions: {len(p.mindfulness_sessions)}")
    if p.sleep_sessions:
        s = p.sleep_sessions[0]
        print(f"  sleep session: stages={len(s.stages)} total={s.total_duration_minutes:.0f}min")
    print("OK")
