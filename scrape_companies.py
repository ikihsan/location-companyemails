#!/usr/bin/env python3
"""
==============================================================================
COMPANY CONTACT SCRAPER - Production-Grade Job Board Scraping Pipeline
==============================================================================

A modular, extensible scraping pipeline for discovering companies hiring for
software development roles and extracting their contact information.

SETUP:
------
1. Python 3.11+ required
2. Install dependencies:
   pip install -r requirements.txt

3. (Optional) For JavaScript-heavy sites:
   pip install playwright
   playwright install chromium

4. Copy .env.example to .env and configure as needed

USAGE:
------
# Basic usage - search Berlin for software developers
python scrape_companies.py --location "Berlin, Germany"

# Multiple locations with max limit
python scrape_companies.py --location "Berlin, Germany" --location "Munich, Germany" --max-companies 500

# With headless browser for JS sites
python scrape_companies.py --location "Berlin, Germany" --use-headless --verbose

# Custom roles
python scrape_companies.py --location "Berlin, Germany" --role "python developer" --role "data engineer"

OUTPUTS:
--------
- data/company_contacts/companies_<location>_<timestamp>.csv
- data/company_contacts/companies_<location>_<timestamp>.json
- data/company_contacts/manifest.json
- logs/company_scraper_<date>.log

ARCHITECTURE:
-------------
- discovery/     : Pluggable sources (Google, job boards, startup directories)
- fetcher/       : HTTP requests with retries, rate limiting, headless browser
- parsers/       : HTML parsing and structured data extraction
- extractors/    : Email extraction with regex and heuristics
- storage/       : CSV/JSON persistence with deduplication
- utils/         : Logging and progress tracking

==============================================================================
"""

import sys
import click
from typing import List, Optional

from pipeline import run_pipeline
from config import get_config


@click.command()
@click.option(
    '--location', '-l',
    multiple=True,
    required=True,
    help='Location to search (can specify multiple). Example: --location "Berlin, Germany"'
)
@click.option(
    '--role', '-r',
    multiple=True,
    help='Target role to search (can specify multiple). Defaults to common software dev roles.'
)
@click.option(
    '--max-companies', '-m',
    default=500,
    type=int,
    help='Maximum number of companies to discover. Default: 500 (for high volume scraping)'
)
@click.option(
    '--use-headless/--no-headless', '-h',
    default=True,
    help='Use headless browser for JavaScript-heavy sites (DEFAULT: ON, requires playwright)'
)
@click.option(
    '--verbose/--quiet', '-v',
    default=True,
    help='Enable verbose logging (DEFAULT: ON)'
)
@click.option(
    '--concurrency', '-c',
    default=10,
    type=int,
    help='Maximum concurrent requests. Default: 10 (optimized for speed)'
)
@click.option(
    '--output-dir', '-o',
    default=None,
    type=str,
    help='Output directory for results. Default: data/company_contacts'
)
def main(
    location: tuple,
    role: tuple,
    max_companies: int,
    use_headless: bool,
    verbose: bool,
    concurrency: int,
    output_dir: Optional[str],
):
    """
    Company Contact Scraper - Discover companies hiring developers and extract contact info.
    
    \b
    Examples:
      python scrape_companies.py --location "Berlin, Germany" --max-companies 300
      python scrape_companies.py -l "London, UK" -l "Paris, France" -v
      python scrape_companies.py -l "Berlin, Germany" --use-headless --role "python developer"
    """
    
    # Convert tuples to lists
    locations = list(location)
    roles = list(role) if role else None
    
    # Update config if output dir specified
    if output_dir:
        from pathlib import Path
        config = get_config()
        config.storage.output_dir = Path(output_dir)
        config.storage.ensure_dirs()
    
    # Update concurrency
    if concurrency != 5:
        config = get_config()
        config.rate_limit.max_concurrent_requests = concurrency
    
    click.echo("=" * 60)
    click.echo("� COMPANY CONTACT SCRAPER - ULTIMATE MODE")
    click.echo("=" * 60)
    click.echo(f"Locations: {', '.join(locations)}")
    click.echo(f"Max companies: {max_companies}")
    click.echo(f"Headless browser: {use_headless}")
    click.echo(f"Verbose: {verbose}")
    click.echo(f"Sources: ULTIMATE SOURCE (120+ known companies + 5 job portals)")
    click.echo("=" * 60)
    click.echo()
    
    try:
        results = run_pipeline(
            locations=locations,
            roles=roles,
            max_companies=max_companies,
            use_headless=use_headless,
            verbose=verbose,
        )
        
        click.echo()
        click.echo("=" * 60)
        click.echo("RESULTS SUMMARY")
        click.echo("=" * 60)
        click.echo(f"Companies discovered: {results.get('companies_discovered', 0)}")
        click.echo(f"Companies with emails: {results.get('companies_with_emails', 0)}")
        click.echo(f"Total emails found: {results.get('total_emails', 0)}")
        click.echo(f"Time elapsed: {results.get('elapsed_seconds', 0):.1f}s")
        click.echo()
        click.echo("Output files:")
        for format_type, path in results.get('output_files', {}).items():
            click.echo(f"  {format_type.upper()}: {path}")
        click.echo("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user. Partial results may have been saved.")
        return 1
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
