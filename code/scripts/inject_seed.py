import sqlite3, hashlib, time, random
from datetime import datetime, timedelta

DB = '/home/ubuntu/yijiaren/code/backend/data/yijiaren.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

# ── 伊家酒店种子数据 ──
print("=== 伊家人酒店 ===")

# 1. 房间类型
room_types = [
    ('标准大床房', 'standard_king', 288, '30平米，1.8m大床，独立卫浴'),
    ('豪华双床房', 'deluxe_twin', 388, '40平米，双1.5m床，智能马桶'),
    ('商务套房', 'business_suite', 588, '55平米，会客区+卧室，浴缸'),
    ('家庭套房', 'family_suite', 688, '65平米，两室一厅，儿童乐园'),
]
for name, code, price, desc in room_types:
    c.execute("INSERT OR IGNORE INTO room_types (name, code, price_per_night, description) VALUES (?,?,?,?)",
              (name, code, price, desc))

# 2. 房间 (5层, 每层10间)
floors = ['1F','2F','3F','5F','6F']  # 4F不吉利跳过
rooms_per_floor = 10
rtype_codes = ['standard_king','standard_king','standard_king','standard_king','deluxe_twin',
               'deluxe_twin','deluxe_twin','business_suite','business_suite','family_suite']

room_id = 0
for fi, floor in enumerate(floors):
    for ri in range(rooms_per_floor):
        room_id += 1
        num = f"{fi+1}0{ri+1:01d}" if ri < 9 else f"{fi+1}{ri+1}"
        rtype = rtype_codes[ri]
        status = random.choice(['vacant','vacant','vacant','occupied','occupied','cleaning'])
        c.execute("""INSERT OR IGNORE INTO rooms (id, number, floor, room_type, status, price_per_night)
                     VALUES (?,?,?,?,?, (SELECT price_per_night FROM room_types WHERE code=?))""",
                  (room_id, num, floor, rtype, status, rtype))
c.execute("SELECT COUNT(*) FROM rooms")
print(f"  房间: {c.fetchone()[0]} 间")

# 3. 预定数据 (最近7天 + 未来7天)
guests = [('张三','13800001111'),('李四','13800002222'),('王五','13800003333'),
          ('赵六','13800004444'),('陈七','13800005555'),('周八','13800006666')]
today = datetime.now()
for i in range(20):
    guest = random.choice(guests)
    checkin = today + timedelta(days=random.randint(-7, 7))
    checkout = checkin + timedelta(days=random.randint(1, 5))
    c.execute("""INSERT OR IGNORE INTO bookings (guest_name, guest_phone, room_id, check_in, check_out, 
                 total_price, status, source) VALUES (?,?,?,?,?,
                 (SELECT price_per_night FROM rooms r LEFT JOIN room_types rt ON r.room_type=rt.code WHERE r.id=?) * ?,
                 ?, '小程序')""",
              (guest[0], guest[1], random.randint(1,50), checkin.strftime('%Y-%m-%d'),
               checkout.strftime('%Y-%m-%d'), random.randint(1,50), (checkout-checkin).days,
               random.choice(['confirmed','checked_in','completed'])))
c.execute("SELECT COUNT(*) FROM bookings")
print(f"  预定: {c.fetchone()[0]} 单")

# 4. 门锁数据
for rid in range(1, 51):
    c.execute("""INSERT OR IGNORE INTO door_locks (room_id, lock_id, battery, status, online)
                 VALUES (?,?,?,?,?)""",
              (rid, f'LOCK-{rid:03d}', random.randint(60,100), 
               random.choice(['normal','normal','normal','low_battery']),
               random.choice([1,1,1,1,1,0])))
c.execute("SELECT COUNT(*) FROM door_locks")
print(f"  门锁: {c.fetchone()[0]} 个")

conn.commit()

# ── 公寓种子数据 ──
print("\n=== 公寓系统 ===")
DB2 = '/home/ubuntu/apartment/code/backend/data/apartment.db'
conn2 = sqlite3.connect(DB2)
c2 = conn2.cursor()

# 5. 账单
tenant_ids = [1,2,3,4]
for i in range(30):
    c2.execute("""INSERT OR IGNORE INTO bills (tenant_id, room_id, bill_type, amount, period_start, 
                  period_end, status, created_at) VALUES (?,?,?,?,?,?,?,?)""",
               (random.choice(tenant_ids), random.randint(1,12), 
                random.choice(['water','rent','property_fee']),
                random.randint(50, 2000),
                (today - timedelta(days=random.randint(1,90))).strftime('%Y-%m-%d'),
                today.strftime('%Y-%m-%d'),
                random.choice(['paid','paid','paid','unpaid']),
                today.strftime('%Y-%m-%d %H:%M:%S')))
c2.execute("SELECT COUNT(*) FROM bills")
print(f"  账单: {c2.fetchone()[0]} 条")

# 6. 访客记录
visitor_names = ['快递员小王','外卖骑手','维修师傅老张','朋友小刘','亲戚阿姨']
for i in range(15):
    c2.execute("""INSERT OR IGNORE INTO visitors (name, phone, room_id, purpose, visit_time, 
                  leave_time, status) VALUES (?,?,?,?,?,?,?)""",
               (random.choice(visitor_names), f'139{random.randint(10000000,99999999)}',
                random.randint(1,12), random.choice(['送快递','维修','探访','送货']),
                (today - timedelta(days=random.randint(0,7), hours=random.randint(8,20))).strftime('%Y-%m-%d %H:%M'),
                (today - timedelta(days=random.randint(0,7), hours=random.randint(8,20))).strftime('%Y-%m-%d %H:%M'),
                random.choice(['completed','completed','cancelled'])))
c2.execute("SELECT COUNT(*) FROM visitors")
print(f"  访客: {c2.fetchone()[0]} 条")

# 7. 报修
for i in range(8):
    c2.execute("""INSERT OR IGNORE INTO maintenance (tenant_id, room_id, title, description, 
                  priority, status, created_at) VALUES (?,?,?,?,?,?,?)""",
               (random.choice(tenant_ids), random.randint(1,12),
                random.choice(['水龙头漏水','空调不制冷','门锁故障','马桶堵塞','灯不亮']),
                random.choice(['需要尽快处理','不影响使用，可择日维修','紧急']),
                random.choice(['high','medium','low']),
                random.choice(['pending','processing','completed','pending']),
                (today - timedelta(days=random.randint(0,14))).strftime('%Y-%m-%d %H:%M')))
c2.execute("SELECT COUNT(*) FROM maintenance")
print(f"  报修: {c2.fetchone()[0]} 条")

conn2.commit()
conn.close()
conn2.close()
print("\n✅ 虚拟数据全部注入完成")
