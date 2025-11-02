#!/bin/bash
# JSIC JSONファイルを3つのフォーマットで生成するスクリプト

# 仮想環境の有効化
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: 仮想環境(.venv)が見つかりません。"
    echo "python3 -m venv .venv を実行してセットアップしてください。"
    exit 1
fi

echo "=== JSIC JSON生成スクリプト ==="
echo ""

# 1. Full版（詳細情報付き）
echo "1. Full版を生成中..."
python jsic.py --format full -o jsic-full.json
if [ $? -eq 0 ]; then
    echo "✓ jsic-full.json を生成しました"
else
    echo "✗ Full版の生成に失敗しました"
    exit 1
fi

echo ""

# 2. Simple版（コードと名前のみ）
echo "2. Simple版を生成中..."
python jsic.py --format simple -o jsic-simple.json 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ jsic-simple.json を生成しました"
else
    echo "✗ Simple版の生成に失敗しました"
    exit 1
fi

echo ""

# 3. EN版（コードと名前と英語名）
echo "3. EN版を生成中..."
python jsic.py --format en -o jsic-en.json 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ jsic-en.json を生成しました"
else
    echo "✗ EN版の生成に失敗しました"
    exit 1
fi

echo ""
echo "=== 生成完了 ==="
echo ""
echo "生成されたファイル:"
ls -lh jsic-full.json jsic-simple.json jsic-en.json 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "JSONの構造を確認:"
echo "  jq '.major_categories | length' jsic-full.json   # 大分類の数"
echo "  jq '.major_categories[0]' jsic-simple.json       # 最初の大分類"
