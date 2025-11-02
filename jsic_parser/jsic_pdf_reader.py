import re
from pathlib import Path
from typing import List
import requests
import pdfplumber


class JsicPdfReader:
    """PDFを読み込み、テキストを抽出し、正誤表を適用するクラス"""

    # 正誤表データ（組み込み）
    CORRECTIONS = [
        {
            "pattern": "定期観光バス業；［4311］",
            "replacement": "定期観光バス業［4311］",
            "description": "除外例の形式エラー修正（；を削除）"
        },
        {
            "pattern": "醸造酒類製造業（果実酒、清酒を除く。）",
            "replacement": "醸造酒類製造業（果実酒、清酒を除く）",
            "description": "末尾の句点削除"
        },
        {
            "pattern": "Ｈead offices primarily engaged in managerial operations",
            "replacement": "Head offices primarily engaged in managerial operations",
            "description": "全角Ｈを半角Hに修正"
        }
    ]

    def __init__(self, pdf_url: str, pdf_path: str = "tmp/jsic.pdf"):
        self.pdf_url = pdf_url
        self.pdf_path = Path(pdf_path)
        self.pages_data = None

        # PDFをダウンロード（キャッシュがなければ）
        self._download_pdf()

        # PDFからテキストを抽出
        self._extract_text()

    def _download_pdf(self):
        """Download PDF from URL if not already cached."""
        if self.pdf_path.exists():
            print(f"Using cached PDF: {self.pdf_path}")
            return

        # tmpディレクトリを作成（存在しなければ）
        self.pdf_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Downloading PDF from {self.pdf_url}...")
        response = requests.get(self.pdf_url)
        response.raise_for_status()

        with open(self.pdf_path, 'wb') as f:
            f.write(response.content)
        print(f"PDF saved to {self.pdf_path}")

    def _remove_page_number_noise(self, text: str) -> str:
        """Remove '- ページ番号 -' pattern from text."""
        # Remove patterns like "- 1 -", "- 2 -", "- 10 -" etc.
        cleaned_text = re.sub(r'-\s*\d+\s*-', '', text)
        return cleaned_text

    def _extract_text(self):
        """PDFからテキストを抽出"""
        print(f"Extracting text from PDF...")
        self.pages_data = []

        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    # ページ番号ノイズを除去
                    cleaned_text = self._remove_page_number_noise(text)
                    self.pages_data.append({
                        "page": page_num,
                        "content": cleaned_text
                    })

        print(f"Extracted {len(self.pages_data)} pages")

    def read_page(self, page_number: int) -> list[str]:
        """Read text from a specific page number.

        Args:
            page_number: The page number to read (1-indexed)

        Returns:
            List of text lines from the page
        """
        for page in self.pages_data:
            if page["page"] == page_number:
                # Split content by newlines and return as list
                return page["content"].split('\n')

        raise ValueError(f"Page {page_number} not found")

    def read_pages(self, start_page: int, end_page: int) -> list[str]:
        """指定された範囲のページからテキストを読み込み、正誤表を適用

        Args:
            start_page: 開始ページ番号（1から始まる、含む）
            end_page: 終了ページ番号（1から始まる、含む）

        Returns:
            範囲内の全ページのテキスト行のリスト（正誤表適用済み）
        """
        if start_page < 1 or end_page < start_page:
            raise ValueError(f"Invalid page range: {start_page}-{end_page}")

        combined_content = []
        for page in self.pages_data:
            page_num = page["page"]
            if start_page <= page_num <= end_page:
                combined_content.append(page["content"])

        if not combined_content:
            raise ValueError(f"No pages found in range {start_page}-{end_page}")

        # 全ページを結合して改行で分割
        lines = '\n'.join(combined_content).split('\n')

        # 正誤表を適用
        corrected_lines = self._apply_corrections(lines)

        return corrected_lines

    def _apply_corrections(self, lines: List[str]) -> List[str]:
        """テキスト行に正誤表を適用

        Args:
            lines: テキスト行のリスト

        Returns:
            修正後のテキスト行のリスト
        """
        corrected_lines = []

        for line in lines:
            corrected_line = line

            for correction in self.CORRECTIONS:
                pattern = correction['pattern']
                replacement = correction['replacement']

                if pattern in corrected_line:
                    # 修正を適用
                    corrected_line = corrected_line.replace(pattern, replacement)

            corrected_lines.append(corrected_line)

        return corrected_lines

    def get_total_pages(self) -> int:
        """総ページ数を取得"""
        return len(self.pages_data)
