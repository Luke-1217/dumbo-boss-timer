from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 1. 抓取環境變數 (Render 會有這個變數)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 2. 本機開發模式 (如果抓不到雲端網址，就用本機的 SQLite)
if not SQLALCHEMY_DATABASE_URL:
    print("⚠️  注意：目前使用本機 SQLite 資料庫 (開發測試用)")
    SQLALCHEMY_DATABASE_URL = "sqlite:///./boss_local.db"
else:
    print(f"✅ 連線至雲端資料庫: {SQLALCHEMY_DATABASE_URL.split('@')[1]}") # 只印出後面那段，保護密碼

# 3. 修正網址格式 (Render 的 postgres:// 需要轉成 postgresql://)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 4. 建立引擎
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()