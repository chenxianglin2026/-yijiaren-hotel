import sqlite3, random
from datetime import datetime, timedelta
today = datetime.now()

# === 伊家人 ===
c = sqlite3.connect('/home/ubuntu/yijiaren/code/backend/data/yijiaren.db')
cur = c.cursor()
hid = 1

# 设备
for i in range(20):
    rn = f"{(i%5)+1}0{random.randint(1,8):01d}"
    cur.execute("INSERT OR IGNORE INTO devices (device_id,name,device_type,hotel_id,room_number,status,battery,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (f'DEV-{i+1:04d}', f'智能设备{i+1}', random.choice(['lock','door_sensor','temp_sensor']),
         hid, rn, 'online', random.randint(60,98), today.isoformat()))
print(f"设备: {cur.rowcount}")

# 订单
for i in range(20):
    g = random.choice(['张三','李四','王五','赵六','陈七','周八'])
    cin = today + timedelta(days=random.randint(-7, 14))
    days = random.randint(1, 5)
    cur.execute("INSERT OR IGNORE INTO orders (order_no,user_id,hotel_id,room_id,room_count,checkin_date,checkout_date,nights,total_price,status,guest_name,guest_phone,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (f'ORD{random.randint(10000,99999)}', 2, hid, random.randint(1,5), 1,
         cin.strftime('%Y-%m-%d'), (cin+timedelta(days=days)).strftime('%Y-%m-%d'), days,
         random.choice([288,388,588,688])*days, random.choice(['confirmed','checked_in','completed']),
         g, f'138{random.randint(10000000,99999999)}', today.isoformat(), today.isoformat()))
print(f"订单: {cur.rowcount}")

# 清洗
for i in range(8):
    cur.execute("INSERT OR IGNORE INTO cleaning_tasks (hotel_id,room_number,task_type,status,created_at) VALUES (?,?,?,?,?)",
        (hid, f"10{random.randint(1,8)}", random.choice(['daily','checkout','deep']),
         random.choice(['pending','completed']), today.isoformat()))
print(f"清洗: {cur.rowcount}")

# 服务
for i in range(6):
    cur.execute("INSERT OR IGNORE INTO service_requests (user_id,hotel_id,room_number,request_type,description,priority,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (2, hid, f"10{random.randint(1,8)}", random.choice(['cleaning','maintenance','amenity']),
         random.choice(['需要补充洗漱用品','空调温度异常','需要加床']),
         random.choice(['normal','urgent']), random.choice(['pending','completed']), today.isoformat()))
print(f"服务: {cur.rowcount}")

c.commit()
c.close()

# === 公寓 ===
c2 = sqlite3.connect('/home/ubuntu/apartment/code/backend/data/apartment.db')
cur2 = c2.cursor()

for i in range(30):
    cur2.execute("INSERT OR IGNORE INTO bills (tenant_id,room_id,bill_type,amount,period_start,period_end,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (random.randint(1,4), random.randint(1,12), random.choice(['water','rent','property']),
         random.randint(50,2000), (today-timedelta(days=random.randint(1,90))).strftime('%Y-%m-%d'),
         today.strftime('%Y-%m-%d'), random.choice(['paid','paid','paid','unpaid']), today.isoformat()))
print(f"公寓账单: {cur2.rowcount}")

for i in range(15):
    cur2.execute("INSERT OR IGNORE INTO visitors (name,phone,room_id,purpose,visit_time,leave_time,status) VALUES (?,?,?,?,?,?,?)",
        (f'访客{i}', f'139{random.randint(10000000,99999999)}', random.randint(1,12),
         random.choice(['送快递','维修','探访']), today.isoformat(), today.isoformat(), 'completed'))
print(f"公寓访客: {cur2.rowcount}")

for i in range(8):
    cur2.execute("INSERT OR IGNORE INTO maintenance (tenant_id,room_id,title,description,priority,status,created_at) VALUES (?,?,?,?,?,?,?)",
        (random.randint(1,4), random.randint(1,12), random.choice(['水龙头漏水','空调不制冷','门锁故障','马桶堵塞','灯不亮']),
         '请尽快处理', random.choice(['high','medium','low']), random.choice(['pending','processing','completed']),
         (today-timedelta(days=random.randint(0,14))).isoformat()))
print(f"公寓报修: {cur2.rowcount}")

c2.commit()
c2.close()
print("✅ 虚拟数据注入完成")
