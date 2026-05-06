"""hw_test_framework/reporting/__init__.py"""

from .html_reporter import write_html
from .junit_reporter import write_junit

__all__ = ["write_junit", "write_html"]
