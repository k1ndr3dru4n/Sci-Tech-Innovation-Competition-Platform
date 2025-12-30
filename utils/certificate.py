"""
电子证书生成工具
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from config import Config
from datetime import datetime
import os

def generate_certificate(team_name, award_name, competition_name, year):
    """
    生成电子证书（图片格式）
    格式：队伍名+奖项名称
    """
    # 创建证书目录
    cert_dir = Path(Config.CERTIFICATE_FOLDER)
    cert_dir.mkdir(parents=True, exist_ok=True)
    
    # 证书尺寸（A4横向：297x210mm，300dpi）
    width, height = 3508, 2480  # 约A4横向尺寸（像素）
    
    # 创建白色背景
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体（如果系统有中文字体）
    try:
        # Windows系统字体路径
        font_paths = [
            'C:/Windows/Fonts/simhei.ttf',  # 黑体
            'C:/Windows/Fonts/simsun.ttc',  # 宋体
            'C:/Windows/Fonts/msyh.ttc',   # 微软雅黑
        ]
        title_font = None
        content_font = None
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                title_font = ImageFont.truetype(font_path, 120)
                content_font = ImageFont.truetype(font_path, 80)
                break
        
        if not title_font:
            # 如果没有找到字体，使用默认字体
            title_font = ImageFont.load_default()
            content_font = ImageFont.load_default()
    except:
        title_font = ImageFont.load_default()
        content_font = ImageFont.load_default()
    
    # 绘制标题
    title = "获奖证书"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    title_y = height // 4
    draw.text((title_x, title_y), title, fill='black', font=title_font)
    
    # 绘制内容
    content_lines = [
        f"兹证明 {team_name} 队伍",
        f"在{year}年{competition_name}中",
        f"荣获 {award_name}",
        "",
        f"特发此证，以资鼓励。"
    ]
    
    line_height = 120
    start_y = height // 2 - 100
    
    for i, line in enumerate(content_lines):
        if line:
            line_bbox = draw.textbbox((0, 0), line, font=content_font)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = (width - line_width) // 2
            draw.text((line_x, start_y + i * line_height), line, fill='black', font=content_font)
    
    # 绘制日期
    date_text = f"{datetime.now().strftime('%Y年%m月%d日')}"
    date_bbox = draw.textbbox((0, 0), date_text, font=content_font)
    date_width = date_bbox[2] - date_bbox[0]
    date_x = width - date_width - 200
    date_y = height - 300
    draw.text((date_x, date_y), date_text, fill='black', font=content_font)
    
    # 生成文件名：队伍名+奖项名称
    safe_team_name = "".join(c for c in team_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_award_name = "".join(c for c in award_name if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"{safe_team_name}_{safe_award_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filename = filename.replace(' ', '_')
    
    # 保存证书
    cert_path = cert_dir / filename
    img.save(str(cert_path), 'PNG', quality=95)
    
    return str(cert_path.relative_to(Path(Config.CERTIFICATE_FOLDER)))

