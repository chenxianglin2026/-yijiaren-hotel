import sqlite3, random
from datetime import datetime, timedelta
today = datetime.now()

# === 伊家人 ===
db = '/home/ubuntu/yijiaren/code/backend/data/yijiaren.db'
cur = sqlite3.connect(db).cursor()
hid = 1

# 设备
for i in range(1, 21):
    rn = f"{(i%5)+1}0{random.randint(1,8):01d}"
    cur.execute("INSERT OR IGNORE INTO devices (device_id,name,device_type,hotel_id,room_number,status,battery,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (f'DEV-{i:04d}', f'智能设备{i}', random.choice(['lock','door_sensor','temp_sensor']), hid, rn,
         'online', random.randint(60,98), today.isoformat()))
cur.execute("SELECT COUNT(*) FROM devices")
print(f"伊家设备: {cur.fetchone()[0]} 个")

# 清洗任务
for i in range(8):
    cur.execute("INSERT OR IGNORE INTO cleaning_tasks (hotel_id, room_number, status, assigned_to, created_at) VALUES (?,?,?,?,?)",
        (hid, f"10{random.randint(1,8)}", random.choice(['pending','completed','pending']), f'保洁{random.randint(1,5)}号', today.isoformat()))
cur.execute("SELECT COUNT(*) FROM cleaning_tasks")
print(f"伊家清洗: {cur.fetchone()[0]} 条")

# 服务请求
for i in range(6):
    cur.execute("INSERT OR IGNORE INTO service_requests (hotel_id, room_number, request_type, description, status, created_at) VALUES (?,?,?,?,?,?)",
        (hid, f"10{random.randint(1,8)}", random.choice(['cleaning','maintenance','amenity']), 
         random.choice(['需要补充洗漱用品','空调温度异常','需要加床']), random.choice(['pending','completed']), today.isoformat()))
cur.execute("SELECT COUNT(*) FROM service_requests")
print(f"伊家服务: {cur.fetchone()[0]} 条")

cur.connection.commit()
cur.connection.close()

# === 公寓 ===
db2 = '/home/ubuntu/apartment/code/backend/data/apartment.db'
cur2 = sqlite3.connect(db2).cursor()

for i in range(30):
    cur2.execute("INSERT OR IGNORE INTO bills (tenant_id,room_id,bill_type,amount,period_start,period_end,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (random.randint(1,4), random.randint(1,12), random.choice(['water','rent','property']),
         random.randint(50,2000), (today-timedelta(days=random.randint(1,90))).strftime('%Y-%m-%d'),
         today.strftime('%Y-%m-%d'), random.choice(['paid','paid','paid','unpaid']), today.isoformat()))
cur2.execute("SELECT COUNT(*) FROM bills")
print(f"公寓账单: {cur2.fetchone()[0]} 条")

for i in range(15):
    cur2.execute("INSERT OR IGNORE INTO visitors (name,phone,room_id,purpose,visit_time,leave_time,status) VALUES (?,?,?,?,?,?,?)",
        (f'访客{i}', f'139{random.randint(10000000,99999999)}', random.randint(1,12),
         random.choice(['送快递','维修','探访']), today.isoformat(), today.isoformat(), 'completed'))
cur2.execute("SELECT COUNT(*) FROM visitors")
print(f"公寓访客: {cur2.fetchone()[0]} 条")

issues = ['水龙头漏水','空调不制冷','门锁故障','马桶堵塞','灯不亮']
for i in range(8):
    cur2.execute("INSERT OR IGNORE INTO maintenance (tenant_id,room_id,title,description,priority,status,created_at) VALUES (?,?,?,?,?,?,?)",
        (random.randint(1,4), random.randint(1,12), random.choice(issues), '请尽快处理',
         random.choice(['high','medium','low']), random.choice(['pending','processing','completed']),
         (today-timedelta(days=random.randint(0,14))).isoformat()))
cur2.execute("SELECT COUNT(*) FROM maintenance")
print(f"公寓报修: {cur2.fetchone()[0]} 条")

cur2.connection.commit()
cur2.connection.close()
print("\n✅ 完成")
