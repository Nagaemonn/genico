"""
プリセット管理モジュール
JSONファイルからプリセットを読み込み、管理する機能を提供
"""

import json
import os
from typing import Dict, List, Any


class PresetManager:
    """プリセット管理クラス"""
    
    def __init__(self, presets_file: str = "presets/presets.json"):
        """
        初期化
        
        Args:
            presets_file: プリセット定義ファイルのパス
        """
        self.presets_file = presets_file
        self.presets = {}
        self.load_presets()
    
    def load_presets(self) -> None:
        """プリセットファイルを読み込む"""
        try:
            if os.path.exists(self.presets_file):
                with open(self.presets_file, 'r', encoding='utf-8') as f:
                    self.presets = json.load(f)
            else:
                print(f"警告: プリセットファイル {self.presets_file} が見つかりません")
                self.presets = {}
        except json.JSONDecodeError as e:
            print(f"エラー: プリセットファイルのJSON形式が不正です: {e}")
            self.presets = {}
        except Exception as e:
            print(f"エラー: プリセットファイルの読み込みに失敗しました: {e}")
            self.presets = {}
    
    def get_presets(self) -> Dict[str, Any]:
        """
        全プリセットを取得
        
        Returns:
            プリセット辞書
        """
        return self.presets
    
    def get_preset(self, preset_id: str) -> Dict[str, Any]:
        """
        指定されたプリセットを取得
        
        Args:
            preset_id: プリセットID
            
        Returns:
            プリセット情報、存在しない場合は空辞書
        """
        return self.presets.get(preset_id, {})
    
    def get_preset_sizes(self, preset_id: str) -> List[int]:
        """
        指定されたプリセットのサイズ一覧を取得
        
        Args:
            preset_id: プリセットID
            
        Returns:
            サイズ一覧、存在しない場合は空リスト
        """
        preset = self.get_preset(preset_id)
        return preset.get('sizes', [])
    
    def get_preset_format(self, preset_id: str) -> str:
        """
        指定されたプリセットの出力形式を取得
        
        Args:
            preset_id: プリセットID
            
        Returns:
            出力形式（png/ico）、存在しない場合は'png'
        """
        preset = self.get_preset(preset_id)
        return preset.get('format', 'png')

    def get_preset_bundle(self, preset_id: str) -> str:
        """
        出力の束ね方を取得（single/zip/icns）
        """
        preset = self.get_preset(preset_id)
        return preset.get('bundle', 'zip')

    def get_filename_pattern(self, preset_id: str) -> str:
        """
        ファイル名パターンを取得。例: "icon{size}.png" / "favicon.ico" / "AppIcon.icns"
        """
        preset = self.get_preset(preset_id)
        return preset.get('filename_pattern', '{preset}_{size}x{size}.{ext}')
    
    def reload_presets(self) -> None:
        """プリセットファイルを再読み込み"""
        self.load_presets()
    
    def validate_preset(self, preset_data: Dict[str, Any]) -> bool:
        """
        プリセットデータの妥当性を検証
        
        Args:
            preset_data: 検証するプリセットデータ
            
        Returns:
            妥当な場合True、そうでなければFalse
        """
        required_fields = ['name', 'sizes', 'format']
        
        # 必須フィールドの存在確認
        for field in required_fields:
            if field not in preset_data:
                return False
        
        # sizesがリストで、すべて整数であることを確認
        if not isinstance(preset_data['sizes'], list):
            return False
        
        if not all(isinstance(size, int) and size > 0 for size in preset_data['sizes']):
            return False
        
        # formatが有効な値であることを確認
        if preset_data['format'] not in ['png', 'ico']:
            return False
        
        return True
