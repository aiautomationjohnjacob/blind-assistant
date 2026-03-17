"""
Second Brain Vault

Obsidian-compatible markdown vault with encryption at rest.
Provides voice-queryable personal knowledge base for blind users.

Storage format: Obsidian-compatible markdown files with YAML frontmatter.
The Obsidian app is NOT required — we use the file format only.
All files are stored encrypted; decrypted in memory only.

Per USER_STORIES.md:
- Dorothy: "remember my doctor's appointment is March 20th at 2pm"
- Alex: "What did I note about the renter's insurance claim last week?"
- Jordan: All queries available as text for braille display
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from blind_assistant.second_brain.encryption import VaultKey, decrypt_string, encrypt_string

logger = logging.getLogger(__name__)

# Subdirectories in the vault
VAULT_DIRS = {
    "daily": "daily",  # Daily notes
    "health": "health",  # Medications, appointments, conditions
    "people": "people",  # Contacts and relationships
    "tasks": "tasks",  # To-dos and follow-ups
    "finance": "finance",  # Financial notes (extra sensitive)
    "general": "general",  # Everything else
}


class EncryptedVault:
    """
    Encrypted markdown vault for personal knowledge storage.

    All files on disk are AES-256-GCM encrypted.
    Files are decrypted in memory only for processing.
    """

    def __init__(self, vault_path: Path, vault_key: VaultKey) -> None:
        self.vault_path = vault_path
        self.key = vault_key

        # Encrypted index: filename → list of keywords/tags
        # Allows search without decrypting all files
        self._index: dict[str, list[str]] = {}

    async def initialize(self) -> None:
        """Create vault directory structure if it doesn't exist."""
        self.vault_path.mkdir(parents=True, exist_ok=True)
        for subdir in VAULT_DIRS.values():
            (self.vault_path / subdir).mkdir(exist_ok=True)

        # Load search index
        await self._load_index()
        logger.info(f"Vault initialized at {self.vault_path}")

    async def add_note(
        self,
        content: str,
        category: str = "general",
        title: str | None = None,
    ) -> str:
        """
        Add a note to the vault.

        Args:
            content: The note content (plain text)
            category: Category subdirectory (health, finance, general, etc.)
            title: Optional title; auto-generated from date if not provided

        Returns:
            The note filename (for confirmation)
        """
        if not self.key.is_unlocked:
            raise RuntimeError("Vault is locked")

        now = datetime.now()
        if title is None:
            title = now.strftime("%Y-%m-%d %H:%M")

        # Build Obsidian-compatible markdown with YAML frontmatter
        frontmatter = {
            "date": now.isoformat(),
            "category": category,
            "title": title,
        }
        note_content = (
            f"---\n"
            f"date: {frontmatter['date']}\n"
            f"category: {frontmatter['category']}\n"
            f"title: {frontmatter['title']}\n"
            f"---\n\n"
            f"# {title}\n\n"
            f"{content}\n"
        )

        # Safe filename: date with microseconds + sanitized title
        # Microseconds ensure uniqueness when multiple notes are added in the same second
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:50]
        filename = f"{now.strftime('%Y%m%d_%H%M%S')}_{now.microsecond:06d}_{safe_title}.md.enc"

        subdir = VAULT_DIRS.get(category, "general")
        note_path = self.vault_path / subdir / filename

        # Encrypt and write
        encrypted = encrypt_string(note_content, self.key.get_key())
        note_path.write_bytes(encrypted)

        # Update search index
        keywords = self._extract_keywords(content + " " + title)
        self._index[str(note_path.relative_to(self.vault_path))] = keywords
        await self._save_index()

        logger.info(f"Note added: {filename}")
        return filename

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        """
        Search vault for notes matching a query.

        Args:
            query: Search query (natural language)
            limit: Maximum number of results

        Returns:
            List of note dicts with 'title', 'content', 'date', 'category'
        """
        if not self.key.is_unlocked:
            raise RuntimeError("Vault is locked")

        query_keywords = self._extract_keywords(query)
        if not query_keywords:
            return []

        # Score each note by keyword overlap
        scores: dict[str, int] = {}
        for rel_path, note_keywords in self._index.items():
            score = len(set(query_keywords) & set(note_keywords))
            if score > 0:
                scores[rel_path] = score

        # Get top results
        # Use explicit lambda to avoid mypy's overloaded-function ambiguity on scores.get
        top_paths = sorted(scores, key=lambda k: scores.get(k, 0), reverse=True)[:limit]

        results = []
        for rel_path in top_paths:
            note = await self._read_note(self.vault_path / rel_path)
            if note:
                results.append(note)

        return results

    async def _read_note(self, note_path: Path) -> dict | None:
        """Read and decrypt a note file."""
        try:
            encrypted = note_path.read_bytes()
            content = decrypt_string(encrypted, self.key.get_key())

            # Parse YAML frontmatter
            parts = content.split("---", 2)
            metadata: dict[str, object] = {}
            body = content
            if len(parts) >= 3:
                import yaml

                metadata = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()

            # Ensure date is always an ISO string (YAML may parse it as datetime)
            raw_date = metadata.get("date", "")
            if hasattr(raw_date, "isoformat"):
                raw_date = raw_date.isoformat()

            return {
                "title": metadata.get("title", note_path.stem),
                "content": body,
                "date": str(raw_date),
                "category": metadata.get("category", "general"),
            }
        except Exception as e:
            logger.error(f"Failed to read note {note_path}: {e}")
            return None

    async def _load_index(self) -> None:
        """Load the search index from disk (stored encrypted)."""
        index_path = self.vault_path / ".index.enc"
        if index_path.exists() and self.key.is_unlocked:
            try:
                encrypted = index_path.read_bytes()
                content = decrypt_string(encrypted, self.key.get_key())
                self._index = json.loads(content)
            except Exception as e:
                logger.warning(f"Could not load index, rebuilding: {e}")
                await self._rebuild_index()
        else:
            await self._rebuild_index()

    async def _save_index(self) -> None:
        """Save the search index to disk (encrypted)."""
        if not self.key.is_unlocked:
            return
        index_path = self.vault_path / ".index.enc"
        content = json.dumps(self._index)
        encrypted = encrypt_string(content, self.key.get_key())
        index_path.write_bytes(encrypted)

    async def _rebuild_index(self) -> None:
        """Rebuild search index by scanning all vault files."""
        self._index = {}
        for enc_file in self.vault_path.rglob("*.md.enc"):
            note = await self._read_note(enc_file)
            if note:
                keywords = self._extract_keywords(note["content"] + " " + note["title"])
                rel_path = str(enc_file.relative_to(self.vault_path))
                self._index[rel_path] = keywords
        await self._save_index()

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract searchable keywords from text."""
        import re

        # Remove markdown formatting
        text = re.sub(r"[#*_`\[\]()]", " ", text)
        # Lowercase and split
        words = text.lower().split()
        # Filter stop words and short words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "is",
            "was",
            "are",
            "were",
            "be",
            "been",
            "have",
            "had",
            "do",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "i",
            "me",
            "my",
            "we",
            "you",
            "it",
            "its",
        }
        return [w for w in words if len(w) > 2 and w not in stop_words and w.isalpha()]
