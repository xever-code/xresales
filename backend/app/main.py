import io
import os
from datetime import datetime, timedelta
import pandas as pd

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from sqlalchemy import func, or_

# 导入我们刚刚写的模块
from core.database import get_db, engine
import models
import schemas

# 启动时自动在数据库创建表
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
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    if not user or form_data.password != user.password_hash:
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    # 👇 新增：登录时检查维护状态
    maintenance = db.query(models.SystemConfig).filter(models.SystemConfig.config_type == "maintenance").first()
    # 如果系统维护中，且登录的不是管理员，直接拒绝登录
    if maintenance and user.role != "admin":
        raise HTTPException(status_code=503, detail="系统维护中，请稍后再试")
        
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
    if data.old_password != current_user.password_hash:
        raise HTTPException(status_code=400, detail="原密码输入错误")
    
    if data.old_password == data.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
        
    current_user.password_hash = data.new_password
    db.commit()
    
    return {"status": "success", "message": "密码修改成功，请重新登录"}

@app.get("/api/configs", tags=["System"])
def get_configs(db: Session = Depends(get_db)):
    configs = db.query(models.SystemConfig).all()
    result = {"visit_type": [], "opportunity_type": []}
    for c in configs:
        if c.config_type in result:
            result[c.config_type].append(c.label)
    return result

# ==========================
# 系统维护控制接口
# ==========================
@app.get("/api/system/maintenance", tags=["System"])
def get_maintenance_status(db: Session = Depends(get_db)):
    """查询系统是否处于维护模式"""
    conf = db.query(models.SystemConfig).filter(models.SystemConfig.config_type == "maintenance").first()
    return {"is_maintenance": True if conf else False}

