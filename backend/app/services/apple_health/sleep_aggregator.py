"""
睡眠会话合并算法

将散落的 sleep_stage 记录按时间聚合为 sleep_session。
算法 vendor 自外部仓库 AppleHealth-DB 的 importer.py（_flush_sleep_to_db / _create_sleep_session），
抽离为纯函数，不碰数据库。

规则：
    1. 按 start_time 排序所有阶段
    2. 相邻阶段间隔 > 2 小时则切分为新会话
    3. 每个会话：start = 首阶段.start_time, end = 末阶段.end_time
       total_duration_minutes = (end - start) / 60
       in_bed_duration_minutes = sum(阶段时长 where is_in_bed)；若为 0 则回退为总时长
       session 的 sample_uuid 取首阶段的 sample_uuid
"""
from datetime import timedelta
from typing import Any

SESSION_GAP_THRESHOLD = timedelta(hours=2)


def aggregate_sleep_sessions(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    将 sleep_stage dict 列表合并为 sleep_session dict 列表。

    :param stages: parser 产出的 sleep_stage 中间 dict 列表，每个含
                   sample_uuid / stage / start_time / end_time /
                   duration_minutes / source_device / is_in_bed / is_asleep
                   以及内部字段 _counter_key / type
    :return: sleep_session dict 列表，字段对齐 SyncHealth 的 SleepSessionIn：
             sample_uuid / source_device / recorded_at / start_time / end_time /
             total_duration_minutes / in_bed_duration_minutes / stages
             其中 stages 内每个 dict 对齐 SleepStageIn：
             stage / start_time / end_time / duration_minutes
    """
    if not stages:
        return []

    # 过滤掉时间缺失的阶段并按 start_time 排序
    valid_stages = [s for s in stages if s.get("start_time") and s.get("end_time")]
    if not valid_stages:
        return []

    sorted_stages = sorted(valid_stages, key=lambda x: x["start_time"])

    # 按 >2h 间隔分组
    sessions_stages: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []

    for stage in sorted_stages:
        if not current:
            current.append(stage)
            continue
        last_end = current[-1]["end_time"]
        this_start = stage["start_time"]
        if (this_start - last_end) > SESSION_GAP_THRESHOLD:
            sessions_stages.append(current)
            current = [stage]
        else:
            current.append(stage)

    if current:
        sessions_stages.append(current)

    # 聚合每个会话
    return [_build_session(s) for s in sessions_stages]


def _build_session(stages: list[dict[str, Any]]) -> dict[str, Any]:
    """根据一组睡眠阶段构建单个会话 dict（对齐 SleepSessionIn）"""
    start_time = stages[0]["start_time"]
    end_time = stages[-1]["end_time"]
    total_minutes = (end_time - start_time).total_seconds() / 60

    # 在床时长：所有 is_in_bed 阶段时长之和，为 0 则回退为总时长
    in_bed_minutes = sum(
        s.get("duration_minutes", 0) for s in stages if s.get("is_in_bed")
    )
    if in_bed_minutes == 0:
        in_bed_minutes = total_minutes

    # 会话 UUID 取首阶段 UUID
    session_uuid = stages[0]["sample_uuid"]

    # 构建对齐 SleepStageIn 的 stages 列表（剥掉内部字段）
    clean_stages = [
        {
            "stage": s["stage"],
            "start_time": s["start_time"],
            "end_time": s["end_time"],
            "duration_minutes": s.get("duration_minutes", 0),
        }
        for s in stages
    ]

    return {
        "sample_uuid": session_uuid,
        "source_device": stages[0].get("source_device", ""),
        # SleepSessionIn 继承 HealthSampleBase，recorded_at 必填，用会话开始时间补全
        "recorded_at": start_time,
        "start_time": start_time,
        "end_time": end_time,
        "total_duration_minutes": total_minutes,
        "in_bed_duration_minutes": in_bed_minutes,
        "stages": clean_stages,
    }
