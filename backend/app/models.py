from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

# 声明 ORM 基类
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="user")
    region = Column(String(100))
    real_name = Column(String(100))
    
    # 建立与日志的关联关系 (一对多)
    logs = relationship("ActivityLog", back_populates="user")

class Hospital(Base):
    __tablename__ = "hospitals"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    region = Column(String(100))
    classification = Column(String, nullable=True) # 直接对应数据库 classification 列
    seg = Column(String, nullable=True)

class SystemConfig(Base):
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    config_type = Column(String(100), index=True, nullable=False)
    label = Column(String(255), nullable=False)

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    user_name = Column(String(100))
    hospital_code = Column(String(100), ForeignKey("hospitals.code", ondelete="CASCADE"), index=True)
    contact_person = Column(String(255))
    visit_time_start = Column(DateTime)
    visit_time_end = Column(DateTime)
    purpose = Column(Text)
    activity_types = Column(JSONB) # 强类型 JSON 存储
    next_step = Column(Text)
    opportunities = Column(JSONB)
    
    # 👇 新增下面这两行映射数据库的新字段
    real_name = Column(String(100))
    created_at = Column(DateTime)

    # ORM 关联属性
    user = relationship("User", back_populates="logs")
