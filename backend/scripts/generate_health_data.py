"""
SyncHealth 健康数据生成器
===========================
自动生成模拟健康数据并上传到后端 API

使用方法:
    1. 确保后端已启动: uvicorn app.main:app --reload --port 8000
    2. 运行脚本: python scripts/generate_health_data.py
    3. 脚本会自动注册/登录用户，生成7天的健康数据并上传

依赖安装:
    pip install requests
"""

import random
import uuid
import json
import sys
import io
from datetime import datetime, timedelta, timezone

import requests

# 修复 Windows GBK 编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ============== 配置 ==============
API_BASE_URL = "http://127.0.0.1:8001/api/v1"
EMAIL = "test@synchealth.com"
PASSWORD = "testpass123"
DISPLAY_NAME = "Test User"
DEVICE_ID = "mock-device-001"
DAYS_TO_GENERATE = 7


# ============== 工具函数 ==============
def generate_uuid() -> str:
    return str(uuid.uuid4())


def fmt(dt: datetime) -> str:
    """ISO 格式化，兼容 Pydantic"""
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00"


def rand_time(date: datetime, hour: int) -> datetime:
    return date.replace(
        hour=hour,
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
        microsecond=0,
    )


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def choice(items):
    return items[random.randint(0, len(items) - 1)]


# ============== 数据生成函数 ==============

def gen_heart_rates(d: datetime) -> list[dict]:
    recs = []
    for h in [6, 8, 10, 12, 14, 16, 18, 20, 22]:
        if random.random() > 0.75:
            bpm = clamp(70 + random.gauss(0, 8), 50, 150)
            if h in [7, 18]:
                bpm += random.randint(15, 35)
            bpm = round(bpm, 1)
            recs.append({
                "sample_uuid": generate_uuid(),
                "source_device": DEVICE_ID,
                "recorded_at": fmt(rand_time(d, h)),
                "bpm": bpm,
                "motion_context": choice(["sedentary", "active", "walking", None]),
                "measurement_type": "heart_rate",
            })

    # 静息心率 (清晨5点，bpm 55-68)
    if random.random() > 0.2:
        rhr = round(clamp(random.gauss(62, 4), 50, 72), 1)
        recs.append({
            "sample_uuid": generate_uuid(),
            "source_device": DEVICE_ID,
            "recorded_at": fmt(rand_time(d, 5)),
            "bpm": rhr,
            "motion_context": "resting",
            "measurement_type": "resting_heart_rate",
        })
    return recs


def gen_hrv(d: datetime) -> list[dict]:
    recs = []
    for h in [7, 12, 22]:
        if random.random() > 0.5:
            recs.append({
                "sample_uuid": generate_uuid(),
                "source_device": DEVICE_ID,
                "recorded_at": fmt(rand_time(d, h)),
                "sdnn_ms": round(clamp(random.gauss(45, 15), 15, 120), 1),
            })
    return recs


def gen_activity(d: datetime) -> list[dict]:
    recs = []
    steps = random.randint(4000, 13000)
    t = d.replace(hour=23, minute=59)
    ts = fmt(t)

    metrics = [
        ("steps", float(steps), None),
        ("distance_meters", round(steps * 0.7, 1), None),
        ("active_energy_kcal", float(round(1500 + steps * 0.08 + random.uniform(-100, 100))), None),
        ("stand_hours", float(random.randint(8, 14)), None),
        ("exercise_time", float(m := random.randint(10, 90)), float(m * 60)),
        ("flights_climbed", float(random.randint(3, 15)), None),
    ]
    for mtype, val, dur in metrics:
        recs.append({
            "sample_uuid": generate_uuid(), "source_device": DEVICE_ID,
            "recorded_at": ts, "metric_type": mtype, "value": val,
            "duration_seconds": dur,
        })
    return recs


def gen_sleep(d: datetime) -> list[dict]:
    sh = random.choice([22, 23])
    sm = choice([0, 15, 30, 45])
    start = (d if sh >= 22 else d - timedelta(days=1)).replace(hour=sh, minute=sm, second=0, microsecond=0)
    total_min = random.randint(360, 510)
    end = start + timedelta(minutes=total_min)
    in_bed = total_min + random.randint(10, 40)

    # stages
    patterns = [
        ("awake", 5, 15), ("core", 20, 40), ("deep", 25, 45),
        ("core", 35, 60), ("rem", 12, 28), ("core", 22, 42),
        ("rem", 18, 33), ("core", 28, 48), ("deep", 12, 26),
        ("core", 30, 52), ("rem", 14, 36), ("awake", 6, 14),
    ]
    stages = []
    cur, remain = start, total_min
    for sn, mn, mx in patterns:
        if remain < 8:
            break
        dur = min(random.randint(mn, mx), remain)
        smap = {"awake": "awake", "light": "core"}
        stages.append({
            "stage": smap.get(sn, sn) if sn in smap else sn,
            "start_time": fmt(cur), "end_time": fmt(cur + timedelta(minutes=dur)),
            "duration_minutes": round(dur, 1),
        })
        cur += timedelta(minutes=dur)
        remain -= dur

    return [{
        "sample_uuid": generate_uuid(), "source_device": DEVICE_ID,
        "recorded_at": fmt(end), "start_time": fmt(start), "end_time": fmt(end),
        "total_duration_minutes": round(total_min, 1),
        "in_bed_duration_minutes": round(in_bed, 1), "stages": stages,
    }]


