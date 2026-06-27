"""检查 backend 数据库中的数据量"""
import sqlite3
import sys
sys.path.insert(0, ".")

db_path = "data/synchealth.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 列出所有表
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("数据库表:")
for t in tables:
    print(f"  {t[0]}")

print()

# 检查关键表的数据量
key_tables = [
    "heart_rates", "sleep_sessions", "activity_samples", 
    "workout_records", "blood_oxygen_samples", "body_temperature_samples",
    "respiratory_rate_samples", "hrv_samples",
]

print("数据量统计:")
for t in key_tables:
    try:
        cnt = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        # 检查 user_id 分布
        try:
            users = c.execute(f"SELECT DISTINCT user_id FROM {t}").fetchall()
            user_ids = [u[0] for u in users]
        except:
            user_ids = []
        # 检查最新数据时间
        try:
            latest = c.execute(f"SELECT MAX(recorded_at) FROM {t}").fetchone()[0]
        except:
            latest = "?"
        print(f"  {t}: {cnt} 行 | user_ids: {user_ids} | 最新: {latest}")
    except Exception as e:
        print(f"  {t}: 错误 - {e}")

print()

# 检查 heart_rates 的 measurement_type 分布
print("heart_rates 的 measurement_type 分布:")
try:
    rows = c.execute("SELECT measurement_type, COUNT(*) FROM heart_rates GROUP BY measurement_type").fetchall()
    for r in rows:
        print(f"  {r[0]}: {r[1]}")
except Exception as e:
    print(f"  错误: {e}")

# 检查 activity_samples 的 metric_type 分布
print("\nactivity_samples 的 metric_type 分布:")
try:
    rows = c.execute("SELECT metric_type, COUNT(*) FROM activity_samples GROUP BY metric_type").fetchall()
    for r in rows:
        print(f"  {r[0]}: {r[1]}")
except Exception as e:
    print(f"  错误: {e}")

# 检查 MCP 查询用的 user_id
print("\n=== MCP 查询模拟 (user_id=1) ===")
for table, time_col in [("heart_rates", "recorded_at"), ("sleep_sessions", "recorded_at"), ("activity_samples", "recorded_at"), ("workout_records", "recorded_at")]:
    try:
        cnt = c.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id = 1").fetchone()[0]
        print(f"  {table} WHERE user_id=1: {cnt} 行")
    except Exception as e:
        print(f"  {table}: {e}")

conn.close()
