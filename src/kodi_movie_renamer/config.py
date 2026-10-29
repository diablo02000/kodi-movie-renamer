"""Configuration management for Kodi Movie Renamer."""

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SourceConfig(BaseModel):
    """Configuration for a movie/TV database source."""
    
    name: str = Field(..., description="Name of the source (e.g., TheMovieDB, TheTVDB)")
    url: str = Field(..., description="Base URL for the API")
    api_key: str | None = Field(default=None, description="API key for authentication")
    enabled: bool = Field(default=True, description="Whether this source is enabled")
    search_endpoint: str = Field(default="/search/movie", description="API endpoint for searching")
    details_endpoint: str = Field(default="/movie/{id}", description="API endpoint for getting details")
    id_field: str = Field(default="id", description="Field name for the ID in API responses")
    
    @property
    def resolved_api_key(self) -> str | None:
        """Get the API key, checking environment variables as fallback."""
        if self.api_key:
            return self.api_key
        
        # Check environment variables
        env_var_name = f"{self.name.upper()}_API_KEY"
        return os.getenv(env_var_name)
    
    @property
    def has_api_key(self) -> bool:
        """Check if API key is available."""
        return self.resolved_api_key is not None and len(self.resolved_api_key) > 0


class FormatPattern(BaseModel):
    """Filename format pattern configuration."""
    
    pattern: str = Field(..., description="Format pattern string")
    description: str | None = Field(default=None, description="Human-readable description")


class Config(BaseModel):
    """Main configuration model."""
    
    sources: dict[str, SourceConfig] = Field(
        default_factory=dict,
        description="Available data sources"
    )
    active_source: str = Field(
        default="TheMovieDB",
        description="Name of the active source to use"
    )
    format_pattern: str = Field(
        default="{title} ({year}) [{source_id}]",
        description="Format pattern for renaming files"
    )
    
    # Supported format placeholders
    format_placeholders: dict[str, str] = Field(
        default_factory=lambda: {
            "title": "Movie title",
            "year": "Release year",
            "source_id": "Source ID (e.g., tmdb-12345, tvdb-67890)",
            "source": "Source name",
            "imdb_id": "IMDb ID",
        },
        description="Available placeholders and their descriptions"
    )
    
    # Pattern presets for user convenience
    pattern_presets: dict[str, str] = Field(
        default_factory=lambda: {
            "default": "{title} ({year}) [{source_id}]",
            "braces": "{title} ({year}) {{source_id}}",
            "source_equals": "{title} ({year}) [source={source_id}]",
            "source_dash": "{title} ({year}) [source-{source_id}]",
            "sourceid_equals": "{title} ({year}) [sourceid={source_id}]",
            "sourceid_dash": "{title} ({year}) [sourceid-{source_id}]",
            "braces_source_equals": "{title} ({year}) {{source={source_id}}}",
            "braces_source_dash": "{title} ({year}) {{source-{source_id}}}",
            "braces_sourceid_equals": "{title} ({year}) {{sourceid={source_id}}}",
            "braces_sourceid_dash": "{title} ({year}) {{sourceid-{source_id}}}",
        },
        description="Predefined format patterns"
    )
    
    @field_validator("active_source")
    @classmethod
    def validate_active_source(cls, v: str, info) -> str:
        """Ensure active source exists in sources."""
        sources = info.data.get("sources", {})
        if v not in sources:
            available = list(sources.keys())
            raise ValueError(
                f"Active source '{v}' not found in sources. Available: {available}"
            )
        return v
    
    @property
    def active_source_config(self) -> SourceConfig | None:
        """Get the configuration for the active source."""
        return self.sources.get(self.active_source)


def get_default_config() -> Config:
    """Return a default configuration."""
    return Config(
        sources={
            "TheMovieDB": SourceConfig(
                name="TheMovieDB",
                url="https://api.themoviedb.org/3",
                api_key=None,
                enabled=True,
                search_endpoint="/search/movie",
                details_endpoint="/movie/{id}",
                id_field="id",
            ),
            "TheTVDB": SourceConfig(
                name="TheTVDB",
                url="https://api.thetvdb.com",
                api_key=None,
                enabled=True,
                search_endpoint="/search/series",
                details_endpoint="/series/{id}",
                id_field="id",
            ),
        },
        active_source="TheMovieDB",
        format_pattern="{title} ({year}) [{source_id}]",
    )


def load_config(config_path: Path | str | None = None) -> Config:
    """Load configuration from TOML file.
    
    Args:
        config_path: Path to the config file. If None, uses default locations.
    
    Returns:
        Config: Loaded configuration
    """
    import tomli
    
    config_path = Path(config_path or "config.toml")
    
    if not config_path.exists():
        return get_default_config()
    
    with open(config_path, "rb") as f:
        config_data = tomli.load(f)
    
    return Config(**config_data)


def save_config(config: Config, config_path: Path | str) -> None:
    """Save configuration to TOML file.
    
    Args:
        config: Configuration to save
        config_path: Path to save the config file
    """
    import tomli_w
    
    config_path = Path(config_path)
    config_data = config.model_dump(exclude_defaults=True)
    
    # Convert nested models to dicts
    if "sources" in config_data:
        config_data["sources"] = {
            name: source.model_dump(exclude_defaults=True)
            for name, source in config.sources.items()
        }
    
    with open(config_path, "wb") as f:
        tomli_w.dump(config_data, f)


def get_config_path() -> Path:
    """Get the default config path."""
    # Check for config in standard locations
    locations = [
        Path("config.toml"),
        Path.home() / ".config" / "kodi-movie-renamer" / "config.toml",
        Path("~/.kodi-movie-renamer.toml").expanduser(),
    ]
    
    for path in locations:
        if path.exists():
            return path
    
    return Path("config.toml")
