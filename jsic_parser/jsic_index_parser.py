import re
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class JsicIndexEntry:
    """Represents a parsed JSIC index entry."""
    type: str  # "major", "middle", "minor", "detail"
    code: str  # "A", "01", "011", "0111", etc.
    name: str = ""  # 日本語名
    name_en: str = ""  # 英語名

    def __repr__(self):
        return f"JsicIndexEntry(type={self.type}, code={self.code}, name='{self.name}', name_en='{self.name_en}')"


class JsicIndexParser:
    """Parser for JSIC index that builds structured entries."""

    def __init__(self):
        # Pattern for major classification: 大分類Ａ－... or 大分類A－...
        self.major_pattern = re.compile(r'大分類([A-TＡ-Ｔ])[－-]')
        # Pattern for middle classification: 中分類01 or 中分類 01
        self.middle_pattern = re.compile(r'中分類\s*(\d{2})')
        # Pattern for code at start of line (3 or 4 digits)
        self.code_pattern = re.compile(r'^(\d{3,4})\s+')
        # Pattern for page number at end
        self.page_pattern = re.compile(r'[･\s]+(\d+)\s*$')
        # Pattern for dots
        self.dots_pattern = re.compile(r'[･]{2,}')

    def parse_index_lines(self, lines: List[str]) -> List[JsicIndexEntry]:
        """Parse index lines and return structured entries.

        Args:
            lines: List of text lines to parse

        Returns:
            List of JsicIndexEntry objects
        """
        entries = []
        current_entry: Optional[JsicIndexEntry] = None
        found_major = False  # Flag to skip lines until first major classification

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for major classification
            major_match = self.major_pattern.search(line)
            if major_match:
                found_major = True
                # Save previous entry if exists
                if current_entry:
                    entries.append(current_entry)

                # Extract major classification code (convert full-width to half-width)
                major_code = major_match.group(1)
                major_code = self._normalize_alpha(major_code)

                # Extract names from the line
                jp_name, en_name = self._extract_major_names(line)

                current_entry = JsicIndexEntry(
                    type="major",
                    code=major_code,
                    name=jp_name,
                    name_en=en_name
                )
                continue

            # Skip lines until we find first major classification
            if not found_major:
                continue

            # Check for middle classification
            middle_match = self.middle_pattern.search(line)
            if middle_match:
                # Save previous entry if exists
                if current_entry:
                    entries.append(current_entry)

                # Extract middle classification code
                middle_code = middle_match.group(1)

                # Extract names from the line
                jp_name, en_name = self._extract_middle_names(line)

                current_entry = JsicIndexEntry(
                    type="middle",
                    code=middle_code,
                    name=jp_name,
                    name_en=en_name
                )
                continue

            # Check for minor/detail classification (3 or 4-digit code at start)
            code_match = self.code_pattern.match(line)
            if code_match:
                code = code_match.group(1)

                # Save previous entry if exists
                if current_entry:
                    entries.append(current_entry)

                # Extract names
                remaining = line[code_match.end():]
                jp_name, en_name = self._extract_names_from_text(remaining)

                # Determine type: 3-digit = minor, 4-digit = detail
                entry_type = "minor" if len(code) == 3 else "detail"

                # Remove trailing parentheses from minor classification names
                # Only remove patterns like （01農業） or （02林業） where it starts with 2-digit code
                # Example: "管理、補助的経済活動を行う事業所（01農業）" -> "管理、補助的経済活動を行う事業所"
                # But keep patterns like "農業サービス業（園芸サービス業を除く）"
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

            # Check if this is a continuation line (no page number, just names)
            has_page = self.page_pattern.search(line)
            if not has_page and current_entry:
                # This is a continuation line - append to current entry
                line_stripped = line.strip()

                # Check if this line is primarily English (lowercase or uppercase start)
                # This handles cases like "ancillary economic activities" or "AGRICULTURE"
                # Also handle lines like "(soy sauce)" that are purely English with parentheses
                is_english_continuation = bool(re.match(r'^[a-zA-Z][a-zA-Z\s,\.\-&\(\)]+$', line_stripped)) or \
                                         bool(re.match(r'^\([a-zA-Z\s,\.\-&]+\)$', line_stripped))

                if is_english_continuation:
                    # Append to English name
                    if current_entry.name_en:
                        current_entry.name_en += " " + line_stripped
                    else:
                        current_entry.name_en = line_stripped
                else:
                    # Try to extract both names
                    # For continuation lines, also allow lowercase English starts
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

        # Add the last entry
        if current_entry:
            entries.append(current_entry)

        # Post-process entries
        for entry in entries:
            # Remove trailing parentheses from minor classification names
            # Only remove patterns like （01農業） or （01農業) where it starts with 2-digit code
            # Note: Some entries have mixed full-width/half-width parentheses
            if entry.type == "minor":
                # Try full-width closing parenthesis first
                entry.name = re.sub(r'（\d{2}[^）)]*）$', '', entry.name).strip()
                # Also try half-width closing parenthesis
                entry.name = re.sub(r'（\d{2}[^）)]*\)$', '', entry.name).strip()

            # Clean up Japanese names
            entry.name = self._clean_japanese_name(entry.name)

            # Clean up English names
            if entry.name_en:
                # Remove spaces inside parentheses
                entry.name_en = re.sub(r'\(\s+', '(', entry.name_en)
                entry.name_en = re.sub(r'\s+\)', ')', entry.name_en)
                # Convert Unicode to ASCII
                entry.name_en = self._clean_english_name(entry.name_en)

        return entries

    def _normalize_alpha(self, char: str) -> str:
        """Convert full-width alphabet to half-width."""
        # Full-width A-Z (U+FF21 to U+FF3A) to half-width
        if 'Ａ' <= char <= 'Ｚ':
            return chr(ord(char) - ord('Ａ') + ord('A'))
        return char

    def _clean_japanese_name(self, name: str) -> str:
        """Clean Japanese name: remove spaces, normalize parentheses and nakaguro."""
        # Remove spaces between Japanese characters
        import re
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

    def _clean_english_name(self, name: str) -> str:
        """Clean English name: convert Unicode characters to ASCII."""
        # Convert curly quotes to straight quotes using Unicode escapes
        # U+2018 ' (LEFT SINGLE QUOTATION MARK) → U+0027 '
        # U+2019 ' (RIGHT SINGLE QUOTATION MARK) → U+0027 '
        # U+201C " (LEFT DOUBLE QUOTATION MARK) → U+0022 "
        # U+201D " (RIGHT DOUBLE QUOTATION MARK) → U+0022 "
        name = name.replace('\u2018', "'").replace('\u2019', "'")
        name = name.replace('\u201C', '"').replace('\u201D', '"')

        # Convert full-width comma (，U+FF0C) to half-width
        name = name.replace('\uFF0C', ',')

        # Convert full-width dash (－ U+FF0D) to half-width hyphen
        name = name.replace('\uFF0D', '-')

        # Convert en dash (– U+2013) to hyphen
        name = name.replace('\u2013', '-')

        # Convert full-width parentheses to half-width
        name = name.replace('\uFF08', '(').replace('\uFF09', ')')

        # Convert horizontal bar (― U+2015) to hyphen
        name = name.replace('\u2015', '-')

        return name

    def _extract_major_names(self, line: str) -> tuple[str, str]:
        """Extract Japanese and English names from major classification line.

        Example: "小 ・ 細 大分類Ａ－農業、林業 A-AGRICULTURE AND FORESTRY ･･････････････ 99"
        """
        # Remove page number first
        line = self.page_pattern.sub('', line)
        # Remove dots
        line = self.dots_pattern.sub('', line)

        # Find the major classification marker and remove everything before it
        major_match = self.major_pattern.search(line)
        if major_match:
            # Get everything after "大分類X－"
            start_pos = major_match.end()
            text = line[start_pos:].strip()

            # Split by uppercase Latin alphabet (start of English name)
            # Look for pattern like "農業、林業 A-AGRICULTURE"
            jp_name, en_name = self._extract_names_from_text(text)

            # Remove leading "X-" from English name (e.g., "A-AGRICULTURE" -> "AGRICULTURE")
            en_name = re.sub(r'^[A-Z]-', '', en_name).strip()

            return jp_name, en_name

        return "", ""

    def _extract_middle_names(self, line: str) -> tuple[str, str]:
        """Extract Japanese and English names from middle classification line.

        Example: "分類番号 中分類01 農業 01 AGRICULTURE ･･････････････ 101"
        """
        # Remove page number first
        line = self.page_pattern.sub('', line)
        # Remove dots
        line = self.dots_pattern.sub('', line)

        # Find the middle classification marker and remove it
        middle_match = self.middle_pattern.search(line)
        if middle_match:
            # Get everything after "中分類XX"
            start_pos = middle_match.end()
            text = line[start_pos:].strip()

            # Extract names
            jp_name, en_name = self._extract_names_from_text(text)
            return jp_name, en_name

        return "", ""

    def _normalize_text(self, text: str) -> str:
        """Normalize full-width alphanumeric characters to half-width.

        Special handling: Full-width letter sequences adjacent to Japanese characters are NOT normalized.
        This preserves patterns like "ＰＨＳ電話機" while normalizing "Ｈead offices".

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        import re

        # Find sequences of full-width letters followed by Japanese characters
        # Pattern: one or more full-width letters followed by hiragana, katakana, or CJK
        # Mark these sequences to skip normalization
        skip_positions = set()
        pattern = re.compile(r'[Ａ-Ｚａ-ｚ]+[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]')
        for match in pattern.finditer(text):
            # Mark all positions of full-width letters in this match (excluding the Japanese char)
            for pos in range(match.start(), match.end() - 1):
                skip_positions.add(pos)

        result = []
        for i, char in enumerate(text):
            if i in skip_positions:
                # This full-width letter is part of a sequence before Japanese - keep as is
                result.append(char)
            elif 'Ａ' <= char <= 'Ｚ':
                # Normalize to half-width
                result.append(chr(ord(char) - ord('Ａ') + ord('A')))
            elif 'ａ' <= char <= 'ｚ':
                # Normalize to half-width
                result.append(chr(ord(char) - ord('ａ') + ord('a')))
            elif char == '．':  # Full-width period (U+FF0E)
                result.append('.')
            else:
                result.append(char)
        return ''.join(result)

    def _extract_names_from_text(self, text: str, allow_lowercase_english: bool = False) -> tuple[str, str]:
        """Extract Japanese and English names from text.

        Args:
            text: Text containing Japanese and/or English names
            allow_lowercase_english: If True, also match English text starting with lowercase

        Returns:
            Tuple of (japanese_name, english_name)
        """
        # Remove page number and dots
        text = self.page_pattern.sub('', text)
        text = self.dots_pattern.sub('', text).strip()

        if not text:
            return "", ""

        # Normalize full-width characters to half-width for English pattern matching
        # This allows matching English names that start with full-width letters (e.g., "Ｈead offices")
        # Later, _clean_japanese_name() will convert half-width letters back to full-width in Japanese text
        text = self._normalize_text(text)

        # Pattern to detect English text
        # Include apostrophe (') for possessives like "Fuller's earth"
        # Include double quotes (", ", ") for quoted terms like "Miso" (fermented soybean paste)
        # U+201C and U+201D are curly double quotes used in PDFs
        # U+2018 and U+2019 are curly single quotes (apostrophes) used in PDFs
        # U+00C0-U+00FF are accented Latin characters (É, è, ñ, etc.)
        # U+FF08 and U+FF09 are full-width parentheses （）
        # U+FF0C is full-width comma ，
        # U+FF0D is full-width dash －
        # U+2013 is en dash –
        if allow_lowercase_english:
            # For continuation lines: allow lowercase start
            english_pattern = re.compile(r'[A-Za-z\"\'\u2018\u2019\u201C\u00C0-\u00FF][A-Za-z0-9\s,\.\-\u2013&\(\)\'\u2018\u2019\"\u201C\u201D\u00C0-\u00FF\uFF08\uFF09\uFF0C\uFF0D]+')
        else:
            # For main lines: require uppercase, quote, or apostrophe start
            english_pattern = re.compile(r'[A-Z\"\'\u2018\u2019\u201C\u00C0-\u00FF][A-Za-z0-9\s,\.\-\u2013&\(\)\'\u2018\u2019\"\u201C\u201D\u00C0-\u00FF\uFF08\uFF09\uFF0C\uFF0D]+')
        english_matches = list(english_pattern.finditer(text))

        if english_matches:
            # Find the first substantial English match
            english_parts = []
            last_end = 0
            japanese_parts = []

            for match in english_matches:
                # Add Japanese part before this English match
                if match.start() > last_end:
                    jp_part = text[last_end:match.start()].strip()
                    # Remove any trailing numbers (like "01", "02")
                    jp_part = re.sub(r'\s*\d+\s*$', '', jp_part).strip()
                    # Remove any trailing quotes (for cases like '味そ製造業 "')
                    # Include curly quotes U+201C and U+201D
                    jp_part = re.sub(r'["\'\u201C\u201D]+$', '', jp_part).strip()
                    if jp_part and not jp_part.isdigit():
                        japanese_parts.append(jp_part)

                english_parts.append(match.group().strip())
                last_end = match.end()

            # Add remaining Japanese part after last English match
            if last_end < len(text):
                jp_part = text[last_end:].strip()
                jp_part = re.sub(r'\s*\d+\s*$', '', jp_part).strip()
                # Remove any trailing quotes (include curly quotes)
                jp_part = re.sub(r'["\'\u201C\u201D]+$', '', jp_part).strip()
                if jp_part and not jp_part.isdigit():
                    japanese_parts.append(jp_part)

            # Combine parts
            japanese_name = ''.join(japanese_parts)
            english_name = ' '.join(english_parts)

            return japanese_name, english_name
        else:
            # No English found, treat all as Japanese
            # Remove any trailing numbers
            japanese_name = re.sub(r'\s*\d+\s*$', '', text).strip()
            return japanese_name, ""
