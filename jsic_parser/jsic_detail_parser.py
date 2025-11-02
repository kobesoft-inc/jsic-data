import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class JsicDetailEntry:
    """説明付きのパースされたJSIC詳細エントリーを表す"""
    type: str  # "major", "middle", "minor", "detail"
    code: str  # "A", "01", "011", "0111", etc.
    name: str  # 名前
    description: str = ""  # 説明文
    included_examples: List[str] = None  # ○で始まる含まれる業態のリスト
    excluded_examples: List[dict] = None  # ×で始まる除外される業態のリスト [{"name": "...", "codes": ["...", "..."]}]

    def __post_init__(self):
        if self.included_examples is None:
            self.included_examples = []
        if self.excluded_examples is None:
            self.excluded_examples = []

    def __repr__(self):
        desc_preview = self.description[:50] + "..." if len(self.description) > 50 else self.description
        return f"JsicDetailEntry(type={self.type}, code={self.code}, name='{self.name}', description='{desc_preview}')"


class JsicDetailParser:
    """説明付きの分類エントリーを抽出するJSIC詳細ページのパーサー"""

    def __init__(self):
        # 大分類のパターン: 大分類Ａ－農業、林業
        # U+FF0D (－) 全角ハイフン・マイナス
        # U+002D (-) ハイフン・マイナス
        # U+2015 (―) 水平線
        self.major_pattern = re.compile(r'^大分類([A-TＡ-Ｔ])[－\-―](.+)$')
        # 中分類のパターン: 中分類01－農 業 (半角と全角の数字に対応)
        self.middle_pattern = re.compile(r'^中分類([\d０-９]{2})[－\-―](.+)$')
        # 総説セクションのパターン
        self.sousetsu_pattern = re.compile(r'^総\s*説\s*$')
        # 小分類 細分類 ヘッダーのパターン
        self.bunrui_header_pattern = re.compile(r'^小分類\s+細分類')
        # 行頭のコードパターン（3桁または4桁の数字の後にスペース）
        self.code_pattern = re.compile(r'^([\d０-９]{3,4})\s+(.+)$')
        # 例示行のパターン（○ または × で始まる）
        self.example_pattern = re.compile(r'^[○×]')

    def parse_detail_pages(self, lines: List[str]) -> List[JsicDetailEntry]:
        """詳細ページをパースして説明付きの構造化されたエントリーを返す

        Args:
            lines: 105-534ページからのテキスト行のリスト

        Returns:
            JsicDetailEntryオブジェクトのリスト
        """
        entries = []
        current_entry: Optional[JsicDetailEntry] = None
        current_description_lines = []
        current_included_lines = []  # ○で始まる行
        current_excluded_lines = []  # ×で始まる行

        in_sousetsu = False
        in_bunrui_section = False

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # 空行をスキップ
            if not line:
                i += 1
                continue

            # 大分類をチェック
            major_match = self.major_pattern.match(line)
            if major_match:
                major_name = major_match.group(2).strip()

                # 参照の場合はスキップ（［ または 〔 を含む、または "に分類される" で終わる）
                if ('［' in major_name or '〔' in major_name or
                    major_name.endswith('に分類される。') or major_name.endswith('に分類される')):
                    i += 1
                    continue

                # 前のエントリーを保存
                if current_entry:
                    current_entry.description = self._clean_description('\n'.join(current_description_lines))
                    current_entry.included_examples = self._parse_included_examples(current_included_lines)
                    current_entry.excluded_examples = self._parse_excluded_examples(current_excluded_lines)
                    entries.append(current_entry)
                    current_description_lines = []
                    current_included_lines = []
                    current_excluded_lines = []

                major_code = self._normalize_alpha(major_match.group(1))

                current_entry = JsicDetailEntry(
                    type="major",
                    code=major_code,
                    name=major_name,
                    description=""
                )
                in_sousetsu = False
                in_bunrui_section = False
                i += 1
                continue

            # 中分類をチェック
            middle_match = self.middle_pattern.match(line)
            if middle_match:
                middle_name = middle_match.group(2).strip()

                # 参照の場合はスキップ（複数の中分類番号 "、52－" を含む、または括弧 ［ や 〔 を含む）
                if (re.search(r'、[\d０-９]{2}[－-]', middle_name) or
                    '［' in middle_name or '〔' in middle_name):
                    i += 1
                    continue

                # 前のエントリーを保存
                if current_entry:
                    current_entry.description = self._clean_description('\n'.join(current_description_lines))
                    current_entry.included_examples = self._parse_included_examples(current_included_lines)
                    current_entry.excluded_examples = self._parse_excluded_examples(current_excluded_lines)
                    entries.append(current_entry)
                    current_description_lines = []
                    current_included_lines = []
                    current_excluded_lines = []

                middle_code = self._normalize_digits(middle_match.group(1))

                current_entry = JsicDetailEntry(
                    type="middle",
                    code=middle_code,
                    name=middle_name,
                    description=""
                )
                in_sousetsu = False
                in_bunrui_section = False
                i += 1
                continue

            # 総説をチェック
            if self.sousetsu_pattern.match(line):
                in_sousetsu = True
                in_bunrui_section = False
                i += 1
                continue

            # 小分類 細分類 ヘッダーをチェック
            if self.bunrui_header_pattern.match(line):
                # 大分類/中分類エントリーを説明とともに保存
                if current_entry and in_sousetsu:
                    current_entry.description = self._clean_description('\n'.join(current_description_lines))
                    current_entry.included_examples = self._parse_included_examples(current_included_lines)
                    current_entry.excluded_examples = self._parse_excluded_examples(current_excluded_lines)
                    entries.append(current_entry)
                    current_entry = None
                    current_description_lines = []
                    current_included_lines = []
                    current_excluded_lines = []

                in_sousetsu = False
                in_bunrui_section = True
                i += 1
                continue

            # 総説にいる場合、大分類/中分類の説明を蓄積
            if in_sousetsu and current_entry:
                # "番 号 番 号" のようなヘッダー行をスキップ
                if not re.match(r'^[番号\s]+$', line):
                    # 例示行かチェック
                    if line.startswith('○'):
                        current_included_lines.append(line)
                        # 継続行をチェック
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j].strip()
                            if not next_line:
                                j += 1
                                continue
                            # Stop if next line starts with ○, ×, digit, or section keywords
                            if (next_line.startswith('○') or next_line.startswith('×') or
                                self.code_pattern.match(next_line) or
                                next_line.startswith('大分類') or next_line.startswith('中分類') or
                                next_line.startswith('小分類') or next_line.startswith('総') or
                                next_line.startswith('番 号')):
                                break
                            current_included_lines.append(next_line)
                            i = j
                            j += 1
                    elif line.startswith('×'):
                        current_excluded_lines.append(line)
                        # Check for continuation lines
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j].strip()
                            if not next_line:
                                j += 1
                                continue
                            # Stop if next line starts with ○, ×, digit, or section keywords
                            if (next_line.startswith('○') or next_line.startswith('×') or
                                self.code_pattern.match(next_line) or
                                next_line.startswith('大分類') or next_line.startswith('中分類') or
                                next_line.startswith('小分類') or next_line.startswith('総') or
                                next_line.startswith('番 号')):
                                break
                            current_excluded_lines.append(next_line)
                            i = j
                            j += 1
                    else:
                        current_description_lines.append(line)
                i += 1
                continue

            # 小分類/細分類をチェック（分類セクション内）
            if in_bunrui_section:
                code_match = self.code_pattern.match(line)
                if code_match:
                    code = self._normalize_digits(code_match.group(1))
                    name = code_match.group(2).strip()

                    # 説明内の参照の場合はスキップ（接続詞/助詞で始まる）
                    if (name.startswith('又は') or name.startswith('に、') or
                        name.startswith('に分類') or name.startswith('を除く') or
                        name.startswith('に設け')):
                        # これは説明文の一部であり、新しいエントリーではない
                        if current_entry:
                            current_description_lines.append(line)
                        i += 1
                        continue

                    # 前のエントリーを保存
                    if current_entry:
                        current_entry.description = self._clean_description('\n'.join(current_description_lines))
                        current_entry.included_examples = self._parse_included_examples(current_included_lines)
                        current_entry.excluded_examples = self._parse_excluded_examples(current_excluded_lines)
                        entries.append(current_entry)
                        current_description_lines = []
                        current_included_lines = []
                        current_excluded_lines = []

                    # 名前が次の行に続くかチェック
                    # 不完全な括弧または非常に短い継続の場合のみ
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()

                        # 継続の可能性をチェック
                        is_continuation = False

                        # ケース1: 不完全な括弧
                        if next_line and '（' in name and '）' not in name:
                            # 次の行は説明の開始ではないはず
                            if (not self.code_pattern.match(next_line) and
                                not self.example_pattern.match(next_line) and
                                not next_line.startswith('主として') and
                                not next_line.startswith('この') and
                                not next_line.startswith('○') and
                                not next_line.startswith('×')):
                                is_continuation = True

                        # ケース2: 非常に短い継続（"造業" のような不完全な単語の可能性）
                        elif (next_line and len(next_line) <= 10 and
                              not self.code_pattern.match(next_line) and
                              not self.example_pattern.match(next_line) and
                              not next_line.startswith('主として') and
                              not next_line.startswith('この')):
                            # 名前は完全な終わりで終わっていないはず
                            if name and not name.endswith(('業', '所', '類', '品', '等', '他', '外', '製造業', '工事業', 'サービス業')):
                                is_continuation = True

                        if is_continuation:
                            name += next_line
                            i += 1  # 継続行をスキップ

                    # タイプを判定: 3桁=小分類、4桁=細分類
                    entry_type = "minor" if len(code) == 3 else "detail"

                    current_entry = JsicDetailEntry(
                        type=entry_type,
                        code=code,
                        name=name,
                        description=""
                    )
                    i += 1
                    continue

                # 現在のエントリーがあり、これがコード行でない場合、説明または例示
                if current_entry:
                    # 例示行かチェック
                    if line.startswith('○'):
                        current_included_lines.append(line)
                        # Check for continuation lines (next line doesn't start with ○, ×, or digit)
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j].strip()
                            if not next_line:
                                j += 1
                                continue
                            # Stop if next line starts with ○, ×, digit, or section keywords
                            if (next_line.startswith('○') or next_line.startswith('×') or
                                self.code_pattern.match(next_line) or
                                next_line.startswith('大分類') or next_line.startswith('中分類') or
                                next_line.startswith('小分類') or next_line.startswith('総') or
                                next_line.startswith('番 号')):
                                break
                            # This is a continuation line
                            current_included_lines.append(next_line)
                            i = j  # Skip this line in main loop
                            j += 1
                    elif line.startswith('×'):
                        current_excluded_lines.append(line)
                        # Check for continuation lines (next line doesn't start with ○, ×, or digit)
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j].strip()
                            if not next_line:
                                j += 1
                                continue
                            # Stop if next line starts with ○, ×, digit, or section keywords
                            if (next_line.startswith('○') or next_line.startswith('×') or
                                self.code_pattern.match(next_line) or
                                next_line.startswith('大分類') or next_line.startswith('中分類') or
                                next_line.startswith('小分類') or next_line.startswith('総') or
                                next_line.startswith('番 号')):
                                break
                            # This is a continuation line
                            current_excluded_lines.append(next_line)
                            i = j  # Skip this line in main loop
                            j += 1
                    else:
                        current_description_lines.append(line)

            i += 1

        # 最後のエントリーを保存
        if current_entry:
            current_entry.description = self._clean_description('\n'.join(current_description_lines))
            current_entry.included_examples = self._parse_included_examples(current_included_lines)
            current_entry.excluded_examples = self._parse_excluded_examples(current_excluded_lines)
            entries.append(current_entry)

        # エントリーを後処理
        for entry in entries:
            # 日本語名をクリーンアップ
            entry.name = self._clean_japanese_name(entry.name)

            # 小分類名から (XX name) パターンを削除
            # 例: "管理、補助的経済活動を行う事業所（01農業）" -> "管理、補助的経済活動を行う事業所"
            if entry.type == "minor":
                # パターン: （数字2桁 任意の文字）
                entry.name = re.sub(r'（\d{2}[^）]*）$', '', entry.name).strip()

        return entries

    def _normalize_alpha(self, char: str) -> str:
        """全角アルファベットを半角に変換"""
        if 'Ａ' <= char <= 'Ｚ':
            return chr(ord(char) - ord('Ａ') + ord('A'))
        return char

    def _normalize_digits(self, text: str) -> str:
        """全角数字を半角に変換"""
        result = []
        for char in text:
            if '０' <= char <= '９':
                result.append(chr(ord(char) - ord('０') + ord('0')))
            else:
                result.append(char)
        return ''.join(result)

    def _clean_description(self, text: str) -> str:
        """説明文のクリーンアップ"""
        # 改行や連続する空白を削除（スペースを入れずに結合）
        text = re.sub(r'\s+', '', text)
        return text.strip()

    def _parse_included_examples(self, lines: List[str]) -> List[str]:
        """含まれる例示行（○）をパースして例示のリストにする

        Args:
            lines: ○ で始まる行のリスト

        Returns:
            例示文字列のリスト（；で分割）
        """
        examples = []
        # すべての行を連結し、先頭の ○ を削除
        full_text = ' '.join(lines)
        full_text = re.sub(r'^○', '', full_text).strip()

        # ； で分割
        items = [item.strip() for item in full_text.split('；') if item.strip()]
        examples.extend(items)

        return examples

    def _parse_excluded_examples(self, lines: List[str]) -> List[dict]:
        """除外例示行（×）をパースしてコード付きの例示のリストにする

        Args:
            lines: × で始まる行のリスト

        Returns:
            'name' と 'codes' キーを持つ辞書のリスト（codes はリスト）
        """
        examples = []
        # すべての行を連結し、先頭の × を削除
        full_text = ' '.join(lines)
        full_text = re.sub(r'^×', '', full_text).strip()

        # ； で分割
        items = [item.strip() for item in full_text.split('；') if item.strip()]

        for item in items:
            # 項目全体から2-4桁のコードをすべて抽出（ネストした括弧を含む）
            # "又は" や "、" で区切られている可能性あり
            codes = re.findall(r'\d{2,4}', item)

            # 名前を抽出（最後の括弧ペアの前の部分）
            # 全角 ［］〔〕 と半角 [] の両方に対応
            match = re.match(r'^(.+?)[［\[〔]', item)
            if match:
                name = match.group(1).strip()
            else:
                # 括弧が見つからない - 項目全体を名前として使用
                name = item.strip()

            if codes:
                examples.append({"name": name, "codes": codes})
            else:
                # コードが見つからない - コードの代わりにテキストがある特殊なケースかもしれない
                import sys
                print(f"WARNING: 除外例のコードが見つかりません: {item}", file=sys.stderr)
                examples.append({"name": name, "codes": []})

        return examples

    def _clean_japanese_name(self, name: str) -> str:
        """日本語名をクリーンアップ: スペースを削除、括弧と中黒を正規化"""
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
