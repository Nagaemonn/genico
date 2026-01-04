"""
画像処理モジュール
Pillowを使用して画像のリサイズとフォーマット変換を行う
"""

import io
import os
import zipfile
from typing import List, Tuple, Optional, BinaryIO, Dict
import tempfile
import subprocess
import shutil
from PIL import Image, ImageOps


class ImageProcessor:
    """画像処理クラス"""
    
    def __init__(self):
        """初期化"""
        self.supported_formats = ['PNG', 'JPEG', 'JPG', 'WEBP']
        self.output_formats = ['PNG', 'ICO']
    
    def validate_image(self, image_data: bytes) -> bool:
        """
        画像データの妥当性を検証
        
        Args:
            image_data: 画像データ
            
        Returns:
            有効な画像の場合True、そうでなければFalse
        """
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                return img.format in self.supported_formats
        except Exception:
            return False
    
    def resize_image(self, image_data: bytes, size: int, output_format: str = 'PNG') -> bytes:
        """
        画像を指定されたサイズにリサイズ
        
        Args:
            image_data: 元画像データ
            size: リサイズ後のサイズ（正方形）
            output_format: 出力形式（PNG/ICO）
            
        Returns:
            リサイズされた画像データ
        """
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                # RGBAモードに変換（透過対応）
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # 正方形にクロップ（中央から）
                img = self._crop_to_square(img)
                
                # 指定サイズにリサイズ
                img = img.resize((size, size), Image.Resampling.LANCZOS)
                
                # 出力形式に応じて処理
                if output_format.upper() == 'ICO':
                    # ICO形式の場合、複数サイズを含める
                    return self._create_ico(img, [size])
                else:
                    # PNG形式の場合
                    return self._create_png(img)
                    
        except Exception as e:
            raise ValueError(f"画像のリサイズに失敗しました: {e}")
    
    def resize_multiple(self, image_data: bytes, sizes: List[int], output_format: str = 'PNG') -> List[Tuple[int, bytes]]:
        """
        複数のサイズにリサイズ
        
        Args:
            image_data: 元画像データ
            sizes: リサイズサイズのリスト
            output_format: 出力形式（PNG/ICO）
            
        Returns:
            (サイズ, 画像データ)のタプルのリスト
        """
        results = []
        
        for size in sizes:
            try:
                resized_data = self.resize_image(image_data, size, output_format)
                results.append((size, resized_data))
            except Exception as e:
                print(f"サイズ {size} のリサイズに失敗: {e}")
                continue
        
        return results
    
    def create_zip(self, resized_images: List[Tuple[int, bytes]], preset_name: str, output_format: str = 'PNG') -> bytes:
        """
        リサイズされた画像をZIPファイルにまとめる
        
        Args:
            resized_images: (サイズ, 画像データ)のタプルのリスト
            preset_name: プリセット名
            
        Returns:
            ZIPファイルデータ
        """
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            ext = 'png' if output_format.upper() != 'ICO' else 'ico'
            for size, image_data in resized_images:
                filename = f"{preset_name}_{size}x{size}.{ext}"
                zip_file.writestr(filename, image_data)
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    def create_zip_from_named(self, files: List[Tuple[str, bytes]]) -> bytes:
        """
        任意の(ファイル名, データ)リストからZIPを作成
        """
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, data in files:
                zip_file.writestr(filename, data)
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    def _crop_to_square(self, img: Image.Image) -> Image.Image:
        """
        画像を正方形にクロップ（中央から）
        
        Args:
            img: 元画像
            
        Returns:
            正方形にクロップされた画像
        """
        width, height = img.size
        
        if width == height:
            return img
        
        # 短い辺に合わせる
        size = min(width, height)
        
        # 中央からクロップ
        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size
        
        return img.crop((left, top, right, bottom))
    
    def _create_png(self, img: Image.Image) -> bytes:
        """
        PNG形式で画像データを作成
        
        Args:
            img: 画像オブジェクト
            
        Returns:
            PNGデータ
        """
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()
    
    def _create_ico(self, img: Image.Image, sizes: List[int]) -> bytes:
        """
        ICO形式で画像データを作成
        
        Args:
            img: 画像オブジェクト
            sizes: 含めるサイズのリスト
            
        Returns:
            ICOデータ
        """
        buffer = io.BytesIO()
        
        # ICO形式では複数サイズを含める必要がある
        ico_images = []
        for size in sizes:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            ico_images.append(resized)
        
        # 最初の画像をベースにICOを作成
        ico_images[0].save(buffer, format='ICO', sizes=[(im.width, im.height) for im in ico_images])
        return buffer.getvalue()

    def create_multi_ico(self, image_data: bytes, sizes: List[int]) -> bytes:
        """
        複数サイズを1つのICOにまとめる
        """
        with Image.open(io.BytesIO(image_data)) as img:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            img = self._crop_to_square(img)
            return self._create_ico(img, sizes)

    def create_icns(self, image_data: bytes, sizes: List[int]) -> Tuple[bytes, List[Tuple[str, bytes]]]:
        """
        macOS .icns を生成（iconutilが利用可能ならicnsバイナリ、
        フォールバックとして.iconset（名前付きPNGの集合）も返す）

        Returns:
            (icns_bytes or b"", iconset_files)
        """
        # iconsetに必要なファイル名マッピング（サイズ -> ファイル名）
        required_entries: List[Tuple[int, str]] = [
            (16, 'icon_16x16.png'),
            (32, 'icon_16x16@2x.png'),
            (32, 'icon_32x32.png'),
            (64, 'icon_32x32@2x.png'),
            (128, 'icon_128x128.png'),
            (256, 'icon_128x128@2x.png'),
            (256, 'icon_256x256.png'),
            (512, 'icon_256x256@2x.png'),
            (512, 'icon_512x512.png'),
            (1024, 'icon_512x512@2x.png'),
        ]

        # 生成（必要サイズのみ）
        iconset_files: List[Tuple[str, bytes]] = []
        with Image.open(io.BytesIO(image_data)) as base:
            if base.mode != 'RGBA':
                base = base.convert('RGBA')
            base = self._crop_to_square(base)
            wanted = set(sizes)
            for size, filename in required_entries:
                if size in wanted:
                    resized = base.resize((size, size), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    resized.save(buf, format='PNG', optimize=True)
                    iconset_files.append((filename, buf.getvalue()))

        # iconutil が使えるなら実ファイルを作ってicns生成
        icns_bytes = b""
        try:
            # iconutil が利用可能かチェック（macOS 向け）
            if shutil.which('iconutil') is None:
                raise RuntimeError('iconutil not available')
            with tempfile.TemporaryDirectory() as tmpdir:
                iconset_dir = os.path.join(tmpdir, 'App.iconset')
                os.makedirs(iconset_dir, exist_ok=True)
                for name, data in iconset_files:
                    with open(os.path.join(iconset_dir, name), 'wb') as f:
                        f.write(data)
                icns_path = os.path.join(tmpdir, 'App.icns')
                subprocess.run(['iconutil', '-c', 'icns', iconset_dir, '-o', icns_path], check=True)
                with open(icns_path, 'rb') as f:
                    icns_bytes = f.read()
        except Exception:
            icns_bytes = b""

        return icns_bytes, iconset_files
    
    def get_image_info(self, image_data: bytes) -> dict:
        """
        画像の基本情報を取得
        
        Args:
            image_data: 画像データ
            
        Returns:
            画像情報辞書
        """
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                return {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height
                }
        except Exception as e:
            return {'error': str(e)}
