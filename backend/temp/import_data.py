import pandas as pd
from sqlalchemy import create_engine

# 数据库连接配置 (注意端口使用映射出来的 5433)
# 请确保密码与您的 docker-compose.yml 一致
DB_URL = "postgresql://admin:YourStrongPassword123!@localhost:5433/presales_db"
engine = create_engine(DB_URL)

try:
    # 1. 读取 GBK 编码的 CSV
    print("正在读取文件...")
    df = pd.read_csv('hospitals_backup_gbk.csv', encoding='gbk')
    
    # 2. 写入数据库
    # if_exists='append' 表示追加数据
    # index=False 表示不写入 pandas 的索引列
    print(f"正在导入 {len(df)} 条数据到 hospitals 表...")
    df.to_sql('hospitals', engine, if_exists='append', index=False)
    
    print("✅ 导入成功！")

except Exception as e:
    print(f"❌ 导入失败: {e}")
    print("\n提示：如果提示 'duplicate key'，说明数据库中已存在相同编码的医院。")
