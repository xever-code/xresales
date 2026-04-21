import io
import pandas as pd
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
import os
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from sqlalchemy import func
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import pandas as pd
import io

# 导入我们刚刚写的模块
from core.database import get_db, engine
import models
import schemas

# (可选) 启动时自动在数据库创建表，因为我们在 docker 里用了 sql 脚本，这步其实是双保险
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Digital Consulting 售前管理系统 API", version="2.0.0")

# 配置跨域 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# JWT 安全认证配置
# ==========================
SECRET_KEY = os.getenv("SECRET_KEY", "it-presales-super-secret-key-v2")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# 获取当前登录用户 (依赖注入)
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="无效的凭证，请重新登录")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# ==========================
# 核心业务接口
# ==========================

@app.post("/api/auth/login", response_model=schemas.Token, tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """用户登录接口，签发 JWT Token"""
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    # MVP阶段：为了兼容旧数据，这里先使用明文密码比对。后续上生产建议改用 passlib 校验哈希。
    if not user or form_data.password != user.password_hash:
        raise HTTPException(status_code=400, detail="用户名或密码错误")
        
    # 生成 Token
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode({"sub": user.username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    
    return {
        "access_token": token, 
        "token_type": "bearer", 
        "role": user.role, 
        "username": user.username, 
        "real_name": user.real_name
    }

@app.post("/api/auth/password", tags=["Auth"])
def change_password(
    data: schemas.PasswordChange, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """修改当前登录用户的密码"""
    # 1. 验证旧密码是否正确
    if data.old_password != current_user.password_hash:
        raise HTTPException(status_code=400, detail="原密码输入错误")
    
    # 2. 不能与旧密码相同
    if data.old_password == data.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
        
    # 3. 更新密码
    current_user.password_hash = data.new_password
    db.commit()
    
    return {"status": "success", "message": "密码修改成功，请重新登录"}

@app.get("/api/configs", tags=["System"])
def get_configs(db: Session = Depends(get_db)):
    """获取系统字典配置 (任务类型、业务机会)"""
    configs = db.query(models.SystemConfig).all()
    result = {"visit_type": [], "opportunity_type": []}
    for c in configs:
        if c.config_type in result:
            result[c.config_type].append(c.label)
    return result

@app.get("/api/hospitals/search", tags=["Hospital"])
def search_hospitals(keyword: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """基于关键字模糊搜索医院"""
    hospitals = db.query(models.Hospital).filter(
        models.Hospital.name.ilike(f"%{keyword}%")
    ).limit(15).all()
    
    return [{"value": h.code, "label": h.name} for h in hospitals]

@app.post("/api/logs", tags=["Activity"])
def create_log(log_data: schemas.LogCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """提交工时日志 (核心录入接口)"""
    
    new_log = models.ActivityLog(
        user_id=current_user.id,
        user_name=current_user.real_name,  # 强制使用当前登录人的真实姓名
        hospital_code=log_data.hospital_code,
        contact_person=log_data.contact_person,
        visit_time_start=log_data.visit_time_start,
        visit_time_end=log_data.visit_time_end,
        purpose=log_data.purpose,
        activity_types=log_data.activity_types,
        next_step=log_data.next_step,
        opportunities=log_data.opportunities
    )
    
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
    return {"status": "success", "message": "录入成功", "log_id": new_log.id}

@app.get("/api/logs", tags=["Activity"])
def get_logs(
    page: int = 1, 
    size: int = 20, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """获取统计分析日志（自带权限隔离，关联查询用户区域）"""
    skip = (page - 1) * size
    
    # 联合查询：把 ActivityLog 和 Hospital、User 连起来
    query = db.query(
        models.ActivityLog, 
        models.Hospital.name.label("hospital_name"),
        models.User.region.label("user_region")  # 查询出该用户所属区域
    ).outerjoin(
        models.Hospital, models.ActivityLog.hospital_code == models.Hospital.code
    ).outerjoin(
        models.User, models.ActivityLog.user_id == models.User.id
    )
    
    # 🛡️ 核心权限隔离逻辑
    if current_user.role != "admin":
        # 如果不是管理员，强制加上 user_id 过滤条件
        query = query.filter(models.ActivityLog.user_id == current_user.id)
        
    # 按拜访开始时间倒序排列
    query = query.order_by(models.ActivityLog.visit_time_start.desc().nulls_last())
    
    # 计算总数（用于前端分页）
    total = query.count()
    # 获取当前页数据
    logs = query.offset(skip).limit(size).all()
    
    # 格式化拼装数据
    result = []
    for log, h_name, u_region in logs:
        result.append({
            "id": log.id,
            "user_name": log.real_name or log.user_name or "未知员工",
            "region": u_region or "未知区域", # 新增区域字段
            "hospital_name": h_name or "未知客户 (" + str(log.hospital_code) + ")",
            "contact_person": log.contact_person,
            "visit_time_start": log.visit_time_start,
            "visit_time_end": log.visit_time_end,
            "purpose": log.purpose,
            "activity_types": log.activity_types if log.activity_types else [],
            "next_step": log.next_step,
            "opportunities": log.opportunities if log.opportunities else []
        })
        
    return {"total": total, "items": result}

@app.get("/api/logs/export", tags=["Activity"])
def export_logs(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """一键导出工时记录为 Excel"""
    # 1. 基础查询：联合医院表和用户表获取名称和区域
    query = db.query(
        models.ActivityLog, 
        models.Hospital.name.label("hospital_name"),
        models.User.region.label("user_region")
    ).outerjoin(
        models.Hospital, models.ActivityLog.hospital_code == models.Hospital.code
    ).outerjoin(
        models.User, models.ActivityLog.user_id == models.User.id
    )
    
    # 2. 权限隔离：非管理员只能导出自己的
    if current_user.role != "admin":
        query = query.filter(models.ActivityLog.user_id == current_user.id)
        
    # 按时间倒序
    query = query.order_by(models.ActivityLog.visit_time_start.desc().nulls_last())
    logs = query.all()
    
    # 3. 组装 Excel 数据，将列表、时间格式化为可读字符串
    data = []
    for log, h_name, u_region in logs:
        data.append({
            "提交人": log.real_name or log.user_name or "未知员工",
            "所属区域": u_region or "未知区域",  # 紧跟在提交人后面
            "拜访客户": h_name or "未知客户",
            "拜访对象": log.contact_person,
            "开始时间": log.visit_time_start.strftime("%Y-%m-%d %H:%M") if log.visit_time_start else "",
            "结束时间": log.visit_time_end.strftime("%Y-%m-%d %H:%M") if log.visit_time_end else "",
            "交流目的": log.purpose,
            "任务类型": "、".join(log.activity_types) if log.activity_types else "",
            "业务机会": "、".join(log.opportunities) if log.opportunities else "",
            "下一步计划": log.next_step
        })
        
    # 4. 生成 Excel 文件流
    df = pd.DataFrame(data)
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    stream.seek(0)
    
    return StreamingResponse(
        stream, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=activity_logs_export.xlsx"}
    )

# 👇 1. 更新大区列表接口：排除 'system'
@app.get("/api/users/regions", tags=["System"])
def get_user_regions(db: Session = Depends(get_db)):
    """获取所有人员的大区列表 (排除系统内置账号)"""
    # 增加 .filter(models.User.region != 'system')
    regions = db.query(models.User.region).filter(
        models.User.region.isnot(None),
        models.User.region != 'system',
        models.User.region != 'System'
    ).distinct().all()
    return [r[0] for r in regions if r[0] and r[0].strip()]

# 👇 2. 更新统计接口：在循环逻辑中增加过滤
@app.get("/api/stats/summary", tags=["System"])
def get_stats_summary(
    start_date: str = None,
    end_date: str = None,
    region: str = None,
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """获取汇总统计数据 (排除 system 分区数据)"""
    
    query = db.query(models.ActivityLog, models.Hospital, models.User).outerjoin(
        models.Hospital, models.ActivityLog.hospital_code == models.Hospital.code
    ).outerjoin(
        models.User, models.ActivityLog.user_id == models.User.id
    )
    
    if current_user.role != "admin":
        query = query.filter(models.ActivityLog.user_id == current_user.id)
        
    if start_date:
        query = query.filter(models.ActivityLog.visit_time_start >= start_date)
    if end_date:
        end_dt = f"{end_date} 23:59:59" if len(end_date) == 10 else end_date
        query = query.filter(models.ActivityLog.visit_time_start <= end_dt)
        
    if region:
        query = query.filter(models.User.region == region)
        
    results = query.all()
    
    region_dict = {}
    hospital_dict = {}
    act_dict = {}
    opp_dict = {}
    
    for log, hosp, user in results:
        # 🛑 核心过滤：如果人员所属区域是 system，则不计入任何统计图表
        u_region = user.region if user and user.region else "未知大区"
        if u_region.lower() == 'system':
            continue

        hours = 0
        if log.visit_time_start and log.visit_time_end:
            delta = log.visit_time_end - log.visit_time_start
            hours = delta.total_seconds() / 3600.0
            
        if hours <= 0:
            continue

        # 1. 区域工时
        region_dict[u_region] = region_dict.get(u_region, 0) + hours
        
        # 2. 客户工时
        h_name = hosp.name if hosp else "未知客户"
        hospital_dict[h_name] = hospital_dict.get(h_name, 0) + hours
        
        # 3. 任务类型和业务机会
        if log.activity_types:
            for t in log.activity_types:
                act_dict[t] = act_dict.get(t, 0) + hours
        if log.opportunities:
            for o in log.opportunities:
                opp_dict[o] = opp_dict.get(o, 0) + hours
                
    top_hospitals = sorted(hospital_dict.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "region_stats": [{"name": k, "value": round(v, 1)} for k, v in region_dict.items()],
        "hospital_stats": {
            "names": [x[0] for x in top_hospitals],
            "values": [round(x[1], 1) for x in top_hospitals]
        },
        "activity_stats": [{"name": k, "value": round(v, 1)} for k, v in act_dict.items()],
        "opportunity_stats": [{"name": k, "value": round(v, 1)} for k, v in opp_dict.items()]
    }

# ==========================
# 客户(医院)管理接口 (仅限 Admin)
# ==========================

@app.get("/api/hospitals", tags=["Hospital"])
def get_hospitals_list(
    page: int = 1, size: int = 20, keyword: str = "", 
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """分页获取客户列表"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问")
        
    query = db.query(models.Hospital)
    if keyword:
        query = query.filter(
            models.Hospital.name.ilike(f"%{keyword}%") | 
            models.Hospital.code.ilike(f"%{keyword}%")
        )
        
    total = query.count()
    items = query.order_by(models.Hospital.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "items": items}


@app.post("/api/hospitals/import", tags=["Hospitals"])
async def import_hospitals(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = await file.read()
        
        # 读取 Excel，并把所有 NaN 替换为空字符串
        df = pd.read_excel(io.BytesIO(contents)).fillna("")
        
        success_count = 0
        for index, row in df.iterrows():
            # 👇 将原来获取中文表头的地方，全部换成与数据库一致的英文字段
            code = str(row.get('code', '')).strip()
            name = str(row.get('name', '')).strip()
            
            # 核心数据为空则跳过
            if not code or not name:
                continue
                
            classification = str(row.get('classification', '')).strip()
            seg = str(row.get('seg', '')).strip()
            region = str(row.get('region', '')).strip()
            
            # 写入数据库对象
            new_hosp = models.Hospital(
                code=code,
                name=name,
                classification=classification if classification else None,
                seg=seg if seg else None,
                region=region if region else None
            )
            db.merge(new_hosp) 
            success_count += 1
            
        db.commit()
        return {"status": "success", "message": f"成功处理 {success_count} 条客户数据！"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"解析 Excel 失败: {str(e)}")


@app.get("/api/hospitals/export", tags=["Hospital"])
def export_hospitals(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """一键导出所有客户数据为 Excel"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问")
        
    hospitals = db.query(models.Hospital).all()
    df = pd.DataFrame([{"code": h.code, "name": h.name, "region": h.region} for h in hospitals])
    
    # 将 DataFrame 写入内存中的 Excel 文件
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    stream.seek(0)
    
    # 以文件流形式返回给前端下载
    return StreamingResponse(
        stream, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=hospitals_export.xlsx"}
    )

@app.get("/api/stats/summary", tags=["System"])
def get_stats_summary(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """获取汇总统计数据用于图表展示"""
    query = db.query(models.ActivityLog)
    
    # 权限隔离
    if current_user.role != "admin":
        query = query.filter(models.ActivityLog.user_id == current_user.id)
    
    logs = query.all()
    
    # 1. 统计任务类型分布
    type_counts = {}
    for log in logs:
        if log.activity_types:
            for t in log.activity_types:
                type_counts[t] = type_counts.get(t, 0) + 1
    
    # 2. 统计客户分布 (取前10)
    hospital_counts = {}
    # 获取所有医院名称映射
    h_map = {h.code: h.name for h in db.query(models.Hospital).all()}
    for log in logs:
        name = h_map.get(log.hospital_code, "未知客户")
        hospital_counts[name] = hospital_counts.get(name, 0) + 1
    
    # 排序取前10
    top_hospitals = sorted(hospital_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "type_stats": [{"name": k, "value": v} for k, v in type_counts.items()],
        "hospital_stats": {
            "names": [x[0] for x in top_hospitals],
            "values": [x[1] for x in top_hospitals]
        }
    }