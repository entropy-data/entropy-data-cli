"""Shared utilities."""

import json
import sys
from pathlib import Path

import yaml


def read_body(file: Path) -> dict:
    """Read JSON or YAML from file path or stdin (-)."""
    if str(file) == "-":
        content = sys.stdin.read()
    else:
        content = file.read_text()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return yaml.safe_load(content)
