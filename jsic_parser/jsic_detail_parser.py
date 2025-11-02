import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class JsicDetailEntry:
    """Represents a parsed JSIC detail entry with description."""
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
    """Parser for JSIC detail pages that extracts classification entries with descriptions."""

    def __init__(self):
        # Pattern for major classification: 大分類Ａ－農業、林業
        # U+FF0D (－) full-width hyphen-minus
        # U+002D (-) hyphen-minus
        # U+2015 (―) horizontal bar
        self.major_pattern = re.compile(r'^大分類([A-TＡ-Ｔ])[－\-―](.+)$')
        # Pattern for middle classification: 中分類01－農 業 (supports both half-width and full-width digits)
        self.middle_pattern = re.compile(r'^中分類([\d０-９]{2})[－\-―](.+)$')
        # Pattern for 総説 section
        self.sousetsu_pattern = re.compile(r'^総\s*説\s*$')
        # Pattern for 小分類 細分類 header
        self.bunrui_header_pattern = re.compile(r'^小分類\s+細分類')
        # Pattern for code at start of line (3 or 4 digits followed by space)
        self.code_pattern = re.compile(r'^([\d０-９]{3,4})\s+(.+)$')
        # Pattern for example lines (starting with ○ or ×)
        self.example_pattern = re.compile(r'^[○×]')

    def parse_detail_pages(self, lines: List[str]) -> List[JsicDetailEntry]:
        """Parse detail pages and return structured entries with descriptions.

        Args:
            lines: List of text lines from pages 105-534

        Returns:
            List of JsicDetailEntry objects
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

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Check for major classification
            major_match = self.major_pattern.match(line)
            if major_match:
                major_name = major_match.group(2).strip()

                # Skip if this is a reference (contains ［ or 〔, or ends with "に分類される")
                if ('［' in major_name or '〔' in major_name or
                    major_name.endswith('に分類される。') or major_name.endswith('に分類される')):
                    i += 1
                    continue

                # Save previous entry
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

            # Check for middle classification
            middle_match = self.middle_pattern.match(line)
            if middle_match:
                middle_name = middle_match.group(2).strip()

                # Skip if this is a reference (contains multiple middle class numbers like "、52－")
                # or contains brackets ［ or 〔
                if (re.search(r'、[\d０-９]{2}[－-]', middle_name) or
                    '［' in middle_name or '〔' in middle_name):
                    i += 1
                    continue

                # Save previous entry
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

            # Check for 総説
            if self.sousetsu_pattern.match(line):
                in_sousetsu = True
                in_bunrui_section = False
                i += 1
                continue

            # Check for 小分類 細分類 header
            if self.bunrui_header_pattern.match(line):
                # Save the major/middle entry with its description
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

            # If we're in 総説, accumulate description for major/middle
            if in_sousetsu and current_entry:
                # Skip header lines like "番 号 番 号"
                if not re.match(r'^[番号\s]+$', line):
                    # Check if this is an example line
                    if line.startswith('○'):
                        current_included_lines.append(line)
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

            # Check for minor/detail classification (in bunrui section)
            if in_bunrui_section:
                code_match = self.code_pattern.match(line)
                if code_match:
                    code = self._normalize_digits(code_match.group(1))
                    name = code_match.group(2).strip()

                    # Skip if this is a reference in description (starts with conjunctions/particles)
                    if (name.startswith('又は') or name.startswith('に、') or
                        name.startswith('に分類') or name.startswith('を除く') or
                        name.startswith('に設け')):
                        # This is part of description text, not a new entry
                        if current_entry:
                            current_description_lines.append(line)
                        i += 1
                        continue

                    # Save previous entry
                    if current_entry:
                        current_entry.description = self._clean_description('\n'.join(current_description_lines))
                        current_entry.included_examples = self._parse_included_examples(current_included_lines)
                        current_entry.excluded_examples = self._parse_excluded_examples(current_excluded_lines)
                        entries.append(current_entry)
                        current_description_lines = []
                        current_included_lines = []
                        current_excluded_lines = []

                    # Check if name continues on next line
                    # Only for incomplete parenthesis or very short continuation
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()

                        # Check if continuation is likely
                        is_continuation = False

                        # Case 1: Incomplete parenthesis
                        if next_line and '（' in name and '）' not in name:
                            # Next line should not be a description start
                            if (not self.code_pattern.match(next_line) and
                                not self.example_pattern.match(next_line) and
                                not next_line.startswith('主として') and
                                not next_line.startswith('この') and
                                not next_line.startswith('○') and
                                not next_line.startswith('×')):
                                is_continuation = True

                        # Case 2: Very short continuation (likely incomplete word like "造業")
                        elif (next_line and len(next_line) <= 10 and
                              not self.code_pattern.match(next_line) and
                              not self.example_pattern.match(next_line) and
                              not next_line.startswith('主として') and
                              not next_line.startswith('この')):
                            # Name should not end with complete ending
                            if name and not name.endswith(('業', '所', '類', '品', '等', '他', '外', '製造業', '工事業', 'サービス業')):
                                is_continuation = True

                        if is_continuation:
                            name += next_line
                            i += 1  # Skip the continuation line

                    # Determine type: 3-digit = minor, 4-digit = detail
                    entry_type = "minor" if len(code) == 3 else "detail"

                    current_entry = JsicDetailEntry(
                        type=entry_type,
                        code=code,
                        name=name,
                        description=""
                    )
                    i += 1
                    continue

                # If we have a current entry and this is not a code line, it's description or example
                if current_entry:
                    # Check if this is an example line
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

        # Save the last entry
        if current_entry:
            current_entry.description = self._clean_description('\n'.join(current_description_lines))
            current_entry.included_examples = self._parse_included_examples(current_included_lines)
            current_entry.excluded_examples = self._parse_excluded_examples(current_excluded_lines)
            entries.append(current_entry)

        # Post-process entries
        for entry in entries:
            # Clean up Japanese names
            entry.name = self._clean_japanese_name(entry.name)

            # Remove (XX name) pattern from minor classification names
            # Example: "管理、補助的経済活動を行う事業所（01農業）" -> "管理、補助的経済活動を行う事業所"
            if entry.type == "minor":
                # Pattern: （数字2桁 任意の文字）
                entry.name = re.sub(r'（\d{2}[^）]*）$', '', entry.name).strip()

        return entries

    def _normalize_alpha(self, char: str) -> str:
        """Convert full-width alphabet to half-width."""
        if 'Ａ' <= char <= 'Ｚ':
            return chr(ord(char) - ord('Ａ') + ord('A'))
        return char

    def _normalize_digits(self, text: str) -> str:
        """Convert full-width digits to half-width."""
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
        """Parse included example lines (○) into list of examples.

        Args:
            lines: List of lines starting with ○

        Returns:
            List of example strings (split by ；)
        """
        examples = []
        # Concatenate all lines and remove leading ○
        full_text = ' '.join(lines)
        full_text = re.sub(r'^○', '', full_text).strip()

        # Split by ；
        items = [item.strip() for item in full_text.split('；') if item.strip()]
        examples.extend(items)

        return examples

    def _parse_excluded_examples(self, lines: List[str]) -> List[dict]:
        """Parse excluded example lines (×) into list of examples with codes.

        Args:
            lines: List of lines starting with ×

        Returns:
            List of dicts with 'name' and 'codes' keys (codes is a list)
        """
        examples = []
        # Concatenate all lines and remove leading ×
        full_text = ' '.join(lines)
        full_text = re.sub(r'^×', '', full_text).strip()

        # Split by ；
        items = [item.strip() for item in full_text.split('；') if item.strip()]

        for item in items:
            # Extract all 2-4 digit codes from the entire item (including nested brackets)
            # They may be separated by "又は" or "、"
            codes = re.findall(r'\d{2,4}', item)

            # Extract name (part before the last bracket pair)
            # Support both full-width ［］〔〕 and half-width []
            match = re.match(r'^(.+?)[［\[〔]', item)
            if match:
                name = match.group(1).strip()
            else:
                # No brackets found - use entire item as name
                name = item.strip()

            if codes:
                examples.append({"name": name, "codes": codes})
            else:
                # No codes found - this might be a special case with text instead of code
                import sys
                print(f"WARNING: 除外例のコードが見つかりません: {item}", file=sys.stderr)
                examples.append({"name": name, "codes": []})

        return examples

    def _clean_japanese_name(self, name: str) -> str:
        """Clean Japanese name: remove spaces, normalize parentheses and nakaguro."""
        # Remove all spaces
        name = name.replace(' ', '').replace('　', '')
        # Convert half-width parentheses to full-width
        name = name.replace('(', '（').replace(')', '）')
        # Convert half-width nakaguro (･ U+FF65) to full-width (・ U+30FB)
        name = name.replace('･', '・')
        # Convert full-width hyphen (－ U+FF0D) to long vowel (ー U+30FC)
        name = name.replace('－', 'ー')
        # Convert half-width English letters to full-width
        result = []
        for char in name:
            if 'A' <= char <= 'Z':
                # Convert A-Z to Ａ-Ｚ (U+FF21 to U+FF3A)
                result.append(chr(ord(char) - ord('A') + ord('Ａ')))
            elif 'a' <= char <= 'z':
                # Convert a-z to ａ-ｚ (U+FF41 to U+FF5A)
                result.append(chr(ord(char) - ord('a') + ord('ａ')))
            else:
                result.append(char)
        return ''.join(result)
