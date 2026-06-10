"""Reset database for fresh testing"""
import os

db_path = os.path.join(os.path.dirname(__file__), "data", "yijiaren.db")
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted: {db_path}")
else:
    print("DB already removed")
