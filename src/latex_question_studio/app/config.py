"""Application paths; secrets are never part of this configuration."""
from dataclasses import dataclass
from pathlib import Path
import json
import os

@dataclass(frozen=True)
class AppConfig:
    data_dir: Path
    theme: str = "dark"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "studio.db"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @classmethod
    def load(cls, data_dir: Path | None = None) -> "AppConfig":
        root = Path(data_dir) if data_dir else Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LaTeXQuestionStudio"
        root = root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        path = root / "settings.json"
        if path.exists():
            settings = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(settings, dict) or settings.get("version") != 1:
                raise ValueError("Unsupported settings format")
            theme = settings.get("theme", "dark")
            if theme not in ("dark", "light"):
                raise ValueError("Invalid theme")
            return cls(root, theme)
        return cls(root)

    def save(self) -> None:
        if self.theme not in ("dark", "light"):
            raise ValueError("Invalid theme")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        target = self.data_dir / "settings.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps({"version": 1, "theme": self.theme}, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)
