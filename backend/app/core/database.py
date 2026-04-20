import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 从环境变量获取数据库地址，默认值为我们 docker-compose 中配置的地址
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://admin:YourStrongPassword123!@db:5432/presales_db"
)

# 创建 SQLAlchemy 引擎
engine = create_engine(DATABASE_URL)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 依赖注入：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
