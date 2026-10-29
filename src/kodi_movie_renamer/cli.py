"""CLI interface for Kodi Movie Renamer."""

import logging
import sys
from pathlib import Path

import click

from .config import Config, get_config_path, load_config, save_config
from .movie_searcher import SearchResult, SyncMovieSearcher
from .renamer import MovieRenamer

logger = logging.getLogger(__name__)


@click.group()
@click.option(
    "-v", "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose logging"
)
@click.option(
    "-c", "--config",
    "config_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to config file (default: config.toml in current directory)"
)
@click.pass_context

def main(ctx: click.Context, verbose: bool, config_path: Path | None) -> None:
    """Kodi Movie Renamer - Rename movie files for Kodi video library."""
    # Set up logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Load config
    config_path = config_path or get_config_path()
    
    try:
        config = load_config(config_path)
    except Exception as e:
        click.echo(f"Error loading config: {e}", err=True)
        sys.exit(1)
    
    # Store config in context
    ctx.obj = {"config": config, "config_path": config_path}


@main.command()
@click.argument("file_path", type=click.Path(path_type=Path, exists=True))
@click.option(
    "-d", "--dry-run",
    is_flag=True,
    default=False,
    help="Don't actually rename files, just show what would be done"
)
@click.option(
    "-y", "--yes",
    "auto_confirm",
    is_flag=True,
    default=False,
    help="Automatically use first match without prompting"
)
@click.option(
    "-f", "--format",
    "format_pattern",
    default=None,
    help="Override the filename format pattern"
)
@click.pass_context

def rename(
    ctx: click.Context,
    file_path: Path,
    dry_run: bool,
    auto_confirm: bool,
    format_pattern: str | None
) -> None:
    """Rename a single movie file."""
    config: Config = ctx.obj["config"]
    
    # Override format pattern if provided
    if format_pattern:
        config = Config(**config.model_dump())
        config.format_pattern = format_pattern
    
    renamer = MovieRenamer(config)
    
    click.echo(f"Processing: {file_path.name}")
    
    result = renamer.rename_file(
        file_path,
        dry_run=dry_run,
        interactive=not auto_confirm
    )
    
    if result.success:
        if result.new_path:
            action = "Would rename" if dry_run else "Renamed"
            click.echo(f"{action}: {result.original_path.name} -> {result.new_path.name}")
        else:
            click.echo(result.message)
    else:
        click.echo(f"Error: {result.message}", err=True)
        
        # If there were search results but user didn't select, show them
        if result.search_results:
            click.echo("\nPossible matches:")
            for i, sr in enumerate(result.search_results, 1):
                year_str = f" ({sr.year})" if sr.year else ""
                click.echo(f"  [{i}] {sr.title}{year_str} - {sr.source} ID: {sr.source_id}")


@main.command()
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path, exists=True))
@click.option(
    "-d", "--dry-run",
    is_flag=True,
    default=False,
    help="Don't actually rename files, just show what would be done"
)
@click.option(
    "-y", "--yes",
    "auto_confirm",
    is_flag=True,
    default=False,
    help="Automatically use first match without prompting"
)
@click.option(
    "-f", "--format",
    "format_pattern",
    default=None,
    help="Override the filename format pattern"
)
@click.option(
    "-r", "--recursive",
    is_flag=True,
    default=False,
    help="Process files recursively in directories"
)
@click.pass_context

def batch(
    ctx: click.Context,
    paths: tuple[Path, ...],
    dry_run: bool,
    auto_confirm: bool,
    format_pattern: str | None,
    recursive: bool
) -> None:
    """Rename multiple movie files."""
    config: Config = ctx.obj["config"]
    
    # Override format pattern if provided
    if format_pattern:
        config = Config(**config.model_dump())
        config.format_pattern = format_pattern
    
    renamer = MovieRenamer(config)
    
    # Collect all files
    all_files: list[Path] = []
    
    for path in paths:
        if path.is_file():
            all_files.append(path)
        elif path.is_dir() and recursive:
            all_files.extend(path.rglob("*"))
            # Filter to only files
            all_files = [f for f in all_files if f.is_file()]
    
    # Filter to common video file extensions
    video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.mpg', '.mpeg'}
    all_files = [f for f in all_files if f.suffix.lower() in video_extensions]
    
    if not all_files:
        click.echo("No video files found", err=True)
        return
    
    click.echo(f"Found {len(all_files)} video file(s) to process")
    
    if dry_run:
        click.echo("Dry run mode - no files will be renamed")
    
    results = renamer.rename_files(
        all_files,
        dry_run=dry_run,
        interactive=not auto_confirm
    )
    
    # Print summary
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count
    
    click.echo(f"\nSummary:")
    click.echo(f"  Successfully processed: {success_count}")
    click.echo(f"  Failed/skipped: {fail_count}")
    
    if fail_count > 0:
        click.echo("\nFailures:")
        for result in results:
            if not result.success:
                click.echo(f"  {result.original_path.name}: {result.message}")


