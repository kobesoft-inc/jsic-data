import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict
from pathlib import Path


@dataclass
class JsicEntry:
    """Represents a single JSIC (Japan Standard Industrial Classification) entry."""
    code: str  # 産業分類コード (3桁または4桁)
    major_classification_code: Optional[str] = None  # 大分類コード (例: "A", "B", "C")
    name: str = ""  # 日本語名
    english_name: str = ""  # 英語名
    description: str = ""  # 説明文

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'JsicEntry':
        """Create JsicEntry from dictionary."""
        return cls(**data)


class JsicData:
    """Manages JSIC data with storage and retrieval capabilities."""

    def __init__(self, data_file: str = "jsic-data.json"):
        self.data_file = Path(data_file)
        self.entries: Dict[str, JsicEntry] = {}  # key: code, value: JsicEntry

        # Load existing data if available
        if self.data_file.exists():
            self.load()

    def add_entry(self, code: str, major_classification_code: Optional[str] = None,
                  name: str = "", english_name: str = "", description: str = "") -> JsicEntry:
        """Add or update a JSIC entry.

        Args:
            code: 産業分類コード
            major_classification_code: 大分類コード
            name: 日本語名
            english_name: 英語名
            description: 説明文

        Returns:
            The created or updated JsicEntry
        """
        if code in self.entries:
            # Update existing entry
            entry = self.entries[code]
            if major_classification_code:
                entry.major_classification_code = major_classification_code
            if name:
                entry.name = name
            if english_name:
                entry.english_name = english_name
            if description:
                entry.description = description
        else:
            # Create new entry
            entry = JsicEntry(
                code=code,
                major_classification_code=major_classification_code,
                name=name,
                english_name=english_name,
                description=description
            )
            self.entries[code] = entry

        return entry

    def get_entry(self, code: str) -> Optional[JsicEntry]:
        """Get a JSIC entry by code.

        Args:
            code: 産業分類コード

        Returns:
            JsicEntry if found, None otherwise
        """
        return self.entries.get(code)

    def has_entry(self, code: str) -> bool:
        """Check if an entry exists.

        Args:
            code: 産業分類コード

        Returns:
            True if entry exists, False otherwise
        """
        return code in self.entries

    def append_name(self, code: str, text: str, separator: str = " ") -> bool:
        """Append text to the Japanese name of an entry.

        Args:
            code: 産業分類コード
            text: Text to append
            separator: Separator between existing and new text

        Returns:
            True if successful, False if entry not found
        """
        entry = self.get_entry(code)
        if entry is None:
            return False

        if entry.name:
            entry.name += separator + text
        else:
            entry.name = text

        return True

    def append_english_name(self, code: str, text: str, separator: str = " ") -> bool:
        """Append text to the English name of an entry.

        Args:
            code: 産業分類コード
            text: Text to append
            separator: Separator between existing and new text

        Returns:
            True if successful, False if entry not found
        """
        entry = self.get_entry(code)
        if entry is None:
            return False

        if entry.english_name:
            entry.english_name += separator + text
        else:
            entry.english_name = text

        return True

    def append_description(self, code: str, text: str, separator: str = "\n") -> bool:
        """Append text to the description of an entry.

        Args:
            code: 産業分類コード
            text: Text to append
            separator: Separator between existing and new text

        Returns:
            True if successful, False if entry not found
        """
        entry = self.get_entry(code)
        if entry is None:
            return False

        if entry.description:
            entry.description += separator + text
        else:
            entry.description = text

        return True

    def get_all_codes(self) -> list[str]:
        """Get all entry codes.

        Returns:
            List of all codes
        """
        return sorted(self.entries.keys())

    def get_entries_by_major_classification(self, major_code: str) -> list[JsicEntry]:
        """Get all entries for a specific major classification.

        Args:
            major_code: 大分類コード (例: "A", "B")

        Returns:
            List of entries in that major classification
        """
        return [
            entry for entry in self.entries.values()
            if entry.major_classification_code == major_code
        ]

    def save(self, file_path: Optional[str] = None):
        """Save data to JSON file.

        Args:
            file_path: Optional custom file path (defaults to self.data_file)
        """
        if file_path:
            save_path = Path(file_path)
        else:
            save_path = self.data_file

        # Convert all entries to dictionaries
        data = {
            code: entry.to_dict()
            for code, entry in self.entries.items()
        }

        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Saved {len(self.entries)} entries to {save_path}")

    def load(self, file_path: Optional[str] = None):
        """Load data from JSON file.

        Args:
            file_path: Optional custom file path (defaults to self.data_file)
        """
        if file_path:
            load_path = Path(file_path)
        else:
            load_path = self.data_file

        if not load_path.exists():
            print(f"File {load_path} does not exist")
            return

        with open(load_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Convert dictionaries to JsicEntry objects
        self.entries = {
            code: JsicEntry.from_dict(entry_data)
            for code, entry_data in data.items()
        }

        print(f"Loaded {len(self.entries)} entries from {load_path}")

    def get_statistics(self) -> dict:
        """Get statistics about the data.

        Returns:
            Dictionary with statistics
        """
        total_entries = len(self.entries)
        entries_with_name = sum(1 for e in self.entries.values() if e.name)
        entries_with_english = sum(1 for e in self.entries.values() if e.english_name)
        entries_with_description = sum(1 for e in self.entries.values() if e.description)

        # Count by major classification
        major_classifications = {}
        for entry in self.entries.values():
            if entry.major_classification_code:
                major_classifications[entry.major_classification_code] = \
                    major_classifications.get(entry.major_classification_code, 0) + 1

        return {
            "total_entries": total_entries,
            "entries_with_name": entries_with_name,
            "entries_with_english_name": entries_with_english,
            "entries_with_description": entries_with_description,
            "major_classifications": major_classifications
        }

    def __len__(self) -> int:
        """Get the number of entries."""
        return len(self.entries)

    def __repr__(self) -> str:
        """String representation."""
        return f"JsicData(entries={len(self.entries)}, file={self.data_file})"
