"""
时区工具模块
用于处理时区转换，统一使用北京时间（UTC+8）
"""
from datetime import datetime, timezone, timedelta

# 北京时间时区（UTC+8）
BEIJING_TZ = timezone(timedelta(hours=8))

def beijing_now():
    """获取当前北京时间（返回naive datetime，与数据库存储格式一致）"""
    # 获取带时区的北京时间，然后去掉时区信息，返回naive datetime
    # 这样可以直接与数据库中存储的naive datetime进行比较
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)

def utc_to_beijing(utc_dt):
    """将UTC时间转换为北京时间"""
    if utc_dt is None:
        return None
    if utc_dt.tzinfo is None:
        # 如果没有时区信息，假设是UTC时间
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(BEIJING_TZ)

def beijing_to_utc(beijing_dt):
    """将北京时间转换为UTC时间（用于存储到数据库）"""
    if beijing_dt is None:
        return None
    if beijing_dt.tzinfo is None:
        # 如果没有时区信息，假设是北京时间
        beijing_dt = beijing_dt.replace(tzinfo=BEIJING_TZ)
    return beijing_dt.astimezone(timezone.utc).replace(tzinfo=None)

def format_beijing_time(dt, format_str='%Y-%m-%d %H:%M'):
    """格式化时间为北京时间字符串"""
    if dt is None:
        return None
    beijing_dt = utc_to_beijing(dt) if dt.tzinfo is None or dt.tzinfo == timezone.utc else dt
    return beijing_dt.strftime(format_str)

