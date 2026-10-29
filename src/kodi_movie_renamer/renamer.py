"""File renaming logic for Kodi Movie Renamer."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Config
from .movie_searcher import SearchResult, SyncMovieSearcher

logger = logging.getLogger(__name__)


@dataclass
class RenameResult:
    """Result of a rename operation."""
    
    original_path: Path
    new_path: Path | None
    success: bool
    message: str
    search_results: list[SearchResult] | None = None
    chosen_result: SearchResult | None = None


class MovieRenamer:
    """Handles renaming of movie files based on metadata."""
    
    def __init__(self, config: Config):
        self.config = config
        self.searcher = SyncMovieSearcher(config)
    
    def extract_search_query(self, filename: str) -> tuple[str, int | None]:
        """Extract search query and optional year from filename.
        
        Args:
            filename: The original filename
        
        Returns:
            Tuple of (query, year) where year may be None
        """
        # Remove file extension
        stem = Path(filename).stem
        
        # Try to extract year from filename using common patterns
        year: int | None = None
        year_match = None
        
        # Look for year in parentheses, brackets, or braces
        year_match = re.search(r'[(\[{](\d{4})[)\]}]', stem)
        if not year_match:
            # Look for year separated by dots, dashes, or underscores
            year_match = re.search(r'(?:^|[._-])(\d{4})(?:$|[._-])', stem)
        
        if year_match:
            try:
                year = int(year_match.group(1))
                # Only accept years in reasonable range
                if not 1900 <= year <= 2100:
                    year = None
            except ValueError:
                pass
        
        # If we found a year, remove it from the stem by replacing it with space
        if year and year_match:
            # Get the full match (including delimiters)
            full_match = year_match.group(0)
            # Replace with space
            stem = stem.replace(full_match, ' ')
        
        # Clean up the stem: replace dots, dashes, underscores with spaces
        stem = re.sub(r'[._-]+', ' ', stem).strip()
        
        # Remove common quality indicators that aren't part of the title
        quality_patterns = [
            r'1080p', r'720p', r'480p', r'2160p',
            r'4K', r'8K', r'UHD', r'HD', r'SD',
            r'BLURAY', r'DVD', r'WEB',
            r'XVID', r'DIVX', r'H264', r'H265',
            r'XviD',
        ]
        for pattern in quality_patterns:
            stem = re.sub(r'\b' + pattern + r'\b', '', stem, flags=re.IGNORECASE)
        
        # Clean up again after removing quality indicators
        stem = re.sub(r'\s+', ' ', stem).strip()
        
        return stem, year
    
    def format_filename(
        self, 
        result: SearchResult, 
        pattern: str | None = None
    ) -> str:
        """Format filename using the configured pattern.
        
        Args:
            result: Search result with movie metadata
            pattern: Optional pattern override
        
        Returns:
            Formatted filename
        """
        pattern = pattern or self.config.format_pattern
        
        # Prepare replacement values
        replacements: dict[str, str | int] = {
            "title": result.title,
            "year": result.year or "",
            "source": result.source,
            "source_id": result.source_id,
            "imdb_id": result.imdb_id or "",
        }
        
        # Apply replacements
        filename = pattern
        for placeholder, value in replacements.items():
            filename = filename.replace("{" + placeholder + "}", str(value))
            filename = filename.replace("[" + placeholder + "]", str(value))
        
        # Clean up the filename: remove special characters, etc.
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()
        
        return filename
    
    def search_movie(self, filename: str) -> list[SearchResult]:
        """Search for movies matching the filename.
        
        Args:
            filename: The filename to search for
        
        Returns:
            List of search results
        """
        query, year = self.extract_search_query(filename)
        
        if not query:
            return []
        
        logger.info(f"Searching for: {query} (year: {year})")
        return self.searcher.search(query, year)
    
    def get_user_choice(self, results: list[SearchResult]) -> SearchResult | None:
        """Prompt user to choose from multiple search results.
        
        Args:
            results: List of search results
        
        Returns:
            Selected SearchResult or None if user cancels
        """
        print("\nMultiple matches found. Please select one:")
        print("-" * 80)
        
        for i, result in enumerate(results, 1):
            year_str = f" ({result.year})" if result.year else ""
            print(f"[{i}] {result.title}{year_str} - {result.source} ID: {result.source_id}")
            if result.overview:
                # Truncate overview to 100 chars
                overview = result.overview[:100] + "..." if len(result.overview) > 100 else result.overview
                print(f"     {overview}")
            print()
        
        print("[0] Cancel and skip this file")
        print("-" * 80)
        
        while True:
            try:
                choice = input("Enter your choice (number): ").strip()
                choice_num = int(choice)
                
                if choice_num == 0:
                    return None
                elif 1 <= choice_num <= len(results):
                    return results[choice_num - 1]
                else:
                    print(f"Please enter a number between 0 and {len(results)}")
            except ValueError:
                print("Please enter a valid number")
    
    def rename_file(
        self, 
        file_path: Path | str, 
        dry_run: bool = False,
        interactive: bool = True
    ) -> RenameResult:
        """Rename a movie file based on metadata.
        
        Args:
            file_path: Path to the file to rename
            dry_run: If True, don't actually rename the file
            interactive: If True, prompt user for disambiguation
        
        Returns:
            RenameResult with details about the operation
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return RenameResult(
                original_path=file_path,
                new_path=None,
                success=False,
                message=f"File not found: {file_path}"
            )
        
        # Search for the movie
        search_results = self.search_movie(file_path.name)
        
        if not search_results:
            return RenameResult(
                original_path=file_path,
                new_path=None,
                success=False,
                message="No matches found for the file",
                search_results=search_results
            )
        
        # If multiple results, ask user to choose
        chosen_result: SearchResult | None = None
        if len(search_results) == 1:
            chosen_result = search_results[0]
        elif interactive:
            chosen_result = self.get_user_choice(search_results)
        else:
            # Non-interactive mode: use first result
            chosen_result = search_results[0]
            logger.warning(f"Multiple matches found, using first: {chosen_result.title}")
        
        if not chosen_result:
            return RenameResult(
                original_path=file_path,
                new_path=None,
                success=False,
                message="No movie selected",
                search_results=search_results
            )
        
        # Format the new filename
        new_filename = self.format_filename(chosen_result)
        
        # Preserve the file extension
        new_stem = new_filename
        new_path = file_path.with_name(f"{new_stem}{file_path.suffix}")
        
        # Check if the new path already exists
        if new_path.exists():
            counter = 1
            while True:
                new_path = file_path.with_name(f"{new_stem} ({counter}){file_path.suffix}")
                if not new_path.exists():
                    break
                counter += 1
        
        # Perform the rename
        if dry_run:
            return RenameResult(
                original_path=file_path,
                new_path=new_path,
                success=True,
                message=f"Dry run: would rename to {new_path.name}",
                search_results=search_results,
                chosen_result=chosen_result
            )
        
        try:
            file_path.rename(new_path)
            return RenameResult(
                original_path=file_path,
                new_path=new_path,
                success=True,
                message=f"Renamed to {new_path.name}",
                search_results=search_results,
                chosen_result=chosen_result
            )
        except Exception as e:
            return RenameResult(
                original_path=file_path,
                new_path=new_path,
                success=False,
                message=f"Error renaming: {e}",
                search_results=search_results,
                chosen_result=chosen_result
            )
    
    def rename_files(
        self, 
        paths: list[Path | str], 
        dry_run: bool = False,
        interactive: bool = True
    ) -> list[RenameResult]:
        """Rename multiple files.
        
        Args:
            paths: List of file paths to rename
            dry_run: If True, don't actually rename files
            interactive: If True, prompt user for disambiguation
        
        Returns:
            List of RenameResult objects
        """
        results: list[RenameResult] = []
        
        for path in paths:
            result = self.rename_file(path, dry_run=dry_run, interactive=interactive)
            results.append(result)
            
            if result.success and result.new_path:
                logger.info(f"✓ {result.original_path.name} -> {result.new_path.name}")
            elif result.message:
                logger.warning(f"✗ {result.original_path.name}: {result.message}")
        
        return results
