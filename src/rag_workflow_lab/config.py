"""Load scaffold settings without initializing models or external services."""

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class Settings:
    """Paths and project identity for the first development stage."""

    project_name: str
    config_path: Path
    sources_manifest: Path
    local_data_dir: Path


def load_settings(config_path: str | Path) -> Settings:
    """Read TOML settings; resolve data paths relative to the config file."""
    path = Path(config_path).resolve()
    with path.open("rb") as stream:
        data = tomllib.load(stream)

    try:
        project_name = data["project"]["name"]
        sources_manifest = data["paths"]["sources_manifest"]
        local_data_dir = data["paths"]["local_data_dir"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Config requires project.name and both paths settings.") from exc

    values = {
        "project.name": project_name,
        "paths.sources_manifest": sources_manifest,
        "paths.local_data_dir": local_data_dir,
    }
    for key, value in values.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string.")

    return Settings(
        project_name=project_name,
        config_path=path,
        sources_manifest=(path.parent / sources_manifest).resolve(),
        local_data_dir=(path.parent / local_data_dir).resolve(),
    )
