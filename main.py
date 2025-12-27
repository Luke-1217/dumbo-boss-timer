from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import math

# 引入我們自己寫的檔案
from database import engine, SessionLocal
import models
import game_config

# 1. 建立資料庫表格
models.Base.metadata.create_all(bind=engine)

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
        
        # 🟢 自動銷毀：維修卡 (-1) 且過期
        if record.channel == -1 and elapsed_mins >= min_spawn:
            db.delete(record)
            db.commit()
            continue 
            
        max_spawn = settings['max_mins']
        
        # 計算各種倒數
        mins_until_min = min_spawn - elapsed_mins
        mins_until_max = max_spawn - elapsed_mins # 這是算離「最晚出生」還要多久
        
        status = "unknown"
        status_color = "gray"
        
        # 🟢 狀態判斷邏輯 (修改重點)
        if elapsed_mins < min_spawn:
            # 時間未到 min -> 重生中 (倒數到 min)
            status = f"⏳ 重生中 (還剩 {int(mins_until_min)} 分)"
            status_color = "blue"
        elif elapsed_mins < max_spawn:
            # 時間超過 min 但還沒到 max -> 可能出生 (倒數到 max)
            # 👇 這裡改了！加上了括號顯示保底時間
            status = f"⚠️ 可能出生 (保底剩 {int(mins_until_max)} 分)"
            status_color = "orange"
        else:
            # 時間超過 max -> 已出生
            status = "🔥 已出生"
            status_color = "red"

        result_list.append({
            "id": record.id,
            "boss_name": record.boss_name,
            "img": settings['img'],
            "channel": record.channel,
            "status": status,
            "color": status_color,
            "kill_time": record.kill_time,
            "min_mins": min_spawn,
            "max_mins": max_spawn,
            "sort_score": mins_until_min # 排序依然照「誰最快有可能出」來排
        })
    
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