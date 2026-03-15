"""
Vercel 썸네일 API - shimaferry.com 전용
배경: ferry-bg.jpg (투명도 70% 다크 오버레이)
텍스트: 1줄, 노란색(#fff371), 검은색 테두리
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
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            raw = post_data.decode('utf-8')
            data = json.loads(raw)
            if isinstance(data, str):
                data = json.loads(data)

            keyword = data.get('keyword', 'キーワードなし') if isinstance(data, dict) else 'キーワードなし'
            overlay_color = data.get('overlay_color', '#0d1b2a') if isinstance(data, dict) else '#0d1b2a'

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
        try:
            local_path = os.path.join(os.path.dirname(__file__), '..', 'ferry-bg.jpg')
            if os.path.exists(local_path):
                bg = Image.open(local_path).convert('RGB')
            else:
                url = "https://raw.githubusercontent.com/85mighty/thumbnail-api-shimaferry/main/ferry-bg.jpg"
                response = urllib.request.urlopen(url, timeout=10)
                bg = Image.open(BytesIO(response.read())).convert('RGB')

            w, h = bg.size
            crop_size = min(w, h)
            left = (w - crop_size) // 2
            top = (h - crop_size) // 2
            bg = bg.crop((left, top, left + crop_size, top + crop_size))
            bg = bg.resize((size, size), Image.LANCZOS)
            return bg
        except:
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

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def create_thumbnail(self, keyword, overlay_color='#0d1b2a'):
        size = 1080

        # 1. 배경 이미지 로드
        bg = self.load_bg_image(size)

        if bg:
            img = bg.copy()
            overlay = Image.new('RGBA', (size, size), (*self.hex_to_rgb(overlay_color), 178))
            img = img.convert('RGBA')
            img = Image.alpha_composite(img, overlay)
            img = img.convert('RGB')
        else:
            img = Image.new('RGB', (size, size), color=overlay_color)

        draw = ImageDraw.Draw(img)

        # 2. 키워드 전체를 1줄로 표시 (공백 포함 그대로)
        text = keyword.strip()

        # 글자 수에 따라 폰트 크기 자동 설정
        if len(text) <= 5:
            font_size = 280
        elif len(text) <= 8:
            font_size = 220
        elif len(text) <= 10:
            font_size = 180
        else:
            font_size = 150

        font = self.load_font(font_size)

        # 텍스트가 이미지 폭을 초과하면 폰트 자동 축소
        for _ in range(10):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            if text_width <= size - 80:
                break
            font_size = int(font_size * 0.85)
            font = self.load_font(font_size)

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 중앙 배치
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - bbox[1]

        # 검은색 테두리 (8방향)
        outline_width = 18
        for ox in range(-outline_width, outline_width + 1, 6):
            for oy in range(-outline_width, outline_width + 1, 6):
                if ox != 0 or oy != 0:
                    draw.text((x + ox, y + oy), text, font=font, fill='black')

        # 노란색 메인 텍스트
        draw.text((x, y), text, font=font, fill='#fff371')

        return img