@app.post("/api/system/maintenance", tags=["System"])
def toggle_maintenance(data: dict, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """开启/关闭系统维护模式 (仅限Admin)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权操作")
        
    is_maintenance = data.get("is_maintenance", False)
    
    # 先清理掉旧的配置
    db.query(models.SystemConfig).filter(models.SystemConfig.config_type == "maintenance").delete()
    
    # 如果开启维护，则写入一条记录
    if is_maintenance:
        new_conf = models.SystemConfig(config_type="maintenance", label="true")
        db.add(new_conf)
        
    db.commit()
    return {"status": "success", "message": "系统维护状态已更新", "is_maintenance": is_maintenance}

@app.get("/api/hospitals/search", tags=["Hospital"])
def search_hospitals(keyword: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    hospitals = db.query(models.Hospital).filter(
        models.Hospital.name.ilike(f"%{keyword}%")
    ).limit(15).all()
    
    return [{"value": h.code, "label": h.name} for h in hospitals]

@app.post("/api/logs", tags=["Activity"])
def create_log(log_data: schemas.LogCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """提交工时日志 (核心录入接口)"""
    
    new_log = models.ActivityLog(
        user_id=current_user.id,
        # 👇 建议保持 user_name 为账号名，real_name 为真实姓名，分工明确
        user_name=current_user.username,  
        real_name=current_user.real_name,  # 👈 新增：强制写入当前用户的真实姓名
        
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

# ==========================
# 修改工时记录接口
# ==========================
@app.put("/api/logs/{log_id}", tags=["Activity"])
def update_log(
    log_id: int, 
    data: dict, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    log = db.query(models.ActivityLog).filter(models.ActivityLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    # 权限校验：管理员可以改所有人，普通员工只能改自己的
    if current_user.role != "admin" and log.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此记录")
        
    if "hospital_code" in data and data["hospital_code"]:
        log.hospital_code = data["hospital_code"]
    if "visit_time_start" in data and data["visit_time_start"]:
        log.visit_time_start = data["visit_time_start"]
    if "visit_time_end" in data and data["visit_time_end"]:
        log.visit_time_end = data["visit_time_end"]
        
    db.commit()
    return {"status": "success", "message": "记录修改成功"}

@app.get("/api/logs", tags=["Logs"])
def get_logs(
    page: int = 1,          
    size: int = 15,         
    start_date: str = None, 
    end_date: str = None,
    user_name: str = None,  
    region: str = None,     
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    skip = (page - 1) * size
    
    # 👇 修改点 1：在查询字段中增加 User.real_name
    query = db.query(
        models.ActivityLog,
        models.Hospital.name.label("hospital_name"),
        models.User.region.label("region"),
        models.User.real_name.label("real_name")  # 👈 新增：查出用户的真实姓名
    ).outerjoin(
        models.User, models.ActivityLog.user_id == models.User.id
    ).outerjoin(
        models.Hospital, models.ActivityLog.hospital_code == models.Hospital.code
    )
    
    # 过滤系统账号
    query = query.filter(
        or_(models.User.region.is_(None), models.User.region.notin_(['system', 'System']))
    )

    if current_user.role != "admin":
        query = query.filter(models.ActivityLog.user_id == current_user.id)
    else:
        if user_name:
            # 👇 核心修改：将原来的 ActivityLog.user_name 改为 ActivityLog.real_name
            query = query.filter(models.ActivityLog.real_name.ilike(f"%{user_name}%"))
        if region:
            query = query.filter(models.User.region == region)

    if start_date:
        query = query.filter(models.ActivityLog.visit_time_start >= start_date)
    if end_date:
        end_dt = f"{end_date} 23:59:59" if len(end_date) == 10 else end_date
        query = query.filter(models.ActivityLog.visit_time_start <= end_dt)

    total = query.count()
    results = query.order_by(models.ActivityLog.visit_time_start.desc()).offset(skip).limit(size).all()
    
    # 👇 修改点 2：将真实姓名组装进返回字典中
    formatted_logs = []
    for log, hospital_name, user_region, user_real_name in results:
        log_dict = {c.name: getattr(log, c.name) for c in log.__table__.columns}
        log_dict["hospital_name"] = hospital_name
        log_dict["region"] = user_region
        # 💡 双保险兜底：如果 user 表里查到了 real_name 就用它，否则退化使用旧版日志里的 user_name
        log_dict["real_name"] = user_real_name if user_real_name else log.user_name 
        formatted_logs.append(log_dict)
    
    return {"total": total, "items": formatted_logs}

@app.get("/api/logs/export", tags=["Activity"])
def export_logs(
    user_name: str = None,  
    region: str = None,     
    start_date: str = None,     # 👇 新增：支持时间过滤
    end_date: str = None,       # 👇 新增：支持时间过滤
    hospital_names: str = None, # 👇 新增：支持批量传入指定的客户名称
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(
        models.ActivityLog, 
        models.Hospital.name.label("hospital_name"),
        models.User.region.label("user_region")
    ).outerjoin(
        models.Hospital, models.ActivityLog.hospital_code == models.Hospital.code
    ).outerjoin(
        models.User, models.ActivityLog.user_id == models.User.id
    )
    
    # 过滤系统账号
    query = query.filter(
        or_(models.User.region.is_(None), models.User.region.notin_(['system', 'System']))
    )
    
    if current_user.role != "admin":
        query = query.filter(models.ActivityLog.user_id == current_user.id)
    else:
        if user_name:
            query = query.filter(models.ActivityLog.real_name.ilike(f"%{user_name}%"))
        # 👇 新增：支持报表的 exclude_central 选项
        if region:
            if region == "exclude_central":
                query = query.filter(func.lower(models.User.region) != 'central')
            else:
                query = query.filter(models.User.region == region)
                
    # 👇 新增：报表时间区间过滤
    if start_date:
        query = query.filter(models.ActivityLog.visit_time_start >= start_date)
    if end_date:
        end_dt = f"{end_date} 23:59:59" if len(end_date) == 10 else end_date
        query = query.filter(models.ActivityLog.visit_time_start <= end_dt)

    # 👇 新增：只导出特定客户（用于 Top 3 客户导出）
    if hospital_names:
        names_list = [name.strip() for name in hospital_names.split(",")]
        query = query.filter(models.Hospital.name.in_(names_list))
        
    query = query.order_by(models.ActivityLog.visit_time_start.desc().nulls_last())
    logs = query.all()
    
    data = []
    for log, h_name, u_region in logs:
        data.append({
            "提交人": log.real_name or log.user_name or "未知员工",
            "所属区域": u_region or "未知区域",
            "拜访客户": h_name or "未知客户",
            "拜访对象": log.contact_person,
            "开始时间": log.visit_time_start.strftime("%Y-%m-%d %H:%M") if log.visit_time_start else "",
            "结束时间": log.visit_time_end.strftime("%Y-%m-%d %H:%M") if log.visit_time_end else "",
            "交流目的": log.purpose,
            "任务类型": "、".join(log.activity_types) if log.activity_types else "",
            "业务机会": "、".join(log.opportunities) if log.opportunities else "",
            "下一步计划": log.next_step
        })
        
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

@app.get("/api/users/regions", tags=["System"])
def get_user_regions(db: Session = Depends(get_db)):
    regions = db.query(models.User.region).filter(
        models.User.region.isnot(None),
        models.User.region != 'system',
        models.User.region != 'System'
    ).distinct().all()
    return [r[0] for r in regions if r[0] and r[0].strip()]

@app.get("/api/stats/summary", tags=["System"])
def get_stats_summary(
    start_date: str = None,
    end_date: str = None,
    region: str = None,
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    # ---------------- 1. 查询售前数据 ----------------
    pre_query = db.query(models.ActivityLog, models.Hospital, models.User).outerjoin(
        models.Hospital, models.ActivityLog.hospital_code == models.Hospital.code
    ).outerjoin(
        models.User, models.ActivityLog.user_id == models.User.id
    )
    
    if current_user.role != "admin":
        pre_query = pre_query.filter(models.ActivityLog.user_id == current_user.id)
        
    if start_date:
        pre_query = pre_query.filter(models.ActivityLog.visit_time_start >= start_date)
    if end_date:
        end_dt = f"{end_date} 23:59:59" if len(end_date) == 10 else end_date
        pre_query = pre_query.filter(models.ActivityLog.visit_time_start <= end_dt)
        
    if region:
        if region == "exclude_central":
            pre_query = pre_query.filter(func.lower(models.User.region) != 'central')
        else:
            pre_query = pre_query.filter(models.User.region == region)
        
    pre_results = pre_query.all()
    
    pre_region = {}
    pre_user = {} 
    hospital_dict = {}
    act_dict = {}
    opp_dict = {}
    
    for log, hosp, user in pre_results:
        u_region = user.region if user and user.region else "未知大区"
        if u_region.lower() == 'system':
            continue

        hours = 0
        if log.visit_time_start and log.visit_time_end:
            delta = log.visit_time_end - log.visit_time_start
            hours = delta.total_seconds() / 3600.0
            
        if hours <= 0: continue

        pre_region[u_region] = pre_region.get(u_region, 0) + hours
        
        # 仅售前参与排行的指标
        h_name = hosp.name if hosp else "未知客户"
        hospital_dict[h_name] = hospital_dict.get(h_name, 0) + hours
        
        if log.activity_types:
            for t in log.activity_types: act_dict[t] = act_dict.get(t, 0) + hours
        if log.opportunities:
            for o in log.opportunities: opp_dict[o] = opp_dict.get(o, 0) + hours
            
        u_display_name = log.real_name if log.real_name else (log.user_name or "未知员工")
        if not u_display_name.strip() or u_display_name == "未知员工":
            continue
        pre_user[u_display_name] = pre_user.get(u_display_name, 0) + hours

    # ---------------- 2. 查询售后数据 (通过名字匹配员工表以规范大区) ----------------
    aft_query = db.query(models.AfterSalesLog, models.User).outerjoin(
        models.User, models.AfterSalesLog.technician_name == models.User.real_name
    )
    if current_user.role != "admin":
        aft_query = aft_query.filter(models.AfterSalesLog.technician_name == current_user.real_name)
        
    if start_date:
        aft_query = aft_query.filter(models.AfterSalesLog.start_time >= start_date)
    if end_date:
        end_dt = f"{end_date} 23:59:59" if len(end_date) == 10 else end_date
        aft_query = aft_query.filter(models.AfterSalesLog.start_time <= end_dt)
        
    if region:
        if region == "exclude_central":
            aft_query = aft_query.filter(func.lower(models.User.region) != 'central')
        else:
            aft_query = aft_query.filter(models.User.region == region)
            
    aft_results = aft_query.all()
    aft_region = {}
    aft_user = {}
    
    for alog, user in aft_results:
        # 使用系统中匹配到的大区规范数据
        u_region = user.region if user and user.region else "未知大区"
        if u_region.lower() == 'system':
            continue
            
        aft_region[u_region] = aft_region.get(u_region, 0) + alog.service_hours
        
        u_name = alog.technician_name if alog.technician_name else "未知员工"
        aft_user[u_name] = aft_user.get(u_name, 0) + alog.service_hours

    # ---------------- 3. 合并数据，供前端渲染堆叠柱状图 ----------------
    def merge_dicts(d1, d2):
        keys = set(d1.keys()) | set(d2.keys())
        combined = {k: d1.get(k, 0) + d2.get(k, 0) for k in keys}
        sorted_keys = sorted(combined.items(), key=lambda x: x[1], reverse=True)
        names = [x[0] for x in sorted_keys]
        return {
            "names": names,
            "presales": [round(d1.get(n, 0), 1) for n in names],
            "aftersales": [round(d2.get(n, 0), 1) for n in names]
        }

    merged_region = merge_dicts(pre_region, aft_region)
    merged_user = merge_dicts(pre_user, aft_user)
    
    # 医院排行榜只返回单纯的数值数组（因为只有售前）
    top_hospitals = sorted(hospital_dict.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "region_stats": merged_region,
        "user_stats": merged_user,
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
        df = pd.read_excel(io.BytesIO(contents)).fillna("")
        
        success_count = 0
        for index, row in df.iterrows():
            code = str(row.get('code', '')).strip()
            name = str(row.get('name', '')).strip()
            
            if not code or not name:
                continue
                
            classification = str(row.get('classification', '')).strip()
            seg = str(row.get('seg', '')).strip()
            region = str(row.get('region', '')).strip()
            
            # 使用精准查询判断，防止 UniqueViolation 报错
            existing_hosp = db.query(models.Hospital).filter(models.Hospital.code == code).first()
            if existing_hosp:
                existing_hosp.name = name
                existing_hosp.classification = classification if classification else None
                existing_hosp.seg = seg if seg else None
                existing_hosp.region = region if region else None
            else:
                new_hosp = models.Hospital(
                    code=code,
                    name=name,
                    classification=classification if classification else None,
                    seg=seg if seg else None,
                    region=region if region else None
                )
                db.add(new_hosp)
                
            success_count += 1
            
        db.commit()
        return {"status": "success", "message": f"成功处理 {success_count} 条客户数据！"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"解析 Excel 失败: {str(e)}")
    
# ==========================
# 售后工时导入接口 (仅限 Admin)
# ==========================
@app.post("/api/aftersales/import", tags=["AfterSales"])
async def import_aftersales(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可导入售后数据")
        
    try:
        contents = await file.read()
        if file.filename.endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding='gbk')
        else:
            df = pd.read_excel(io.BytesIO(contents))
            
        df = df.fillna("")
        
        # 👇 新增：一个非常健壮的时间解析函数
        def parse_excel_date(val):
            val_str = str(val).strip()
            if not val_str:
                return None
            try:
                # 尝试作为 Excel 序列号处理（例如 46146.0833）
                # Excel 序列号是以 1899-12-30 为起点的天数
                f_val = float(val_str)
                return pd.to_datetime(f_val, unit='D', origin='1899-12-30')
            except ValueError:
                # 如果转 float 报错，说明它是普通的文本时间（例如 "2026-05-01 10:00:00"）
                return pd.to_datetime(val_str)

        success_count = 0
        for index, row in df.iterrows():
            tech_name = str(row.get('执行姓名', '')).strip()
            hours_str = str(row.get('服务时长', '0')).strip()
            
            if not tech_name or not hours_str:
                continue
                
            try:
                hours = float(hours_str)
            except ValueError:
                hours = 0.0
                
            if hours <= 0:
                continue
                
            # 👇 修改：使用刚才写好的函数来解析开始和结束时间
            start_time = parse_excel_date(row.get('Start Date and Time', ''))
            end_time = parse_excel_date(row.get('End Date and Time', ''))

            log = models.AfterSalesLog(
                technician_name=tech_name,
                service_hours=hours,
                hospital_name=str(row.get('客户名', '')).strip(),
                region=str(row.get('SI区域', '')).strip(),
                work_order=str(row.get('Work Order Number', '')).strip(),
                start_time=start_time,
                end_time=end_time
            )
            db.add(log)
            success_count += 1
            
        db.commit()
        return {"status": "success", "message": f"成功导入 {success_count} 条售后工时数据！"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")

@app.get("/api/hospitals/export", tags=["Hospital"])
def export_hospitals(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问")
        
    hospitals = db.query(models.Hospital).all()
    # 增加细分和等级的导出
    df = pd.DataFrame([{
        "code": h.code, 
        "name": h.name, 
        "region": h.region,
        "classification": getattr(h, 'classification', ''),
        "seg": getattr(h, 'seg', '')
    } for h in hospitals])
    
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    stream.seek(0)
    
    return StreamingResponse(
        stream, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=hospitals_export.xlsx"}
    )

# 文件顶部引入处请确保有 IntegrityError：
from sqlalchemy.exc import IntegrityError

# ==========================
# 用户管理接口 (仅限 Admin)
# ==========================

@app.get("/api/users", tags=["Users"])
def get_users_list(
    page: int = 1, size: int = 20, keyword: str = "", 
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """获取用户列表"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问")
        
    query = db.query(models.User)
    if keyword:
        query = query.filter(
            (models.User.username.ilike(f"%{keyword}%")) | 
            (models.User.real_name.ilike(f"%{keyword}%"))
        )
        
    total = query.count()
    users = query.order_by(models.User.id.desc()).offset((page - 1) * size).limit(size).all()
    
    return {
        "total": total, 
        "items": [{
            "id": u.id, 
            "username": u.username, 
            "real_name": u.real_name, 
            "region": u.region, 
            "role": u.role
        } for u in users]
    }

