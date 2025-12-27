from sqlalchemy import Column, Integer, String, DateTime
from database import Base
import datetime

class BossRecord(Base):
    __tablename__ = "boss_timers"

    id = Column(Integer, primary_key=True, index=True)
    
    # 頻道 (例如 1527)
    channel = Column(Integer, nullable=False)
    
    # 王的名字 (例如 "巴洛谷")
    boss_name = Column(String, nullable=False)
    
    # 擊殺時間 (存 UTC 時間，這是計算倒數的基準)
    kill_time = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 建立這筆紀錄的時間 (Log用)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)