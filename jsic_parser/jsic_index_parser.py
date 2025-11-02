import re
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class JsicIndexEntry:
    """パースされたJSICインデックスエントリーを表す"""
    type: str  # "major", "middle", "minor", "detail"
    code: str  # "A", "01", "011", "0111", etc.
    name: str = ""  # 日本語名
    name_en: str = ""  # 英語名

    def __repr__(self):
        return f"JsicIndexEntry(type={self.type}, code={self.code}, name='{self.name}', name_en='{self.name_en}')"


class JsicIndexParser:
    """構造化されたエントリーを構築するJSICインデックスのパーサー"""

    def __init__(self):
        # 大分類のパターン: 大分類Ａ－... or 大分類A－...
        self.major_pattern = re.compile(r'大分類([A-TＡ-Ｔ])[－-]')
        # 中分類のパターン: 中分類01 or 中分類 01
        self.middle_pattern = re.compile(r'中分類\s*(\d{2})')
        # 行頭のコードパターン（3桁または4桁）
        self.code_pattern = re.compile(r'^(\d{3,4})\s+')
        # 行末のページ番号パターン
        self.page_pattern = re.compile(r'[･\s]+(\d+)\s*$')
        # ドットのパターン
        self.dots_pattern = re.compile(r'[･]{2,}')

    def parse_index_lines(self, lines: List[str]) -> List[JsicIndexEntry]:
        """インデックス行をパースして構造化されたエントリーを返す

        Args:
            lines: パースするテキスト行のリスト

        Returns:
            JsicIndexEntryオブジェクトのリスト
        """
        entries = []
        current_entry: Optional[JsicIndexEntry] = None
        found_major = False  # 最初の大分類が見つかるまで行をスキップするフラグ

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 大分類をチェック
            major_match = self.major_pattern.search(line)
            if major_match:
                found_major = True
                # 前のエントリーがあれば保存
                if current_entry:
                    entries.append(current_entry)

                # 大分類コードを抽出（全角を半角に変換）
                major_code = major_match.group(1)
                major_code = self._normalize_alpha(major_code)

                # 行から名前を抽出
                jp_name, en_name = self._extract_major_names(line)

                current_entry = JsicIndexEntry(
                    type="major",
                    code=major_code,
                    name=jp_name,
                    name_en=en_name
                )
                continue

            # 最初の大分類が見つかるまで行をスキップ
            if not found_major:
                continue

            # 中分類をチェック
            middle_match = self.middle_pattern.search(line)
            if middle_match:
                # 前のエントリーがあれば保存
                if current_entry:
                    entries.append(current_entry)

                # 中分類コードを抽出
                middle_code = middle_match.group(1)

                # 行から名前を抽出
                jp_name, en_name = self._extract_middle_names(line)

                current_entry = JsicIndexEntry(
                    type="middle",
                    code=middle_code,
                    name=jp_name,
                    name_en=en_name
                )
                continue

            # 小分類/細分類をチェック（行頭の3桁または4桁コード）
            code_match = self.code_pattern.match(line)
            if code_match:
                code = code_match.group(1)

                # 前のエントリーがあれば保存
                if current_entry:
                    entries.append(current_entry)

                # 名前を抽出
                remaining = line[code_match.end():]
                jp_name, en_name = self._extract_names_from_text(remaining)

                # タイプを判定: 3桁=小分類、4桁=細分類
                entry_type = "minor" if len(code) == 3 else "detail"

                # 小分類名から末尾の括弧を削除
                # （01農業）や（02林業）のように2桁コードで始まるパターンのみ削除
                # 例: "管理、補助的経済活動を行う事業所（01農業）" -> "管理、補助的経済活動を行う事業所"
                # ただし「農業サービス業（園芸サービス業を除く）」のようなパターンは保持
                if entry_type == "minor":
                    jp_name = re.sub(r'（\d{2}[^）)]*）$', '', jp_name).strip()
                    jp_name = re.sub(r'（\d{2}[^）)]*\)$', '', jp_name).strip()

                current_entry = JsicIndexEntry(
                    type=entry_type,
                    code=code,
                    name=jp_name,
                    name_en=en_name
                )
                continue

            # これが継続行かチェック（ページ番号なし、名前のみ）
            has_page = self.page_pattern.search(line)
            if not has_page and current_entry:
                # これは継続行 - 現在のエントリーに追加
                line_stripped = line.strip()

                # この行が主に英語かチェック（小文字または大文字で始まる）
                # "ancillary economic activities" や "AGRICULTURE" のようなケースを処理
                # また "(soy sauce)" のような括弧付きの純粋な英語行も処理
                is_english_continuation = bool(re.match(r'^[a-zA-Z][a-zA-Z\s,\.\-&\(\)]+$', line_stripped)) or \
                                         bool(re.match(r'^\([a-zA-Z\s,\.\-&]+\)$', line_stripped))

                if is_english_continuation:
                    # 英語名に追加
                    if current_entry.name_en:
                        current_entry.name_en += " " + line_stripped
                    else:
                        current_entry.name_en = line_stripped
                else:
                    # 両方の名前を抽出
                    # 継続行の場合、小文字で始まる英語も許可
                    jp_name, en_name = self._extract_names_from_text(line, allow_lowercase_english=True)

                    if jp_name:
                        if current_entry.name:
                            current_entry.name += jp_name
                        else:
                            current_entry.name = jp_name

                    if en_name:
                        if current_entry.name_en:
                            current_entry.name_en += " " + en_name
                        else:
                            current_entry.name_en = en_name

        # 最後のエントリーを追加
        if current_entry:
            entries.append(current_entry)

        # エントリーを後処理
        for entry in entries:
            # 小分類名から末尾の括弧を削除
            # （01農業）や（01農業)のように2桁コードで始まるパターンのみ削除
            # 注: 一部のエントリーは全角/半角括弧が混在
            if entry.type == "minor":
                # まず全角閉じ括弧を試す
                entry.name = re.sub(r'（\d{2}[^）)]*）$', '', entry.name).strip()
                # 半角閉じ括弧も試す
                entry.name = re.sub(r'（\d{2}[^）)]*\)$', '', entry.name).strip()

            # 日本語名をクリーンアップ
            entry.name = self._clean_japanese_name(entry.name)

            # 英語名をクリーンアップ
            if entry.name_en:
                # 括弧内のスペースを削除
                entry.name_en = re.sub(r'\(\s+', '(', entry.name_en)
                entry.name_en = re.sub(r'\s+\)', ')', entry.name_en)
                # UnicodeをASCIIに変換
                entry.name_en = self._clean_english_name(entry.name_en)

        return entries

    def _normalize_alpha(self, char: str) -> str:
        """全角アルファベットを半角に変換"""
        # 全角A-Z (U+FF21 to U+FF3A) を半角に変換
        if 'Ａ' <= char <= 'Ｚ':
            return chr(ord(char) - ord('Ａ') + ord('A'))
        return char

    def _clean_japanese_name(self, name: str) -> str:
        """日本語名をクリーンアップ: スペースを削除、括弧と中黒を正規化"""
        # 日本語文字間のスペースを削除
        import re
        # すべてのスペースを削除
        name = name.replace(' ', '').replace('　', '')
        # 半角括弧を全角に変換
        name = name.replace('(', '（').replace(')', '）')
        # 半角中黒 (･ U+FF65) を全角 (・ U+30FB) に変換
        name = name.replace('･', '・')
        # 全角ハイフン (－ U+FF0D) を長音 (ー U+30FC) に変換
        name = name.replace('－', 'ー')
        # 半角英字を全角に変換
        result = []
        for char in name:
            if 'A' <= char <= 'Z':
                # A-Z を Ａ-Ｚ (U+FF21 to U+FF3A) に変換
                result.append(chr(ord(char) - ord('A') + ord('Ａ')))
            elif 'a' <= char <= 'z':
                # a-z を ａ-ｚ (U+FF41 to U+FF5A) に変換
                result.append(chr(ord(char) - ord('a') + ord('ａ')))
            else:
                result.append(char)
        return ''.join(result)

    def _clean_english_name(self, name: str) -> str:
        """英語名をクリーンアップ: Unicode文字をASCIIに変換"""
        # カーリークォートを直線クォートに変換（Unicodeエスケープ使用）
        # U+2018 ' (LEFT SINGLE QUOTATION MARK) → U+0027 '
        # U+2019 ' (RIGHT SINGLE QUOTATION MARK) → U+0027 '
        # U+201C " (LEFT DOUBLE QUOTATION MARK) → U+0022 "
        # U+201D " (RIGHT DOUBLE QUOTATION MARK) → U+0022 "
        name = name.replace('\u2018', "'").replace('\u2019', "'")
        name = name.replace('\u201C', '"').replace('\u201D', '"')

        # 全角カンマ (，U+FF0C) を半角に変換
        name = name.replace('\uFF0C', ',')

        # 全角ダッシュ (－ U+FF0D) を半角ハイフンに変換
        name = name.replace('\uFF0D', '-')

        # エンダッシュ (– U+2013) をハイフンに変換
        name = name.replace('\u2013', '-')

        # 全角括弧を半角に変換
        name = name.replace('\uFF08', '(').replace('\uFF09', ')')

        # 水平線 (― U+2015) をハイフンに変換
        name = name.replace('\u2015', '-')

        return name

    def _extract_major_names(self, line: str) -> tuple[str, str]:
        """大分類行から日本語名と英語名を抽出

        例: "小 ・ 細 大分類Ａ－農業、林業 A-AGRICULTURE AND FORESTRY ･･････････････ 99"
        """
        # Remove page number first
        line = self.page_pattern.sub('', line)
        # Remove dots
        line = self.dots_pattern.sub('', line)

        # 大分類マーカーを見つけて、それより前をすべて削除
        major_match = self.major_pattern.search(line)
        if major_match:
            # "大分類X－" 以降のすべてを取得
            start_pos = major_match.end()
            text = line[start_pos:].strip()

            # 大文字ラテンアルファベットで分割（英語名の開始）
            # "農業、林業 A-AGRICULTURE" のようなパターンを探す
            jp_name, en_name = self._extract_names_from_text(text)

            # 英語名から先頭の "X-" を削除 (例: "A-AGRICULTURE" -> "AGRICULTURE")
            en_name = re.sub(r'^[A-Z]-', '', en_name).strip()

            return jp_name, en_name

        return "", ""

    def _extract_middle_names(self, line: str) -> tuple[str, str]:
        """中分類行から日本語名と英語名を抽出

        例: "分類番号 中分類01 農業 01 AGRICULTURE ･･････････････ 101"
        """
        # 最初にページ番号を削除
        line = self.page_pattern.sub('', line)
        # ドットを削除
        line = self.dots_pattern.sub('', line)

        # 中分類マーカーを見つけて削除
        middle_match = self.middle_pattern.search(line)
        if middle_match:
            # "中分類XX" 以降のすべてを取得
            start_pos = middle_match.end()
            text = line[start_pos:].strip()

            # 名前を抽出
            jp_name, en_name = self._extract_names_from_text(text)
            return jp_name, en_name

        return "", ""

    def _normalize_text(self, text: str) -> str:
        """全角英数字を半角に正規化

        特別な処理: 日本語文字に隣接する全角文字列は正規化されません。
        これにより "ＰＨＳ電話機" のようなパターンを保持しつつ "Ｈead offices" を正規化します。

        Args:
            text: 正規化するテキスト

        Returns:
            正規化されたテキスト
        """
        import re

        # 日本語文字の前にある全角文字列を見つける
        # パターン: 1つ以上の全角文字の後にひらがな、カタカナ、またはCJK
        # これらのシーケンスを正規化をスキップするようマーク
        skip_positions = set()
        pattern = re.compile(r'[Ａ-Ｚａ-ｚ]+[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]')
        for match in pattern.finditer(text):
            # このマッチ内の全角文字のすべての位置をマーク（日本語文字を除く）
            for pos in range(match.start(), match.end() - 1):
                skip_positions.add(pos)

        result = []
        for i, char in enumerate(text):
            if i in skip_positions:
                # この全角文字は日本語の前のシーケンスの一部 - そのまま保持
                result.append(char)
            elif 'Ａ' <= char <= 'Ｚ':
                # 半角に正規化
                result.append(chr(ord(char) - ord('Ａ') + ord('A')))
            elif 'ａ' <= char <= 'ｚ':
                # 半角に正規化
                result.append(chr(ord(char) - ord('ａ') + ord('a')))
            elif char == '．':  # 全角ピリオド (U+FF0E)
                result.append('.')
            else:
                result.append(char)
        return ''.join(result)

    def _extract_names_from_text(self, text: str, allow_lowercase_english: bool = False) -> tuple[str, str]:
        """テキストから日本語名と英語名を抽出

        Args:
            text: 日本語名と/または英語名を含むテキスト
            allow_lowercase_english: Trueの場合、小文字で始まる英語テキストもマッチ

        Returns:
            (japanese_name, english_name) のタプル
        """
        # ページ番号とドットを削除
        text = self.page_pattern.sub('', text)
        text = self.dots_pattern.sub('', text).strip()

        if not text:
            return "", ""

        # 英語パターンマッチング用に全角文字を半角に正規化
        # これにより全角文字で始まる英語名をマッチできる (例: "Ｈead offices")
        # 後で _clean_japanese_name() が日本語テキストの半角文字を全角に戻す
        text = self._normalize_text(text)

        # 英語テキストを検出するパターン
        # アポストロフィ (') を含める ("Fuller's earth" のような所有格用)
        # ダブルクォート (", ", ") を含める ("Miso" (fermented soybean paste) のような引用用語用)
        # U+201C と U+201D はPDFで使用されるカーリーダブルクォート
        # U+2018 と U+2019 はPDFで使用されるカーリーシングルクォート (アポストロフィ)
        # U+00C0-U+00FF はアクセント付きラテン文字 (É, è, ñ など)
        # U+FF08 と U+FF09 は全角括弧 （）
        # U+FF0C は全角カンマ ，
        # U+FF0D は全角ダッシュ －
        # U+2013 はエンダッシュ –
        if allow_lowercase_english:
            # 継続行用: 小文字開始を許可
            english_pattern = re.compile(r'[A-Za-z\"\'\u2018\u2019\u201C\u00C0-\u00FF][A-Za-z0-9\s,\.\-\u2013&\(\)\'\u2018\u2019\"\u201C\u201D\u00C0-\u00FF\uFF08\uFF09\uFF0C\uFF0D]+')
        else:
            # メイン行用: 大文字、クォート、またはアポストロフィ開始が必要
            english_pattern = re.compile(r'[A-Z\"\'\u2018\u2019\u201C\u00C0-\u00FF][A-Za-z0-9\s,\.\-\u2013&\(\)\'\u2018\u2019\"\u201C\u201D\u00C0-\u00FF\uFF08\uFF09\uFF0C\uFF0D]+')
        english_matches = list(english_pattern.finditer(text))

        if english_matches:
            # 最初の実質的な英語マッチを見つける
            english_parts = []
            last_end = 0
            japanese_parts = []

            for match in english_matches:
                # この英語マッチの前の日本語部分を追加
                if match.start() > last_end:
                    jp_part = text[last_end:match.start()].strip()
                    # 末尾の数字を削除 ("01", "02" など)
                    jp_part = re.sub(r'\s*\d+\s*$', '', jp_part).strip()
                    # 末尾のクォートを削除 ('味そ製造業 "' のようなケース用)
                    # カーリークォート U+201C と U+201D を含む
                    jp_part = re.sub(r'["\'\u201C\u201D]+$', '', jp_part).strip()
                    if jp_part and not jp_part.isdigit():
                        japanese_parts.append(jp_part)

                english_parts.append(match.group().strip())
                last_end = match.end()

            # 最後の英語マッチの後の残りの日本語部分を追加
            if last_end < len(text):
                jp_part = text[last_end:].strip()
                jp_part = re.sub(r'\s*\d+\s*$', '', jp_part).strip()
                # 末尾のクォートを削除 (カーリークォートを含む)
                jp_part = re.sub(r'["\'\u201C\u201D]+$', '', jp_part).strip()
                if jp_part and not jp_part.isdigit():
                    japanese_parts.append(jp_part)

            # 部分を結合
            japanese_name = ''.join(japanese_parts)
            english_name = ' '.join(english_parts)

            return japanese_name, english_name
        else:
            # 英語が見つからない、すべてを日本語として扱う
            # 末尾の数字を削除
            japanese_name = re.sub(r'\s*\d+\s*$', '', text).strip()
            return japanese_name, ""