def gen_blood_oxygen(d: datetime) -> list[dict]:
    recs = []
    for h in [8, 14, 22]:
        if random.random() > 0.4:
            recs.append({
                "sample_uuid": generate_uuid(), "source_device": DEVICE_ID,
                "recorded_at": fmt(rand_time(d, h)),
                "spo2_percent": round(clamp(random.gauss(97.5, 1.2), 94, 100), 1),
                "measurement_condition": choice(["resting", "sleep", None]),
            })
    return recs


def gen_body_temp(d: datetime) -> list[dict]:
    recs = []
    for h in [7, 13, 21]:
        if random.random() > 0.4:
            base = {True: 36.5, False: (36.7 if h < 18 else 36.4)}[h < 12]
            recs.append({
                "sample_uuid": generate_uuid(), "source_device": DEVICE_ID,
                "recorded_at": fmt(rand_time(d, h)),
                "temperature_celsius": round(clamp(random.gauss(base, 0.25), 35.5, 38.0), 2),
                "measurement_location": choice(["wrist", "forehead", "oral"]),
            })
    return recs


def gen_workouts(d: datetime) -> list[dict]:
    if random.random() > 0.55:
        return []
    wtypes = [
        ("running", 1800, 4800, 3.0, 10.0, 250, 600),
        ("cycling", 2400, 5400, 8.0, 30.0, 200, 550),
        ("strength_training", 1800, 3600, None, None, 150, 400),
        ("swimming", 1800, 4200, 0.8, 3.0, 200, 500),
        ("yoga", 2700, 5400, None, None, 100, 250),
        ("hiit", 1200, 2400, None, None, 200, 450),
    ]
    wt, mins, maxs, mdst, mdx, mcmin, mcmax = choice(wtypes)
    dur = random.randint(mins, maxs)
    sh = choice([6, 7, 17, 18, 19])
    st = rand_time(d, sh); et = st + timedelta(seconds=dur)
    ahr = random.randint(110, 165)
    r = {
        "sample_uuid": generate_uuid(), "source_device": DEVICE_ID,
        "recorded_at": fmt(et), "workout_type": wt,
        "start_time": fmt(st), "end_time": fmt(et),
        "duration_seconds": float(dur),
        "total_energy_kcal": float(random.randint(mcmin, mcmax)),
        "active_energy_kcal": float(random.randint(int(mcmin * 0.85), int(mcmax * 0.95))),
        "avg_heart_rate": float(ahr),
        "max_heart_rate": float(ahr + random.randint(15, 35)),
        "min_heart_rate": float(max(ahr - random.randint(25, 45), 50)),
    }
    if mdst is not None:
        r["distance_meters"] = round(random.uniform(mdst, mdx) * 1000, 1)
    return [r]


def gen_ecg(d: datetime) -> list[dict]:
    if random.random() > 0.3:
        return []
    return [{
        "sample_uuid": generate_uuid(), "source_device": DEVICE_ID,
        "recorded_at": fmt(rand_time(d, choice([9, 10, 11]))),
        "classification": choice(["sinus_rhythm"] * 15 + ["high_heart_rate"]),
        "average_heart_rate": round(clamp(random.gauss(72, 10), 50, 120), 1),
        "symptoms_status": None, "voltage_measurements": None,
    }]


def gen_resp_rate(d: datetime) -> list[dict]:
    recs = []
    for h in [8, 14, 22]:
        if random.random() > 0.4:
            base = 16 if h in [8, 22] else 18
            recs.append({
                "sample_uuid": generate_uuid(), "source_device": DEVICE_ID,
                "recorded_at": fmt(rand_time(d, h)),
                "breaths_per_minute": round(clamp(random.gauss(base, 2), 10, 28), 1),
            })
    return recs


def gen_noise(d: datetime) -> list[dict]:
    recs = []
    for h in range(8, 22, 3):
        if random.random() > 0.3:
            db = 55 if 9 <= h <= 17 else 40
            recs.append({
                "sample_uuid": generate_uuid(), "source_device": DEVICE_ID,
                "recorded_at": fmt(rand_time(d, h)),
                "decibels": round(clamp(random.gauss(db, 10), 30, 95), 1),
                "duration_seconds": float(random.randint(1800, 7200)),
            })
    return recs


def gen_mindfulness(d: datetime) -> list[dict]:
    if random.random() > 0.4:
        return []
    dur = choice([5, 10, 15, 20]); h = choice([7, 8, 21, 22])
    st = rand_time(d, h)
    return [{
        "sample_uuid": generate_uuid(), "source_device": DEVICE_ID,
        "recorded_at": fmt(st), "start_time": fmt(st),
        "end_time": fmt(st + timedelta(minutes=dur)), "duration_minutes": float(dur),
    }]


