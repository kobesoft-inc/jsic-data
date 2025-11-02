# JSIC PDFパーサー

日本標準産業分類（JSIC）のPDFを解析して、構造化されたJSONデータに変換するPythonツールです。

## 概要

総務省が公開している日本標準産業分類（JSIC）のPDF文書から、以下の情報を抽出して階層化されたJSONデータを生成します：

- 大分類（20件）、中分類（99件）、小分類（536件）、細分類（1,473件）
- 各分類の日本語名と英語名
- 詳細な説明文
- 含まれる業態の例
- 除外される業態の例（該当コード付き）

**データソース**: [総務省 日本標準産業分類](https://www.soumu.go.jp/main_content/000941216.pdf)

## リポジトリ

このプロジェクトは以下のGitHubリポジトリで管理されています：

https://github.com/kobesoft-inc/jsic

## JSONデータの直接利用

パーサーを実行せずに、生成済みのJSONデータを直接利用できます。以下のURLから必要な形式のファイルを取得してください：

### 生成済みファイル

| 形式 | サイズ | 説明 | ダウンロードURL |
|------|--------|------|----------------|
| **full** | 1.8MB | 完全なデータ（説明・例含む） | https://raw.githubusercontent.com/kobesoft-inc/jsic/main/jsic-full.json |
| **simple** | 295KB | コードと名前のみ | https://raw.githubusercontent.com/kobesoft-inc/jsic/main/jsic-simple.json |
| **en** | 439KB | コードと名前と英語名 | https://raw.githubusercontent.com/kobesoft-inc/jsic/main/jsic-en.json |

### 使用例

#### ブラウザから直接取得

```javascript
// JavaScriptでの使用例
fetch('https://raw.githubusercontent.com/kobesoft-inc/jsic/main/jsic-simple.json')
  .then(response => response.json())
  .then(data => {
    console.log(data.major_categories);
  });
```

#### cURLでダウンロード

```bash
# シンプル版をダウンロード
curl -O https://raw.githubusercontent.com/kobesoft-inc/jsic/main/jsic-simple.json

# 完全版をダウンロード
curl -O https://raw.githubusercontent.com/kobesoft-inc/jsic/main/jsic-full.json

# 英語名付き版をダウンロード
curl -O https://raw.githubusercontent.com/kobesoft-inc/jsic/main/jsic-en.json
```

#### Pythonでの使用例

```python
import requests

# JSONデータを取得
url = 'https://raw.githubusercontent.com/kobesoft-inc/jsic/main/jsic-simple.json'
response = requests.get(url)
jsic_data = response.json()

# データの利用
for major in jsic_data['major_categories']:
    print(f"{major['code']}: {major['name']}")
```

## インストール

### 必要な環境

- Python 3.7以上
- 仮想環境（推奨）

### セットアップ

```bash
# リポジトリのクローン
cd jsic

# 仮想環境の作成
python3 -m venv .venv

# 仮想環境の有効化
source .venv/bin/activate  # macOS/Linux
# または
.venv\\Scripts\\activate  # Windows

# 依存パッケージのインストール
pip install -r requirements.txt
```

## 使い方

### 基本的な使用方法

```bash
# デフォルト設定で実行（詳細版JSON出力）
python jsic.py

# 出力: jsic.json

# 3つのフォーマットをまとめて生成
./generate_all.sh

# 出力: jsic-full.json, jsic-simple.json, jsic-en.json
```

### コマンドラインオプション

```bash
python jsic.py [OPTIONS]

オプション:
  -o, --output FILE      出力JSONファイル名 (デフォルト: jsic.json)
  --format FORMAT        出力形式: full, simple, en (デフォルト: full)
  -h, --help             ヘルプを表示
```

### 出力形式の選択

3つの出力形式から選択できます：

| 形式 | サイズ | 用途 | コマンド |
|------|--------|------|----------|
| **full** | 1.8MB | 完全なデータ（説明・例含む） | `python jsic.py --format full` |
| **simple** | 295KB | コードと名前のみ | `python jsic.py --format simple` |
| **en** | 439KB | コードと名前と英語名 | `python jsic.py --format en` |

## JSON仕様

### 基本構造

すべての出力形式は以下の階層構造を持ちます：

```
大分類 (major_categories)
└── 中分類 (middle_categories)
    └── 小分類 (minor_categories)
        └── 細分類 (detail_categories)
```

### フィールド定義

#### 共通フィールド（全形式）

| フィールド | 型 | 説明 | 例 |
|-----------|-----|------|-----|
| `code` | string | 分類コード | `"A"`, `"01"`, `"011"`, `"0111"` |
| `name` | string | 日本語名称 | `"農業、林業"` |

#### 追加フィールド（形式による）

| フィールド | 型 | 含まれる形式 | 説明 |
|-----------|-----|-------------|------|
| `name_en` | string | `en`, `full` | 英語名称 |
| `description` | string | `full` | 詳細説明（majorとmiddleのみ） |
| `included_examples` | array[string] | `full` | 含まれる業態の例 |
| `excluded_examples` | array[object] | `full` | 除外される業態の例 |

#### `excluded_examples` の構造

```json
{
  "name": "業態名",
  "codes": ["コード1", "コード2", ...]
}
```

### コード体系

| 階層 | コード形式 | 桁数 | 件数 | 範囲 | 例 |
|------|-----------|------|------|------|-----|
| 大分類 | アルファベット | 1文字 | 20件 | A-T | `"A"` |
| 中分類 | 数字 | 2桁 | 99件 | 01-99 | `"01"` |
| 小分類 | 数字 | 3桁 | 536件 | 010-999 | `"011"` |
| 細分類 | 数字 | 4桁 | 1,473件 | 0100-9999 | `"0111"` |

**合計**: 2,128件

### 完全なJSON例（full形式）

```json
{
  "major_categories": [
    {
      "code": "A",
      "name": "農業、林業",
      "name_en": "AGRICULTURE, FORESTRY",
      "description": "この大分類には、耕作、採草、採種等の耕種農業、酪農、肉用牛、豚、鶏等の畜産農業...",
      "middle_categories": [
        {
          "code": "01",
          "name": "農業",
          "name_en": "AGRICULTURE",
          "description": "この中分類には、耕種農業、畜産農業...",
          "minor_categories": [
            {
              "code": "011",
              "name": "耕種農業",
              "name_en": "Crop farming",
              "detail_categories": [
                {
                  "code": "0111",
                  "name": "米作農業",
                  "name_en": "Paddy rice farming",
                  "description": "主として米を栽培し、出荷する事業所をいう。",
                  "included_examples": [
                    "稲作農業",
                    "水稲作農業",
                    "陸稲作農業"
                  ],
                  "excluded_examples": [
                    {
                      "name": "種もみ生産業",
                      "codes": ["0119"]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### Simple形式の例

```json
{
  "major_categories": [
    {
      "code": "A",
      "name": "農業、林業",
      "middle_categories": [
        {
          "code": "01",
          "name": "農業",
          "minor_categories": [
            {
              "code": "011",
              "name": "耕種農業",
              "detail_categories": [
                {
                  "code": "0111",
                  "name": "米作農業"
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### EN形式の例

```json
{
  "major_categories": [
    {
      "code": "A",
      "name": "農業、林業",
      "name_en": "AGRICULTURE, FORESTRY",
      "middle_categories": [
        {
          "code": "01",
          "name": "農業",
          "name_en": "AGRICULTURE",
          "minor_categories": [
            {
              "code": "011",
              "name": "耕種農業",
              "name_en": "Crop farming",
              "detail_categories": [
                {
                  "code": "0111",
                  "name": "米作農業",
                  "name_en": "Paddy rice farming"
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### フィールドの値の特徴

- **空のフィールド**: `description`、`included_examples`、`excluded_examples`は、該当する内容がない場合はフィールド自体が省略される
- **文字エンコーディング**: UTF-8
- **改行**: `description`内の改行は削除され、スペースなしで連結
- **正規化**: 全角/半角の統一、記号の正規化が適用済み

## ライセンス

このツールはオープンソースプロジェクトです。

## データソース

総務省 日本標準産業分類（第14回改定）
https://www.soumu.go.jp/main_content/000941216.pdf