@main.command()
@click.argument("query", nargs=-1)
@click.option(
    "-y", "--year",
    type=int,
    default=None,
    help="Filter by year"
)
@click.option(
    "-l", "--limit",
    type=int,
    default=10,
    help="Maximum number of results to show"
)
@click.pass_context

def search(ctx: click.Context, query: tuple[str, ...], year: int | None, limit: int) -> None:
    """Search for movies in the configured database."""
    config: Config = ctx.obj["config"]
    
    if not query:
        click.echo("Please provide a search query", err=True)
        return
    
    search_query = " ".join(query)
    
    searcher = SyncMovieSearcher(config)
    results = searcher.search(search_query, year)
    
    if not results:
        click.echo("No results found")
        return
    
    click.echo(f"Found {len(results)} result(s):")
    click.echo("-" * 80)
    
    for i, result in enumerate(results[:limit], 1):
        year_str = f" ({result.year})" if result.year else ""
        click.echo(f"[{i}] {result.title}{year_str}")
        click.echo(f"     Source: {result.source} | ID: {result.source_id}")
        if result.overview:
            overview = result.overview[:150] + "..." if len(result.overview) > 150 else result.overview
            click.echo(f"     Overview: {overview}")
        click.echo()
    
    if len(results) > limit:
        click.echo(f"... and {len(results) - limit} more results")


@main.command()
@click.option(
    "-l", "--list",
    "list_formats",
    is_flag=True,
    default=False,
    help="List available format patterns"
)
@click.pass_context

def format(ctx: click.Context, list_formats: bool) -> None:
    """Manage filename format patterns."""
    config: Config = ctx.obj["config"]
    
    if list_formats:
        click.echo("Available format patterns:")
        click.echo("-" * 80)
        click.echo(f"Current: {config.format_pattern}")
        click.echo()
        click.echo("Presets:")
        for name, pattern in config.pattern_presets.items():
            click.echo(f"  {name:20} -> {pattern}")
        click.echo()
        click.echo("Placeholders:")
        for placeholder, desc in config.format_placeholders.items():
            click.echo(f"  {{{placeholder}:20}} - {desc}")
        return
    
    click.echo(f"Current format pattern: {config.format_pattern}")


@main.command()
@click.option(
    "-s", "--set",
    "set_default",
    is_flag=True,
    default=False,
    help="Set as default source"
)
@click.pass_context

def source(ctx: click.Context, set_default: bool) -> None:
    """Manage data sources."""
    config: Config = ctx.obj["config"]
    config_path: Path = ctx.obj["config_path"]
    
    click.echo("Configured sources:")
    click.echo("-" * 80)
    
    for name, source_config in config.sources.items():
        active = " (active)" if name == config.active_source else ""
        enabled = " [enabled]" if source_config.enabled else " [disabled]"
        click.echo(f"  {name}{active}{enabled}")
        click.echo(f"    URL: {source_config.url}")
        if source_config.api_key:
            click.echo(f"    API Key: {'*' * len(source_config.api_key)}")
        else:
            click.echo(f"    API Key: Not configured")
        click.echo()
    
    if set_default:
        click.echo("Available sources to set as default:")
        for name in config.sources.keys():
            click.echo(f"  - {name}")
        # In interactive mode, would prompt user here


@main.command()
@click.option(
    "-i", "--init",
    "init_config",
    is_flag=True,
    default=False,
    help="Create a default config file"
)
@click.pass_context

def config_cmd(ctx: click.Context, init_config: bool) -> None:
    """Manage configuration."""
    config_path: Path = ctx.obj["config_path"]
    
    if init_config:
        config_path = config_path or Path("config.toml")
        
        if config_path.exists():
            click.confirm(
                f"Config file already exists at {config_path}. Overwrite?",
                abort=True
            )
        
        # Create default config
        from .config import get_default_config
        config = get_default_config()
        
        save_config(config, config_path)
        click.echo(f"Default config created at: {config_path}")
        return
    
    config: Config = ctx.obj["config"]
    click.echo("Current configuration:")
    click.echo("-" * 80)
    click.echo(f"Active source: {config.active_source}")
    click.echo(f"Format pattern: {config.format_pattern}")
    click.echo(f"Config file: {config_path}")


@main.command()
@click.argument("format_name")
@click.pass_context

def preset(ctx: click.Context, format_name: str) -> None:
    """Use a predefined format pattern."""
    config: Config = ctx.obj["config"]
    config_path: Path = ctx.obj["config_path"]
    
    if format_name not in config.pattern_presets:
        click.echo(f"Unknown preset: {format_name}", err=True)
        click.echo("Available presets:")
        for name in config.pattern_presets.keys():
            click.echo(f"  - {name}")
        return
    
    new_pattern = config.pattern_presets[format_name]
    config.format_pattern = new_pattern
    
    save_config(config, config_path)
    click.echo(f"Format pattern set to: {new_pattern}")


def entry_point() -> None:
    """Entry point for the CLI."""
    main(obj={})  # Initialize with empty obj


if __name__ == "__main__":
    entry_point()
