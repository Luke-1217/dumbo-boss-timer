from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import math
# 👇 1. 新增這個 import，為了執行 SQL 指令
from sqlalchemy import text 

# 引入我們自己寫的檔案
from database import engine, SessionLocal
import models
import game_config

# 1. 建立資料庫表格
models.Base.metadata.create_all(bind=engine)

# 👇 2. 【新增區塊】自動檢查並升級資料庫 (幫你加 note 欄位)
with engine.connect() as conn:
    try:
        # 試著讀取 boss_timers 表格的 note 欄位
        conn.execute(text("SELECT note FROM boss_timers LIMIT 1"))
    except:
        print("⚡ 正在自動升級資料庫，新增 note 欄位...")
        # 如果失敗 (代表沒這欄位)，就自動加上去
        conn.execute(text("ALTER TABLE boss_timers ADD COLUMN note VARCHAR"))
        conn.commit()

app = FastAPI()

# 2. 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class BossRecordCreate(BaseModel):
    boss_name: str
    channel: int
    # 👇 3. 【新增欄位】允許前端傳送 note (7 或 7-1)
    note: str | None = None

# --- API 區域 ---

@app.get("/")
def read_root():
    return {"message": "DUMBO Boss Timer API is Running! ⏰"}

# 🔥 功能 A: 新增擊殺紀錄
@app.post("/bosses")
def create_boss_record(record: BossRecordCreate, db: Session = Depends(get_db)):
    if record.boss_name not in game_config.VALID_BOSS_NAMES:
        raise HTTPException(status_code=400, detail=f"找不到這隻王: {record.boss_name}")

    new_record = models.BossRecord(
        boss_name=record.boss_name,
        channel=record.channel,
        # 👇 4. 【新增寫入】把 note 存進資料庫
        note=record.note,
        kill_time=datetime.utcnow()
    )
    
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return {"status": "success", "data": new_record}

# 📋 功能 B: 查詢所有王的倒數狀態
@app.get("/bosses")
def get_all_timers(db: Session = Depends(get_db)):
    records = db.query(models.BossRecord).all()
    result_list = []
    
    now = datetime.utcnow()
    
    for record in records:
        settings = game_config.BOSS_SETTINGS.get(record.boss_name)
        if not settings:
            continue 
            
        elapsed_time = now - record.kill_time
        elapsed_mins = elapsed_time.total_seconds() / 60
        
        min_spawn = settings['min_mins']
        max_spawn = settings['max_mins']
        mins_until_spawn = min_spawn - elapsed_mins
        mins_until_max = max_spawn - elapsed_mins
        
        status = "unknown"
        status_color = "gray"
        overdue_mins = 0
        should_delete = False

        # --- 統一邏輯：所有卡片 (包含維修卡) 都跑一樣的流程 ---

        if elapsed_mins < min_spawn:
            # 🔵 藍燈: 還沒煮熟 (重生中)
            status = f"⏳ 重生中 (還剩 {int(mins_until_spawn)} 分)"
            status_color = "blue"
            
        elif elapsed_mins < max_spawn:
            # 🟠 橘燈: 進入保底區間 (可能出生)
            status = f"⚠️ 可能出生 (保底剩 {int(mins_until_max)} 分)"
            status_color = "orange"
            
        else:
            # 🔴 紅燈: 超過保底時間 (已出生)
            overdue_mins = elapsed_mins - max_spawn
            status = f"🔥 已出生 (+{int(overdue_mins)} 分)"
            status_color = "red"
            
            # 💀 自動刪除機制：180 分鐘後刪除
            if overdue_mins >= 180:
                should_delete = True

        # --- 如果需要刪除就執行，否則加入列表 ---
        if should_delete:
            db.delete(record)
            db.commit()
            continue 

        result_list.append({
            "id": record.id,
            "boss_name": record.boss_name,
            "img": settings['img'],
            "channel": record.channel,
            # 👇 5. 【新增回傳】把 note 傳給前端顯示
            "note": record.note, 
            "status": status,
            "color": status_color,
            "kill_time": record.kill_time,
            "min_mins": min_spawn,
            "max_mins": max_spawn,
            "sort_score": mins_until_max 
        })
    
    # 排序：快要出的排前面
    result_list.sort(key=lambda x: x['sort_score'])
    return result_list

# 🗑️ 功能 C: 刪除紀錄
@app.delete("/bosses/{boss_id}")
def delete_boss(boss_id: int, db: Session = Depends(get_db)):
    record = db.query(models.BossRecord).filter(models.BossRecord.id == boss_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="找不到這筆資料")
    
    db.delete(record)
    db.commit()
    return {"status": "success", "message": "刪除成功"}

# 🔄 功能 D: 重置時間
@app.put("/bosses/{boss_id}/reset")
def reset_boss(boss_id: int, db: Session = Depends(get_db)):
    record = db.query(models.BossRecord).filter(models.BossRecord.id == boss_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="找不到這筆資料")
    
    record.kill_time = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return {"status": "success", "message": "時間已重置"}

# 🛠️ 功能 E: 維修重置
@app.post("/maintenance/reset")
def maintenance_reset(db: Session = Depends(get_db)):
    db.query(models.BossRecord).delete()
    now = datetime.utcnow()
    for boss_name in game_config.VALID_BOSS_NAMES:
        new_record = models.BossRecord(
            boss_name=boss_name,
            channel=-1, 
            kill_time=now
        )
        db.add(new_record)
    db.commit()
    return {"status": "success", "message": "維修重置完成"}