@app.post("/api/users", tags=["Users"])
def create_user(data: dict, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """创建新用户"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权操作")
        
    username = data.get("username", "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="登录账号名不能为空")
        
    if db.query(models.User).filter(models.User.username == username).first():
        raise HTTPException(status_code=400, detail="该登录账号已存在，请换一个")
        
    new_user = models.User(
        username=username,
        password_hash=data.get("password", "123456"), # 默认初始密码为 123456
        real_name=data.get("real_name", "").strip(),
        region=data.get("region", "").strip(),
        role=data.get("role", "user")
    )
    db.add(new_user)
    db.commit()
    return {"status": "success", "message": "员工账号创建成功！初始密码为：123456"}

@app.put("/api/users/{user_id}", tags=["Users"])
def update_user(user_id: int, data: dict, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """修改用户信息 / 重置密码"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权操作")
        
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="未找到该用户")
        
    # 如果修改了账号名，检查是否与别人冲突
    new_username = data.get("username", "").strip()
    if new_username and new_username != user.username:
        if db.query(models.User).filter(models.User.username == new_username).first():
            raise HTTPException(status_code=400, detail="该账号名已被其他员工占用")
        user.username = new_username
        
    if "real_name" in data:
        user.real_name = data["real_name"].strip()
    if "region" in data:
        user.region = data["region"].strip()
    if "role" in data:
        user.role = data["role"]
        
    # 核心：重置密码功能
    if data.get("reset_password"):
        user.password_hash = "123456"
        
    db.commit()
    return {"status": "success", "message": "信息更新成功"}

@app.delete("/api/users/{user_id}", tags=["Users"])
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """删除用户"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权操作")
        
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="安全限制：您不能删除正在使用的管理员账号自身")
        
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="未找到该用户")
        
    try:
        db.delete(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        # 防爆机制：如果该员工已经填过工时，数据库外键会阻止删除，这里做友好拦截
        raise HTTPException(status_code=400, detail="删除失败！该员工已有关联的打卡记录。为保证数据完整，建议您仅将其角色修改或大区改为空。")
        
    return {"status": "success", "message": "用户删除成功"}