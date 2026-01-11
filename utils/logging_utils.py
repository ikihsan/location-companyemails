"""
Logging utilities for the company scraper.
Provides rotating file logs and rich console output.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from loguru import logger as loguru_logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False


class ScraperLogger:
    """Custom logger with file rotation and optional rich console output."""
    
    def __init__(
        self, 
        name: str = "company_scraper",
        log_dir: Path = Path("logs"),
        log_level: int = logging.INFO,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        verbose: bool = False,
    ):
        self.name = name
        self.log_dir = log_dir
        self.log_level = logging.DEBUG if verbose else log_level
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.verbose = verbose
        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = self._setup_logger()
        
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None
    
    def _setup_logger(self) -> logging.Logger:
        """Configure the logger with handlers."""
        logger = logging.getLogger(self.name)
        logger.setLevel(self.log_level)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # File handler with rotation
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = self.log_dir / f"{self.name}_{timestamp}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Always log debug to file
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        if RICH_AVAILABLE:
            console_handler = RichHandler(
                rich_tracebacks=True,
                markup=True,
                show_time=True,
                show_path=False,
            )
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
        
        console_handler.setLevel(self.log_level)
        logger.addHandler(console_handler)
        
        return logger
    
    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)


def create_progress_bar(description: str = "Processing") -> Optional['Progress']:
    """Create a rich progress bar if available."""
    if not RICH_AVAILABLE:
        return None
    
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
    )


class ProgressTracker:
    """Track progress with or without rich library."""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.progress = None
        self.task_id = None
        
        if RICH_AVAILABLE:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeElapsedColumn(),
            )
    
    def __enter__(self):
        if self.progress:
            self.progress.start()
            self.task_id = self.progress.add_task(self.description, total=self.total)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.progress:
            self.progress.stop()
    
    def update(self, advance: int = 1, description: Optional[str] = None):
        """Update progress."""
        self.current += advance
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, advance=advance)
            if description:
                self.progress.update(self.task_id, description=description)
        else:
            # Fallback to simple print
            pct = (self.current / self.total) * 100 if self.total > 0 else 0
            print(f"\r{self.description}: {self.current}/{self.total} ({pct:.1f}%)", end='', flush=True)
    
    def set_description(self, description: str):
        """Update the description."""
        self.description = description
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, description=description)


# Global logger instance
_logger: Optional[ScraperLogger] = None


def get_logger(
    verbose: bool = False,
    log_dir: Path = Path("logs"),
) -> ScraperLogger:
    """Get or create global logger instance."""
    global _logger
    if _logger is None:
        _logger = ScraperLogger(verbose=verbose, log_dir=log_dir)
    return _logger


def setup_logger(
    verbose: bool = False,
    log_dir: Path = Path("logs"),
) -> ScraperLogger:
    """Setup and return a new logger instance."""
    global _logger
    _logger = ScraperLogger(verbose=verbose, log_dir=log_dir)
    return _logger
