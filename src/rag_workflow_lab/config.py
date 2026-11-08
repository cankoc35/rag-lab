"""Load project and database settings without initializing external services."""

from collections.abc import Mapping
from dataclasses import dataclass, field
import os
from pathlib import Path
import tomllib
import re


@dataclass(frozen=True)
class DatabaseSettings:
    """PostgreSQL connection parameters; repr omits the password."""

    host: str
    port: int
    dbname: str
    user: str
    password: str = field(repr=False)
    connect_timeout: int = 5

    def connect_kwargs(self) -> dict[str, str | int]:
        """Return Psycopg keyword arguments, including the password; do not log."""
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
            "connect_timeout": self.connect_timeout,
        }


@dataclass(frozen=True)
class EmbeddingSettings:
    """An explicitly selected local model; reading settings never loads it."""

    model_id: str
    revision: str
    models_dir: Path
    device: str = "cpu"
    dimensions: int = 768
    max_tokens: int = 1024

    @property
    def model_dir(self) -> Path:
        return self.models_dir / self.model_id.replace("/", "--") / self.revision


@dataclass(frozen=True)
class Settings:
    """Paths and project identity for the first development stage."""

    project_name: str
    config_path: Path
    sources_manifest: Path
    local_data_dir: Path
    embedding: EmbeddingSettings | None = None


def load_database_settings(environ: Mapping[str, str] | None = None) -> DatabaseSettings:
    """Read POSTGRES_* from the process environment, without I/O or a DB call.

    An explicit mapping replaces the process environment for callers/tests.
    No .env file is loaded automatically. Credentials are passed as separate
    Psycopg keyword arguments, preserving password punctuation and whitespace.
    """
    environment = os.environ if environ is None else environ

    def text(key: str, default: str | None = None) -> str:
        value = environment.get(key, default)
        if not isinstance(value, str) or not value.strip() or "\x00" in value:
            raise ValueError(f"{key} must be a non-empty string without NUL characters.")
        return value

    def integer(key: str, default: int, maximum: int) -> int:
        value = text(key, str(default))
        # Bound the length before conversion; errors must never echo env values.
        if not re.fullmatch(r"[0-9]{1,10}", value) or not 1 <= int(value) <= maximum:
            raise ValueError(f"{key} must be an integer between 1 and {maximum}.")
        return int(value)

    return DatabaseSettings(
        host=text("POSTGRES_HOST", "127.0.0.1"),
        port=integer("POSTGRES_PORT", 5432, 65535),
        dbname=text("POSTGRES_DB", "rag_workflow_lab"),
        user=text("POSTGRES_USER", "rag_lab"),
        password=text("POSTGRES_PASSWORD"),
        connect_timeout=integer("POSTGRES_CONNECT_TIMEOUT", 5, 2147483647),
    )


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

    embedding = None
    if "embedding" in data:
        section = data["embedding"]
        try:
            for key in ("model_id", "revision", "models_dir"):
                if not isinstance(section[key], str) or not section[key].strip():
                    raise ValueError(f"embedding.{key} must be a non-empty string.")
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*/[a-zA-Z0-9][a-zA-Z0-9_.-]*", section["model_id"]):
                raise ValueError("embedding.model_id must be a repository identifier.")
            if not re.fullmatch(r"[a-f0-9]{40}", section["revision"]):
                raise ValueError("embedding.revision must be a pinned 40-character commit hash.")
            for key, default in (("dimensions", 768), ("max_tokens", 1024)):
                value = section.get(key, default)
                if type(value) is not int or value <= 0:
                    raise ValueError(f"embedding.{key} must be a positive integer.")
            if section.get("device", "cpu") != "cpu":
                raise ValueError("The first embedding adapter supports device='cpu' only.")
            embedding = EmbeddingSettings(
                model_id=section["model_id"], revision=section["revision"],
                models_dir=(path.parent / section["models_dir"]).resolve(),
                device=section.get("device", "cpu"), dimensions=section.get("dimensions", 768),
                max_tokens=section.get("max_tokens", 1024),
            )
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError("Config embedding section requires model_id, revision and models_dir.") from exc

    return Settings(
        project_name=project_name,
        config_path=path,
        sources_manifest=(path.parent / sources_manifest).resolve(),
        local_data_dir=(path.parent / local_data_dir).resolve(),
        embedding=embedding,
    )
