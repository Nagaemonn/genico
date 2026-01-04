# Icon Resizer

入力されたアイコン用画像ファイルを，適切にリサイズするWebサービスです。

## 特徴

- 🖼️ **簡単な画像アップロード**: ドラッグ&ドロップまたはクリックで画像をアップロード
- 📱 **プリセット対応**: Chrome拡張、macOSアイコン、Webファビコンなどのプリセットサイズ
- ⚙️ **カスタムサイズ**: 任意のサイズを指定してリサイズ可能
- 🎨 **モダンなUI**: 清潔感のあるグリーンベースのデザイン
- 📦 **ZIPダウンロード**: 複数サイズの場合はZIPファイルで一括ダウンロード
- 🔧 **拡張可能**: JSONファイルでプリセットを簡単に追加可能

## 対応画像形式

### 入力形式
- PNG
- JPEG/JPG
- WebP

### 出力形式
- PNG
- ICO（Webファビコン用・単一ファイルに複数サイズ内包可）
- ICNS（macOSアプリアイコン。`iconutil`が無い場合は`.iconset.zip`を返却）

## インストールと起動

### uvを使用する場合（推奨）

#### 1. 依存パッケージのインストール

```bash
uv sync
```

#### 2. サーバーの起動

```bash
uv run server.py
```

デフォルトでは`0.0.0.0:8000`で起動するため、外部からもアクセス可能です。

ポートを指定する場合：

```bash
uv run server.py -p 3000
```

ホストを指定する場合（localhostのみに制限）：

```bash
uv run server.py -H localhost
```

または、エントリーポイントを使用：

```bash
uv run icon-resizer
```

### 従来の方法（pip使用）

#### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

#### 2. サーバーの起動

```bash
python server.py
```

デフォルトでは`0.0.0.0:8000`で起動するため、外部からもアクセス可能です。

ポートを指定する場合：

```bash
python server.py -p 3000
```

ホストを指定する場合（localhostのみに制限）：

```bash
python server.py -H localhost
```

### 3. ブラウザでアクセス

```
http://localhost:8000
```

## 使用方法

1. **画像をアップロード**: ドラッグ&ドロップまたは「ファイルを選択」ボタンで画像をアップロード
2. **プリセットを選択**: 目的に応じたプリセットカードをクリック
3. **カスタムサイズ**: 任意のサイズをカンマ区切りで入力（例: 16,32,48,64）
4. **ダウンロード**: 処理完了後、自動的にダウンロードが開始されます

## プリセットの追加（設定ファイルの書き方）

`presets/presets.json`にプリセットを定義します。各エントリは以下のキーを持てます：

- `name`（必須）: 表示名
- `sizes`（必須）: 出力サイズの配列（整数、正方）
- `format`（必須）: 出力形式（`png` | `ico` | `icns`）
- `bundle`（任意）: 出力の束ね方
  - `single`: 単一ファイルとして返却（例: 1つの`ico`）
  - `zip`: 複数ファイルをZIPで返却（例: 複数PNG）
  - `icns`: 可能なら`.icns`単体で返却（不可なら`.iconset.zip`）
- `filename_pattern`（任意）: ファイル名規則。以下のプレースホルダを使用可能
  - `{size}`: サイズ数値（例: 16）
  - `{preset}`: プリセットID（例: chrome_extension）
  - `{ext}`: 拡張子（`png`/`ico`/`icns`）

最小例（従来と互換）:

```json
{
  "your_preset": {
    "name": "あなたのプリセット名",
    "sizes": [16, 32, 48, 64, 128],
    "format": "png"
  }
}
```

推奨例（Chrome拡張・macOS・favicon）:

```json
{
  "chrome_extension": {
    "name": "Chrome拡張アイコン",
    "sizes": [16, 32, 48, 128],
    "format": "png",
    "bundle": "zip",
    "filename_pattern": "icon{size}.png"
  },
  "macos_icon": {
    "name": "macOSアイコン",
    "sizes": [16, 32, 64, 128, 256, 512, 1024],
    "format": "icns",
    "bundle": "icns",
    "filename_pattern": "AppIcon.icns"
  },
  "favicon": {
    "name": "Webファビコン",
    "sizes": [16, 32, 48],
    "format": "ico",
    "bundle": "single",
    "filename_pattern": "favicon.ico"
  }
}
```

注意:
- macOS用`icns`はシステムに`iconutil`がある場合のみ直接`.icns`を生成します。無い場合は`.iconset`構造をZIPで返します。
- 設定変更後はサーバー再起動で反映されます。

## 技術仕様

- **Python**: 3.8+
- **Webフレームワーク**: 標準ライブラリ（http.server）
- **画像処理**: Pillow
- **フロントエンド**: バニラJavaScript + CSS
- **最大ファイルサイズ**: 10MB
- **ポート**: 8000（デフォルト）

## ライセンス

MIT License
