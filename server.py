"""
HTTPサーバーモジュール
標準ライブラリのhttp.serverを使用してWebサービスを提供
"""

import os
import json
import argparse
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

from preset_manager import PresetManager
from image_processor import ImageProcessor
import re


class IconResizerHandler(BaseHTTPRequestHandler):
    """アイコンリサイザーのHTTPリクエストハンドラー"""
    
    def __init__(self, *args, **kwargs):
        self.preset_manager = PresetManager()
        self.image_processor = ImageProcessor()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """GETリクエストの処理"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        if path == '/':
            self.serve_index()
        elif path == '/api/presets':
            self.serve_presets()
        elif path.startswith('/static/'):
            self.serve_static_file(path)
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """POSTリクエストの処理"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/resize':
            self.handle_resize()
        else:
            self.send_error(404, "Not Found")
    
    def serve_index(self):
        """メインページを提供"""
        try:
            with open('templates/index.html', 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, "Template not found")
    
    def serve_presets(self):
        """プリセット一覧を提供"""
        presets = self.preset_manager.get_presets()
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = json.dumps(presets, ensure_ascii=False, indent=2)
        self.wfile.write(response.encode('utf-8'))
    
    def serve_static_file(self, path: str):
        """静的ファイルを提供"""
        file_path = path[1:]  # 先頭の'/'を削除
        
        # セキュリティチェック
        if '..' in file_path or not file_path.startswith('static/'):
            self.send_error(403, "Forbidden")
            return
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # ファイル拡張子に基づいてContent-Typeを設定
                if file_path.endswith('.css'):
                    content_type = 'text/css'
                elif file_path.endswith('.js'):
                    content_type = 'application/javascript'
                else:
                    content_type = 'application/octet-stream'
                
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "File not found")
        except Exception as e:
            self.send_error(500, f"Error serving file: {e}")
    
    def handle_resize(self):
        """画像リサイズ処理"""
        try:
            # マルチパートフォームデータを解析
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_error(400, "Content-Type must be multipart/form-data")
                return
            
            # 境界文字列を取得
            boundary = content_type.split('boundary=')[1]
            
            # リクエストボディを読み込み
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "No content")
                return
            
            post_data = self.rfile.read(content_length)
            
            # マルチパートデータを解析
            form_data = self._parse_multipart(post_data, boundary)
            
            # 必要なパラメータを取得
            image_file = form_data.get('image')
            preset_id = form_data.get('preset_id')
            custom_sizes = form_data.get('custom_sizes')
            
            if not image_file:
                self.send_error(400, "No image file provided")
                return
            
            # 画像データを取得
            image_data = image_file['data']
            
            # 画像の妥当性をチェック
            if not self.image_processor.validate_image(image_data):
                self.send_error(400, "Invalid image format")
                return
            
            # リサイズサイズを決定
            if preset_id and preset_id in self.preset_manager.get_presets():
                # プリセットを使用
                sizes = self.preset_manager.get_preset_sizes(preset_id)
                output_format = self.preset_manager.get_preset_format(preset_id)
                preset = self.preset_manager.get_preset(preset_id)
                preset_name = preset.get('name', preset_id)
                bundle = self.preset_manager.get_preset_bundle(preset_id)
                filename_pattern = self.preset_manager.get_filename_pattern(preset_id)
            elif custom_sizes:
                # カスタムサイズを使用
                try:
                    sizes = [int(s.strip()) for s in custom_sizes.split(',') if s.strip()]
                    if not sizes:
                        self.send_error(400, "No valid sizes provided")
                        return
                    output_format = 'PNG'
                    preset_name = 'custom'
                    bundle = 'zip' if len(sizes) > 1 else 'single'
                    filename_pattern = '{preset}_{size}x{size}.{ext}' if bundle != 'single' else 'custom.{ext}'
                except ValueError:
                    self.send_error(400, "Invalid custom sizes format")
                    return
            else:
                self.send_error(400, "No preset or custom sizes provided")
                return
            
            # バンドル方式に応じた生成とレスポンス
            if output_format.upper() == 'ICO' and bundle == 'single':
                # 単一ICO（複数サイズ内包）
                ico_bytes = self.image_processor.create_multi_ico(image_data, sizes)
                name = filename_pattern.format(preset=preset_id or 'custom', size=sizes[0], ext='ico')
                ascii_name = self._ascii_slug(name)
                self.send_response(200)
                self.send_header('Content-Type', 'image/x-icon')
                self._send_filename_headers(ascii_name, name)
                self.end_headers()
                self.wfile.write(ico_bytes)
                return

            if output_format.upper() == 'ICNS' and bundle == 'icns':
                icns_bytes, iconset_files = self.image_processor.create_icns(image_data, sizes)
                if icns_bytes:
                    name = filename_pattern if filename_pattern.endswith('.icns') else 'AppIcon.icns'
                    ascii_name = self._ascii_slug(name)
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/icns')
                    self._send_filename_headers(ascii_name, name)
                    self.end_headers()
                    self.wfile.write(icns_bytes)
                    return
                # フォールバック: .iconset をZIPで返す
                zip_bytes = self.image_processor.create_zip_from_named(iconset_files)
                name = (preset_id or 'app') + '.iconset.zip'
                self.send_response(200)
                self.send_header('Content-Type', 'application/zip')
                self._send_filename_headers(self._ascii_slug(name), name)
                self.end_headers()
                self.wfile.write(zip_bytes)
                return

            # 通常の複数PNGなど
            resized_images = self.image_processor.resize_multiple(image_data, sizes, output_format)
            if not resized_images:
                self.send_error(500, "Failed to resize images")
                return

            if len(resized_images) == 1 and bundle == 'single':
                # 単一画像の場合、直接ダウンロード
                size, image_data = resized_images[0]
                ext = output_format.lower()
                # UTF-8名（表示名ベース）とASCIIフォールバック（表示名のスラグ）
                name = filename_pattern.format(preset=(preset_id or 'custom'), size=size, ext=ext)
                ascii_filename = self._ascii_slug(name)
                # RFC 5987: UTF-8 名も併記（%エンコード）
                try:
                    utf8_filename = name
                except Exception:
                    utf8_filename = ascii_filename
                from urllib.parse import quote
                filename_star = quote(utf8_filename.encode('utf-8'))

                self.send_response(200)
                # 正しいContent-Type
                if ext == 'png':
                    self.send_header('Content-Type', 'image/png')
                elif ext == 'ico':
                    self.send_header('Content-Type', 'image/x-icon')
                else:
                    self.send_header('Content-Type', 'application/octet-stream')
                # Content-Disposition（ASCII fallback と UTF-8 併記）
                self.send_header('Content-Disposition', f"attachment; filename={ascii_filename}; filename*=UTF-8''{filename_star}")
                self.end_headers()
                self.wfile.write(image_data)
            else:
                # 複数画像の場合、ZIPファイルで提供
                # パターン適用したファイル名でZIP作成
                ext = output_format.lower()
                files = []
                base_safe = (preset_id if preset_id else 'custom')
                for size, data in resized_images:
                    fname = filename_pattern.format(preset=base_safe, size=size, ext=ext)
                    files.append((fname, data))
                zip_data = self.image_processor.create_zip_from_named(files)
                # ZIP名はプリセットの表示名を先頭に
                ascii_filename = f"{self._ascii_slug(preset_name)}_icons.zip"
                from urllib.parse import quote
                try:
                    utf8_filename = f"{preset_name}_icons.zip"
                except Exception:
                    utf8_filename = ascii_filename
                filename_star = quote(utf8_filename.encode('utf-8'))
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/zip')
                self.send_header('Content-Disposition', f"attachment; filename={ascii_filename}; filename*=UTF-8''{filename_star}")
                self.end_headers()
                self.wfile.write(zip_data)
                
        except Exception as e:
            print(f"Error in handle_resize: {e}")
            self.send_error(500, f"Internal server error: {e}")
    
    def _parse_multipart(self, data: bytes, boundary: str) -> Dict[str, Any]:
        """
        マルチパートフォームデータを解析
        
        Args:
            data: リクエストボディデータ
            boundary: 境界文字列
            
        Returns:
            解析されたフォームデータ
        """
        form_data = {}
        boundary_bytes = f'--{boundary}'.encode()
        
        parts = data.split(boundary_bytes)
        
        for part in parts[1:-1]:  # 最初と最後は空なので除外
            if b'\r\n\r\n' in part:
                header, content = part.split(b'\r\n\r\n', 1)
                content = content.rstrip(b'\r\n')
                
                # Content-Dispositionヘッダーを解析
                header_str = header.decode('utf-8', errors='ignore')
                if 'Content-Disposition' in header_str:
                    # name属性を抽出
                    if 'name="' in header_str:
                        name_start = header_str.find('name="') + 6
                        name_end = header_str.find('"', name_start)
                        name = header_str[name_start:name_end]
                        
                        # filename属性があるかチェック
                        if 'filename="' in header_str:
                            # ファイルアップロード
                            filename_start = header_str.find('filename="') + 10
                            filename_end = header_str.find('"', filename_start)
                            filename = header_str[filename_start:filename_end]
                            
                            form_data[name] = {
                                'filename': filename,
                                'data': content
                            }
                        else:
                            # 通常のフォームフィールド
                            form_data[name] = content.decode('utf-8')
        
        return form_data
    
    def log_message(self, format, *args):
        """ログメッセージの出力をカスタマイズ"""
        print(f"{self.address_string()} - {format % args}")

    def _send_filename_headers(self, ascii_filename: str, utf8_name: str):
        """Content-Disposition の filename/filename* を付与"""
        from urllib.parse import quote
        try:
            utf8_filename = utf8_name
        except Exception:
            utf8_filename = ascii_filename
        filename_star = quote(utf8_filename.encode('utf-8'))
        self.send_header('Content-Disposition', f"attachment; filename={ascii_filename}; filename*=UTF-8''{filename_star}")

    def _ascii_slug(self, name: str) -> str:
        """プリセット名などからASCII安全なスラグを生成"""
        if not isinstance(name, str):
            name = str(name)
        # 非ASCII除去
        name_ascii = name.encode('ascii', 'ignore').decode('ascii')
        # 許可文字以外を"_"に
        name_ascii = re.sub(r'[^A-Za-z0-9._-]+', '_', name_ascii).strip('_')
        return name_ascii or 'icons'


def run_server(host='0.0.0.0', port=8000):
    """
    サーバーを起動
    
    Args:
        host: ホスト名
        port: ポート番号
    """
    server_address = (host, port)
    httpd = HTTPServer(server_address, IconResizerHandler)
    
    print(f"アイコンリサイザーサーバーを起動しました")
    print(f"アクセス: http://{host}:{port}")
    print("終了するには Ctrl+C を押してください")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止しています...")
        httpd.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='アイコンリサイザーWebサーバー')
    parser.add_argument('-p', '--port', type=int, default=8000, help='ポート番号（デフォルト: 8000）')
    parser.add_argument('-H', '--host', type=str, default='0.0.0.0', help='ホスト名（デフォルト: 0.0.0.0）')
    
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
