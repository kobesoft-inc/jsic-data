"""
JSIC Hierarchy Builder - IndexパーサーとDetailパーサーの結果をマージして階層構造を構築
"""
from typing import List, Dict, Any
from .jsic_index_parser import JsicIndexEntry
from .jsic_detail_parser import JsicDetailEntry


class JsicHierarchyBuilder:
    """IndexパーサーとDetailパーサーの結果をマージし、階層構造のJSONを生成するクラス"""

    def __init__(self, format_type: str = 'full'):
        """
        Args:
            format_type: 出力形式 ('full', 'simple', 'en')
        """
        self.format_type = format_type
        self.warnings = []

    def merge_and_build_hierarchy(
        self,
        index_entries: List[JsicIndexEntry],
        detail_entries: List[JsicDetailEntry]
    ) -> Dict[str, Any]:
        """
        IndexとDetailのエントリーをマージし、階層構造を構築

        Args:
            index_entries: IndexParserからのエントリーリスト
            detail_entries: DetailParserからのエントリーリスト

        Returns:
            階層構造のdict {'major_categories': [...]}
        """
        # コードでエントリーを検索できるようにdict化
        detail_by_code = {entry.code: entry for entry in detail_entries}

        # 階層構造を構築（index_entriesの順序に基づく）
        major_categories = []
        current_major = None
        current_middle = None
        current_minor = None

        for entry in index_entries:
            if entry.type == "major":
                # 新しいmajor category
                current_major = self._merge_entry(entry, detail_by_code.get(entry.code))
                current_major['middle_categories'] = []
                major_categories.append(current_major)
                current_middle = None
                current_minor = None

            elif entry.type == "middle":
                # 新しいmiddle category（現在のmajorに属する）
                if current_major is not None:
                    current_middle = self._merge_entry(entry, detail_by_code.get(entry.code))
                    current_middle['minor_categories'] = []
                    current_major['middle_categories'].append(current_middle)
                    current_minor = None

            elif entry.type == "minor":
                # 新しいminor category（現在のmiddleに属する）
                if current_middle is not None:
                    current_minor = self._merge_entry(entry, detail_by_code.get(entry.code))
                    current_minor['detail_categories'] = []
                    current_middle['minor_categories'].append(current_minor)

            elif entry.type == "detail":
                # 新しいdetail category（現在のminorに属する）
                if current_minor is not None:
                    detail = self._merge_entry(entry, detail_by_code.get(entry.code))
                    current_minor['detail_categories'].append(detail)

        return {'major_categories': major_categories}

    def _merge_entry(self, index_entry: JsicIndexEntry, detail_entry: JsicDetailEntry = None) -> Dict[str, Any]:
        """
        1つのエントリーをマージする（出力形式に応じてフィールドを選択）

        Args:
            index_entry: IndexParserからのエントリー
            detail_entry: DetailParserからのエントリー（存在する場合）

        Returns:
            マージされたエントリーのdict
        """
        if index_entry and detail_entry:
            # 両方のパーサーにこのコードがある - 名前が一致するかチェック
            if index_entry.name != detail_entry.name:
                self.warnings.append({
                    'code': index_entry.code,
                    'type': index_entry.type,
                    'index_name': index_entry.name,
                    'detail_name': detail_entry.name
                })

            # 出力形式に応じてフィールドを選択
            if self.format_type == 'simple':
                return {
                    'code': index_entry.code,
                    'name': index_entry.name
                }
            elif self.format_type == 'en':
                return {
                    'code': index_entry.code,
                    'name': index_entry.name,
                    'name_en': index_entry.name_en
                }
            else:  # full
                result = {
                    'code': index_entry.code,
                    'name': index_entry.name,
                    'name_en': index_entry.name_en
                }
                # 空でないフィールドのみ追加
                if detail_entry.description:
                    result['description'] = detail_entry.description
                if detail_entry.included_examples:
                    result['included_examples'] = detail_entry.included_examples
                if detail_entry.excluded_examples:
                    result['excluded_examples'] = detail_entry.excluded_examples
                return result
        elif index_entry:
            # Index parserにのみ存在
            self.warnings.append({
                'code': index_entry.code,
                'type': index_entry.type,
                'index_name': index_entry.name,
                'detail_name': None
            })

            if self.format_type == 'simple':
                return {
                    'code': index_entry.code,
                    'name': index_entry.name
                }
            elif self.format_type == 'en':
                return {
                    'code': index_entry.code,
                    'name': index_entry.name,
                    'name_en': index_entry.name_en
                }
            else:  # full
                # detailがない場合は、code, name, name_enのみ
                return {
                    'code': index_entry.code,
                    'name': index_entry.name,
                    'name_en': index_entry.name_en
                }
        else:
            # Detail parserにのみ存在
            self.warnings.append({
                'code': detail_entry.code,
                'type': detail_entry.type,
                'index_name': None,
                'detail_name': detail_entry.name
            })

            if self.format_type == 'simple':
                return {
                    'code': detail_entry.code,
                    'name': detail_entry.name
                }
            elif self.format_type == 'en':
                result = {
                    'code': detail_entry.code,
                    'name': detail_entry.name
                }
                # name_enが空でなければ追加
                if detail_entry.name_en:
                    result['name_en'] = detail_entry.name_en
                return result
            else:  # full
                result = {
                    'code': detail_entry.code,
                    'name': detail_entry.name
                }
                # 空でないフィールドのみ追加
                if detail_entry.name_en:
                    result['name_en'] = detail_entry.name_en
                if detail_entry.description:
                    result['description'] = detail_entry.description
                if detail_entry.included_examples:
                    result['included_examples'] = detail_entry.included_examples
                if detail_entry.excluded_examples:
                    result['excluded_examples'] = detail_entry.excluded_examples
                return result

    def get_warnings(self) -> List[Dict[str, Any]]:
        """
        マージ中に発見された警告（名前の不一致など）を取得

        Returns:
            警告のリスト
        """
        return self.warnings
