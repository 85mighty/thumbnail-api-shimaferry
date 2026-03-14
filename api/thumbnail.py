"""
Vercel 썸네일 API - shimaferry.jp 전용
배경: ferry-bg.jpg (투명도 70% 다크 오버레이)
텍스트: 노란색/초록색/핑크색 멀티컬러
"""

from http.server import BaseHTTPRequestHandler
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import json
import urllib.request
import os

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            keyword = data.get('keyword', 'キーワードなし')
            # bg_color1/2는 오버레이 색상으로 재활용 (기본: 다크 네이비)
            overlay_color = data.get('overlay_color', '#0d1b2a')
            
            thumbnail = self.create_thumbnail(keyword, overlay_color)
            
            buffer = BytesIO()
            thumbnail.save(buffer, format='PNG', quality=95)
            buffer.seek(0)
            
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(buffer.getvalue())))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(buffer.getvalue())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def load_bg_image(self, size):
        """ferry-bg.jpg를 레포에서 로드 후 1:1 크롭"""
        try:
            # 레포 내 이미지 경로 (Vercel 배포 시 /var/task/ferry-bg.jpg)
            local_path = os.path.join(os.path.dirname(__file__), '..', 'ferry-bg.jpg')
            if os.path.exists(local_path):
                bg = Image.open(local_path).convert('RGB')
            else:
                # 폴백: GitHub raw URL에서 다운로드
                url = "https://raw.githubusercontent.com/85mighty/thumbnail-api-shimaferry/main/ferry-bg.jpg"
                response = urllib.request.urlopen(url, timeout=10)
                bg = Image.open(BytesIO(response.read())).convert('RGB')
            
            # 1:1 센터 크롭
            w, h = bg.size
            crop_size = min(w, h)
            left = (w - crop_size) // 2
            top = (h - crop_size) // 2
            bg = bg.crop((left, top, left + crop_size, top + crop_size))
            bg = bg.resize((size, size), Image.LANCZOS)
            return bg
        except Exception as e:
            # 폴백: 단색 배경
            return None
    
    def download_japanese_font(self):
        try:
            font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Bold.otf"
            response = urllib.request.urlopen(font_url, timeout=10)
            return BytesIO(response.read())
        except:
            try:
                font_url = "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"
                response = urllib.request.urlopen(font_url, timeout=10)
                return BytesIO(response.read())
            except:
                return None
    
    def load_font(self, size):
        font_data = self.download_japanese_font()
        if font_data:
            try:
                return ImageFont.truetype(font_data, size)
            except:
                return ImageFont.load_default()
        return ImageFont.load_default()
    
    def split_japanese_text(self, text, max_lines=4):
        words = text.split()
        return words[:max_lines]
    
    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def create_thumbnail(self, keyword, overlay_color='#0d1b2a'):
        size = 1080

        # 1. 배경 이미지 로드
        bg = self.load_bg_image(size)
        
        if bg:
            img = bg.copy()
            # 2. 다크 오버레이 (투명도 70% = alpha 178)
            overlay = Image.new('RGBA', (size, size), (*self.hex_to_rgb(overlay_color), 178))
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay)
            img = img.convert('RGB')
        else:
            # 폴백: 단색
            img = Image.new('RGB', (size, size), color=overlay_color)

        draw = ImageDraw.Draw(img)

        # 3. 텍스트 렌더링
        lines = self.split_japanese_text(keyword, max_lines=4)
        num_lines = len(lines)

        line_colors = [
            '#fff371',  # 노란색
            '#62ff00',  # 초록색
            '#ff00a2',  # 핑크색
            '#ffffff'   # 흰색
        ]

        if num_lines == 1:
            font_size = 320
        elif num_lines == 2:
            font_size = 260
        elif num_lines == 3:
            font_size = 210
        else:
            font_size = 170

        font = self.load_font(font_size)

        line_spacing = 60
        line_bboxes = []
        total_height = 0

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            actual_height = bbox[3] - bbox[1]
            line_bboxes.append(bbox)
            total_height += actual_height

        total_height += line_spacing * (num_lines - 1)
        y_start = (size - total_height) // 2

        for i, line in enumerate(lines):
            bbox = line_bboxes[i]
            text_width = bbox[2] - bbox[0]
            actual_height = bbox[3] - bbox[1]

            x = (size - text_width) // 2
            y = y_start - bbox[1]

            color = line_colors[i % len(line_colors)]

            # 검은색 테두리
            outline_width = 15
            for ox in range(-outline_width, outline_width + 1, 5):
                for oy in range(-outline_width, outline_width + 1, 5):
                    if ox != 0 or oy != 0:
                        draw.text((x + ox, y + oy), line, font=font, fill='black')

            draw.text((x, y), line, font=font, fill=color)
            y_start += actual_height + line_spacing

        return img