# ============== 主逻辑 ==============

def get_token(sess: requests.Session) -> str:
    print(f"\n{'='*50}")
    print("Step 1: Auth")
    print(f"{'='*50}")

    reg = sess.post(f"{API_BASE_URL}/auth/register", json={
        "email": EMAIL, "password": PASSWORD, "display_name": DISPLAY_NAME,
    })
    if reg.status_code == 201:
        print(f"OK Registered: {EMAIL}")
    elif reg.status_code in (400, 200):
        print("INFO User exists, logging in...")
    else:
        print(f"WARN Register: {reg.status_code} - {reg.text[:80]}")

    login = sess.post(f"{API_BASE_URL}/auth/login", json={
        "email": EMAIL, "password": PASSWORD,
    })
    if login.status_code != 200:
        raise Exception(f"Login failed: {login.status_code} - {login.text}")
    token = login.json().get("access_token")
    print("OK Token acquired")
    return token


def upload(sess, token):
    hdrs = {"Authorization": f"Bearer {token}"}
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    totals = {}
    gens = {
        "heart_rates": gen_heart_rates, "hrv_samples": gen_hrv,
        "activity_samples": gen_activity, "sleep_sessions": gen_sleep,
        "blood_oxygen_samples": gen_blood_oxygen, "body_temperature_samples": gen_body_temp,
        "workout_records": gen_workouts, "ecg_records": gen_ecg,
        "respiratory_rate_samples": gen_resp_rate, "noise_exposure_samples": gen_noise,
        "mindfulness_sessions": gen_mindfulness,
    }

    print(f"\n{'='*50}")
    print(f"Step 2: Generate {DAYS_TO_GENERATE} days data")
    print(f"{'='*50}")

    for offset in range(DAYS_TO_GENERATE):
        td = today - timedelta(days=offset)
        ds = td.strftime("%Y-%m-%d (%A)")
        print(f"\n  Generating {ds}...")

        payload = {
            "device_info": {
                "model": "MockDevice Pro",
                "os_version": f"{random.randint(14, 17)}.{random.randint(0, 5)}",
                "app_version": f"{random.randint(1, 3)}.{random.randint(0, 9)}",
            },
            "sync_window": {
                "start": fmt(td - timedelta(hours=2)),
                "end": fmt(td + timedelta(hours=26)),
            },
        }
        for key, fn in gens.items():
            payload[key] = fn(td)
            totals[key] = totals.get(key, 0) + len(payload[key])

        resp = sess.post(f"{API_BASE_URL}/sync/upload", headers=hdrs, json=payload)
        if resp.status_code in (200, 201):
            ins = resp.json().get("records_inserted", "?")
            print(f"   OK Uploaded | inserted={ins}")
        else:
            print(f"   FAIL ({resp.status_code}): {resp.text[:120]}")

    print(f"\n{'='*50}")
    print("Summary")
    print(f"{'='*50}")
    grand = 0
    for k, v in totals.items():
        dn = k.replace("_samples","").replace("_records","").replace("_sessions","")
        print(f"   {dn:<25}: {v:>4}")
        grand += v
    print(f"\n   Total: {grand} records")


def verify(sess, token):
    hdrs = {"Authorization": f"Bearer {token}"}
    eps = [
        ("/health/heart-rate?size=5", "Heart Rate"),
        ("/health/activity?size=5", "Activity"),
        ("/health/sleep?size=3", "Sleep"),
        ("/dashboard/summary", "Dashboard Summary"),
        ("/dashboard/trends?days=7", "Trends"),
        # ("/dashboard/health-score", "Health Score"),  # may need more data
    ]

    print(f"\n{'='*50}")
    print("Step 3: Verify")
    print(f"{'='*50}")

    for ep, desc in eps:
        try:
            r = sess.get(f"{API_BASE_URL}{ep}", headers=hdrs)
            if r.status_code == 200:
                d = r.json()
                if isinstance(d, dict):
                    if "items" in d:
                        print(f"   OK {desc:<20}: {len(d['items'])} items (total={d.get('total','?')})")
                    elif "data" in d and isinstance(d["data"], list):
                        print(f"   OK {desc:<20}: {len(d['data'])} records")
                    else:
                        preview = json.dumps(d, ensure_ascii=False)[:70]
                        print(f"   OK {desc:<20}: {preview}...")
                else:
                    print(f"   OK {desc:<20}: response ok")
            else:
                print(f"   WARN {desc:<20}: HTTP {r.status_code}")
        except Exception as e:
            print(f"   FAIL {desc:<20}: {e}")


def main():
    print("=" * 50)
    print("  SyncHealth Data Generator")
    print("=" * 50)
    print(f"Server : {API_BASE_URL}")
    print(f"Days   : {DAYS_TO_GENERATE}")
    print(f"Account: {EMAIL}")

    try:
        s = requests.Session()
        tk = get_token(s)
        upload(s, tk)
        verify(s, tk)
        print(f"\n{'='*50}")
        print("Done! Open frontend at http://localhost:5173")
        print(f"{'='*50}\n")
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    main()
