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
        data = json.loads(content)
    except json.JSONDecodeError:
        data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON/YAML object, got {type(data).__name__}.")
    return data
