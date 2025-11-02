import json
import argparse
from jsic_parser import (
    JsicPdfReader,
    JsicIndexParser,
    JsicDetailParser,
    JsicHierarchyBuilder
)


def main():
    # コマンドライン引数のパース
    parser = argparse.ArgumentParser(description='JSIC PDF Parser - 日本標準産業分類PDFをパースしてJSONに変換')
    parser.add_argument('-o', '--output', default='jsic.json',
                        help='出力JSONファイル名 (デフォルト: jsic.json)')
    parser.add_argument('--format', choices=['full', 'simple', 'en'], default='full',
                        help='出力形式: full=詳細（説明・例含む）, simple=コードと名前のみ, en=コードと名前と英語名 (デフォルト: full)')
    args = parser.parse_args()

    print("=== JSIC PDF Parser ===\n")

    # 1. PDFリーダーを作成してPDFをロード
    pdf_url = "https://www.soumu.go.jp/main_content/000941216.pdf"
    reader = JsicPdfReader(pdf_url)
    print(f"Total pages: {reader.get_total_pages()}")

    # 2. 目次を読み込む（51-102ページ）
    print("\nReading table of contents (pages 51-102)...")
    toc_lines = reader.read_pages(51, 102)
    print(f"Read {len(toc_lines)} lines")

    # 3. インデックスをパース
    print("\nParsing index...")
    index_parser = JsicIndexParser()
    index_entries = index_parser.parse_index_lines(toc_lines)

    # 統計情報
    major_count = sum(1 for e in index_entries if e.type == "major")
    middle_count = sum(1 for e in index_entries if e.type == "middle")
    minor_count = sum(1 for e in index_entries if e.type == "minor")
    detail_count = sum(1 for e in index_entries if e.type == "detail")

    print(f"\nParsed {len(index_entries)} entries:")
    print(f"  Major classifications: {major_count}")
    print(f"  Middle classifications: {middle_count}")
    print(f"  Minor classifications: {minor_count}")
    print(f"  Detail classifications: {detail_count}")

    # 4. 詳細ページを読み込む（105-534ページ）
    print("\nReading detail pages (105-534)...")
    detail_lines = reader.read_pages(105, 534)
    print(f"Read {len(detail_lines)} lines")

    # 5. 詳細をパース
    print("\nParsing detail...")
    detail_parser = JsicDetailParser()
    detail_entries = detail_parser.parse_detail_pages(detail_lines)

    print(f"Parsed {len(detail_entries)} detail entries")

    # 6. IndexパーサーとDetailパーサーの結果をマージ（階層構造）
    print("\n=== Merging Index and Detail Results ===")
    builder = JsicHierarchyBuilder(format_type=args.format)
    merged_data = builder.merge_and_build_hierarchy(index_entries, detail_entries)
    warnings = builder.get_warnings()

    # 警告を表示
    if warnings:
        print(f"\n⚠ Found {len(warnings)} code/name differences:")
        for w in warnings:
            if w['index_name'] is None:
                print(f"  Code {w['code']} ({w['type']}): Only in Detail parser - '{w['detail_name']}'")
            elif w['detail_name'] is None:
                print(f"  Code {w['code']} ({w['type']}): Only in Index parser - '{w['index_name']}'")
            else:
                print(f"  Code {w['code']} ({w['type']}): Name mismatch")
                print(f"    Index:  '{w['index_name']}'")
                print(f"    Detail: '{w['detail_name']}'")
    else:
        print("✓ All codes and names match perfectly!")

    # 7. マージしたデータをJSONにエクスポート
    print(f"\nExporting merged data to {args.output}...")

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)

    print(f"✓ Exported {len(merged_data['major_categories'])} major categories to {args.output}")
    print(f"\nDone!")


if __name__ == '__main__':
    main()
