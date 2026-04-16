"""Knowledge base configuration management."""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class KBConfig:
    """Knowledge base configuration."""

    name: str
    topic: str
    kb_path: Path
    created: str
    last_compile: Optional[str] = None
    source_count: int = 0
    article_count: int = 0

    @classmethod
    def create(cls, kb_path: Path, name: str, topic: str) -> "KBConfig":
        """Create new KB configuration.

        Args:
            kb_path: Path to knowledge base directory
            name: KB name
            topic: Research topic

        Returns:
            New KBConfig instance
        """
        config = cls(
            name=name,
            topic=topic,
            kb_path=kb_path,
            created=datetime.now().isoformat()
        )
        config.save()
        return config

    @classmethod
    def load(cls, kb_path: Path) -> "KBConfig":
        """Load existing KB configuration.

        Args:
            kb_path: Path to knowledge base directory

        Returns:
            Loaded KBConfig instance
        """
        config_file = kb_path / ".kbconfig"
        if not config_file.exists():
            raise FileNotFoundError(f"No .kbconfig found in {kb_path}")

        data = json.loads(config_file.read_text(encoding='utf-8'))
        return cls(kb_path=kb_path, **data)

    def save(self) -> None:
        """Save configuration to .kbconfig file."""
        config_file = self.kb_path / ".kbconfig"
        data = asdict(self)
        # Remove kb_path from saved data
        data.pop("kb_path")
        config_file.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def update_stats(self, source_count: int, article_count: int) -> None:
        """Update statistics and save.

        Args:
            source_count: Number of sources in raw/
            article_count: Number of articles in wiki/
        """
        self.source_count = source_count
        self.article_count = article_count
        self.save()

    def mark_compiled(self) -> None:
        """Mark KB as compiled with current timestamp."""
        self.last_compile = datetime.now().isoformat()
        self.save()
