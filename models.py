from sqlalchemy import Column, Integer, String, DateTime
from database import Base
import datetime

class BossRecord(Base):
    # ⚠️ 這裡保持你原本的表單名稱 "boss_timers"，千萬不要改，不然舊資料會找不到！
    __tablename__ = "boss_timers"

    id = Column(Integer, primary_key=True, index=True)
    
    # 頻道
    channel = Column(Integer, nullable=False)
    
    # 王的名字
    boss_name = Column(String, nullable=False)

    # 👇 新增這個欄位：用來存 "7" 或 "7-1"
    # nullable=True 代表這個欄位可以是空的 (因為其他王不需要填這個)
    note = Column(String, nullable=True)
    
    # 擊殺時間
    kill_time = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 建立紀錄時間
    created_at = Column(DateTime, default=datetime.datetime.utcnow)