# Kodi Movie Renamer

A CLI tool to rename movie files for Kodi video library using metadata from TheMovieDB or TheTVDB.

## Features

- **Automatic renaming**: Extract movie information from filenames and rename them using metadata from TheMovieDB or TheTVDB
- **Multiple data sources**: Support for TheMovieDB and TheTVDB (configurable)
- **Flexible format patterns**: Multiple predefined format patterns with customizable placeholders
- **Interactive disambiguation**: When multiple matches are found, the tool prompts you to select the correct one
- **Dry run mode**: Preview changes before applying them
- **Batch processing**: Process single files or entire directories

## Installation

### Prerequisites

- Python 3.10+
- API key from [TheMovieDB](https://www.themoviedb.org/) or [TheTVDB](https://thetvdb.com/)

### Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/kodi-movie-renamer.git
cd kodi-movie-renamer

# Install dependencies
uv sync

# Or install with pip
pip install -e .
```

## Usage

### Basic usage

```bash
# Rename a single file
kodi-movie-renamer rename "The Matrix (1999).mkv"

# Dry run (show what would be renamed)
kodi-movie-renamer rename --dry-run "The Matrix (1999).mkv"

# Automatically use first match without prompting
kodi-movie-renamer rename --yes "The Matrix (1999).mkv"

# Use a custom format pattern
kodi-movie-renamer rename -f "{title} ({year}) [{source_id}]" "The Matrix (1999).mkv"
```

### Batch processing

```bash
# Rename multiple files
kodi-movie-renamer batch movie1.mkv movie2.mp4 movie3.avi

# Process a directory recursively
kodi-movie-renamer batch /path/to/movies --recursive

# Dry run for batch processing
kodi-movie-renamer batch --dry-run /path/to/movies --recursive
```

### Search for movies

```bash
# Search for a movie
kodi-movie-renamer search "Inception"

# Search with year filter
kodi-movie-renamer search "Inception" --year 2010

# Limit results
kodi-movie-renamer search "Inception" --limit 5
```

### Configuration

```bash
# Initialize default config
kodi-movie-renamer config --init

# Show current configuration
kodi-movie-renamer config

# Show available format patterns
kodi-movie-renamer format --list

# Use a predefined format pattern
kodi-movie-renamer preset default
kodi-movie-renamer preset braces_source_equals

# Show configured sources
kodi-movie-renamer source
```

## Configuration File

The tool uses a TOML configuration file (`config.toml`). You can place it in:

1. Current directory
2. `~/.config/kodi-movie-renamer/config.toml`
3. `~/.kodi-movie-renamer.toml`

### Example Configuration

```toml
# Active source to use for searches
active_source = "TheMovieDB"

# Filename format pattern
format_pattern = "{title} ({year}) [{source_id}]"

# Data source configurations
[sources.TheMovieDB]
name = "TheMovieDB"
url = "https://api.themoviedb.org/3"
api_key = "your-tmdb-api-key"
enabled = true
search_endpoint = "/search/movie"
details_endpoint = "/movie/{id}"
id_field = "id"

[sources.TheTVDB]
name = "TheTVDB"
url = "https://api.thetvdb.com"
api_key = "your-tvdb-api-key"
enabled = true
search_endpoint = "/search/series"
details_endpoint = "/series/{id}"
id_field = "id"
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `active_source` | Name of the active source to use | `TheMovieDB` |
| `format_pattern` | Format pattern for renamed files | `{title} ({year}) [{source_id}]` |

#### Source Configuration

Each source under `[sources]` has the following options:

| Option | Description | Default |
|--------|-------------|---------|
| `name` | Name of the source | Required |
| `url` | Base URL for the API | Required |
| `api_key` | API key for authentication | `""` |
| `enabled` | Whether this source is enabled | `true` |
| `search_endpoint` | API endpoint for searching | `/search/movie` |
| `details_endpoint` | API endpoint for getting details | `/movie/{id}` |
| `id_field` | Field name for the ID in API responses | `id` |

## Format Patterns

### Available Placeholders

| Placeholder | Description |
|-------------|-------------|
| `{title}` | Movie title |
| `{year}` | Release year |
| `{source}` | Source name (e.g., TheMovieDB) |
| `{source_id}` | Source-specific ID (e.g., tmdb-12345, tvdb-67890) |
| `{imdb_id}` | IMDb ID |

### Predefined Patterns

The following format presets are available:

| Preset Name | Pattern | Example |
|-------------|---------|---------|
| `default` | `{title} ({year}) [{source_id}]` | `Inception (2010) [tmdb-27205]` |
| `braces` | `{title} ({year}) {{source_id}}` | `Inception (2010) {tmdb-27205}` |
| `source_equals` | `{title} ({year}) [source={source_id}]` | `Inception (2010) [source=tmdb-27205]` |
| `source_dash` | `{title} ({year}) [source-{source_id}]` | `Inception (2010) [source-tmdb-27205]` |
| `sourceid_equals` | `{title} ({year}) [sourceid={source_id}]` | `Inception (2010) [sourceid=tmdb-27205]` |
| `sourceid_dash` | `{title} ({year}) [sourceid-{source_id}]` | `Inception (2010) [sourceid-tmdb-27205]` |
| `braces_source_equals` | `{title} ({year}) {{source={source_id}}}` | `Inception (2010) {source=tmdb-27205}` |
| `braces_source_dash` | `{title} ({year}) {{source-{source_id}}}` | `Inception (2010) {source-tmdb-27205}` |
| `braces_sourceid_equals` | `{title} ({year}) {{sourceid={source_id}}}` | `Inception (2010) {sourceid=tmdb-27205}` |
| `braces_sourceid_dash` | `{title} ({year}) {{sourceid-{source_id}}}` | `Inception (2010) {sourceid-tmdb-27205}` |

## Getting API Keys

### TheMovieDB

1. Go to [TheMovieDB](https://www.themoviedb.org/)
2. Sign up for an account
3. Go to your account settings
4. Navigate to "API" section
5. Request an API key
6. Copy the "API Key (v3 auth)" value

### TheTVDB

1. Go to [TheTVDB](https://thetvdb.com/)
2. Sign up for an account
3. Go to your account settings
4. Navigate to "API" section
5. Generate a new API key
6. Copy the API key value

## Examples

### Example 1: Rename a single movie

```bash
# Original filename: The.Dark.Knight.2008.BlahBlah.mkv
kodi-movie-renamer rename "The.Dark.Knight.2008.BlahBlah.mkv"

# Output (assuming TheMovieDB finds "The Dark Knight (2008)"):
# Renamed: The.Dark.Knight.2008.BlahBlah.mkv -> The Dark Knight (2008) [tmdb-155].mkv
```

### Example 2: Batch rename all movies in a directory

```bash
# Process all video files in the current directory
kodi-movie-renamer batch --recursive .

# Output:
# Found 25 video file(s) to process
# ✓ The.Dark.Knight.2008.mkv -> The Dark Knight (2008) [tmdb-155].mkv
# ✓ Inception.2010.mkv -> Inception (2010) [tmdb-27205].mkv
# ...
# Summary:
#   Successfully processed: 25
#   Failed/skipped: 0
```

### Example 3: Use custom format

```bash
# Use braces instead of brackets
kodi-movie-renamer preset braces

# Or directly specify the format
kodi-movie-renamer rename -f "{title} ({year}) {{sourceid={source_id}}}" "Inception.mkv"

# Output:
# Renamed: Inception.mkv -> Inception (2010) {sourceid=tmdb-27205}.mkv
```

### Example 4: Dry run before actual rename

```bash
# Preview changes
kodi-movie-renamer rename --dry-run "Inception.mkv"

# Output:
# Would rename: Inception.mkv -> Inception (2010) [tmdb-27205].mkv

# If it looks good, do the actual rename
kodi-movie-renamer rename "Inception.mkv"
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/kodi-movie-renamer.git
cd kodi-movie-renamer

# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Run linting
uv run ruff check

# Run type checking
uv run mypy src/
```

### Project Structure

```
kodi-movie-renamer/
├── src/
│   └── kodi_movie_renamer/
│       ├── __init__.py
│       ├── cli.py          # CLI entry point
│       ├── config.py       # Configuration management
│       ├── movie_searcher.py # Movie/TV search functionality
│       ├── renamer.py      # File renaming logic
│       └── utils.py        # Helper functions
├── pyproject.toml
├── README.md
└── config.toml            # Default config template
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
