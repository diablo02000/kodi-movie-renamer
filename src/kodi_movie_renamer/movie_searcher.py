"""Movie and TV show search functionality for TheMovieDB and TheTVDB."""

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import Config, SourceConfig

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result from a movie/TV database."""
    
    id: str | int
    title: str
    year: int | None = None
    overview: str | None = None
    poster_path: str | None = None
    source: str = ""
    source_id: str = ""
    imdb_id: str | None = None
    release_date: str | None = None
    vote_average: float | None = None
    media_type: str = "movie"  # movie or tv
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "id": self.id,
            "title": self.title,
            "year": self.year,
            "overview": self.overview,
            "poster_path": self.poster_path,
            "source": self.source,
            "source_id": self.source_id,
            "imdb_id": self.imdb_id,
            "release_date": self.release_date,
            "vote_average": self.vote_average,
            "media_type": self.media_type,
        }


@dataclass
class MovieSearcher:
    """Searches for movies and TV shows in configured databases."""
    
    config: Config
    client: httpx.AsyncClient = field(default_factory=lambda: httpx.AsyncClient())
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self) -> "MovieSearcher":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
    
    def get_active_source(self) -> SourceConfig | None:
        """Get the active source configuration."""
        return self.config.active_source_config
    
    async def search(self, query: str, year: int | None = None) -> list[SearchResult]:
        """Search for movies matching the query.
        
        Args:
            query: Search query (movie title or part of it)
            year: Optional year to filter results
        
        Returns:
            List of SearchResult objects
        """
        source_config = self.get_active_source()
        if not source_config:
            logger.error("No active source configured")
            return []
        
        try:
            if source_config.name.lower() == "themoviedb":
                results = await self._search_themoviedb(source_config, query, year)
            elif source_config.name.lower() == "thetvdb":
                results = await self._search_thetvdb(source_config, query, year)
            else:
                logger.error(f"Unknown source: {source_config.name}")
                return []
            
            return results
        except Exception as e:
            logger.error(f"Error searching {source_config.name}: {e}")
            return []
    
    async def _search_themoviedb(
        self, source: SourceConfig, query: str, year: int | None
    ) -> list[SearchResult]:
        """Search TheMovieDB for movies."""
        base_url = source.url.rstrip("/")
        endpoint = source.search_endpoint
        api_key = source.resolved_api_key or ""
        
        # For TheMovieDB, we need an API key
        if not api_key:
            logger.warning("TheMovieDB API key not configured. Set TMDB_API_KEY environment variable or add to config")
            return []
        
        url = f"{base_url}{endpoint}"
        
        params: dict[str, Any] = {
            "api_key": api_key,
            "query": query,
            "include_adult": "false",
        }
        
        if year:
            params["year"] = year
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results: list[SearchResult] = []
            for item in data.get("results", []):
                source_id = f"tmdb-{item.get(source.id_field, '')}"
                
                # Extract year from release_date
                release_date = item.get("release_date", "")
                year_val: int | None = None
                if release_date and len(release_date) >= 4:
                    try:
                        year_val = int(release_date[:4])
                    except ValueError:
                        pass
                
                result = SearchResult(
                    id=item.get("id", ""),
                    title=item.get("title", "") or item.get("name", ""),
                    year=year_val,
                    overview=item.get("overview"),
                    poster_path=item.get("poster_path"),
                    source=source.name,
                    source_id=source_id,
                    imdb_id=item.get("imdb_id"),
                    release_date=release_date,
                    vote_average=item.get("vote_average"),
                    media_type=item.get("media_type", "movie"),
                )
                results.append(result)
            
            return results
        except httpx.HTTPError as e:
            logger.error(f"TheMovieDB API error: {e}")
            return []
    
    async def _search_thetvdb(
        self, source: SourceConfig, query: str, year: int | None
    ) -> list[SearchResult]:
        """Search TheTVDB for series."""
        base_url = source.url.rstrip("/")
        endpoint = source.search_endpoint
        api_key = source.resolved_api_key or ""
        
        if not api_key:
            logger.warning("TheTVDB API key not configured. Set TVDB_API_KEY environment variable or add to config")
            return []
        
        url = f"{base_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
        
        params: dict[str, Any] = {
            "name": query,
        }
        
        try:
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            results: list[SearchResult] = []
            for item in data.get("data", []):
                source_id = f"tvdb-{item.get(source.id_field, '')}"
                
                # Extract year from first_air_date or similar
                release_date = item.get("firstAirDate", "") or item.get("first_air_date", "")
                year_val: int | None = None
                if release_date and len(release_date) >= 4:
                    try:
                        year_val = int(release_date[:4])
                    except ValueError:
                        pass
                
                result = SearchResult(
                    id=item.get("id", ""),
                    title=item.get("seriesName", "") or item.get("name", ""),
                    year=year_val,
                    overview=item.get("overview"),
                    poster_path=item.get("banner", "") or item.get("poster", ""),
                    source=source.name,
                    source_id=source_id,
                    imdb_id=item.get("imdbId", "") or item.get("imdb_id", ""),
                    release_date=release_date,
                    vote_average=item.get("siteRating"),
                    media_type="tv",
                )
                results.append(result)
            
            return results
        except httpx.HTTPError as e:
            logger.error(f"TheTVDB API error: {e}")
            return []
    
    async def get_details(self, source_id: str) -> dict[str, Any] | None:
        """Get detailed information for a specific movie/show.
        
        Args:
            source_id: The source-specific ID (e.g., "tmdb-12345")
        
        Returns:
            Dictionary with detailed information or None if not found
        """
        source_config = self.get_active_source()
        if not source_config:
            return None
        
        # Parse source_id to get the actual ID
        # Format: source-id or just id
        if "-" in source_id:
            _, id_part = source_id.split("-", 1)
        else:
            id_part = source_id
        
        try:
            if source_config.name.lower() == "themoviedb":
                return await self._get_themoviedb_details(source_config, id_part)
            elif source_config.name.lower() == "thetvdb":
                return await self._get_thetvdb_details(source_config, id_part)
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting details from {source_config.name}: {e}")
            return None
    
    async def _get_themoviedb_details(
        self, source: SourceConfig, id_part: str
    ) -> dict[str, Any] | None:
        """Get details from TheMovieDB."""
        base_url = source.url.rstrip("/")
        endpoint = source.details_endpoint.replace("{id}", id_part)
        api_key = source.resolved_api_key or ""
        
        if not api_key:
            logger.warning("TheMovieDB API key not configured")
            return None
        
        url = f"{base_url}{endpoint}"
        
        params = {
            "api_key": api_key,
            "append_to_response": "external_ids",
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return None
    
    async def _get_thetvdb_details(
        self, source: SourceConfig, id_part: str
    ) -> dict[str, Any] | None:
        """Get details from TheTVDB."""
        base_url = source.url.rstrip("/")
        endpoint = source.details_endpoint.replace("{id}", id_part)
        api_key = source.resolved_api_key or ""
        
        if not api_key:
            logger.warning("TheTVDB API key not configured")
            return None
        
        url = f"{base_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
        
        try:
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return None


class SyncMovieSearcher:
    """Synchronous wrapper for MovieSearcher."""
    
    def __init__(self, config: Config):
        self.config = config
        self._async_searcher: MovieSearcher | None = None
    
    def search(self, query: str, year: int | None = None) -> list[SearchResult]:
        """Synchronously search for movies."""
        import asyncio
        
        async def _search() -> list[SearchResult]:
            async with MovieSearcher(self.config) as searcher:
                return await searcher.search(query, year)
        
        return asyncio.run(_search())
    
    def get_details(self, source_id: str) -> dict[str, Any] | None:
        """Synchronously get details for a movie."""
        import asyncio
        
        async def _get_details() -> dict[str, Any] | None:
            async with MovieSearcher(self.config) as searcher:
                return await searcher.get_details(source_id)
        
        return asyncio.run(_get_details())
