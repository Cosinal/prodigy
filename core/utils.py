"""Utility functions for Prodigy agents."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_json(filepath: str | Path) -> Dict[str, Any]:
    """
    Load JSON file with error handling.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Parsed JSON dict, or empty dict if file not found
    """
    try:
        path = Path(filepath)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        print(f"[Warning] Failed to parse JSON from {filepath}: {e}")
        return {}


def save_json(data: Dict[str, Any], filepath: str | Path, indent: int = 2) -> None:
    """
    Save data to JSON file with pretty printing.
    
    Args:
        data: Data to save
        filepath: Path to save JSON file
        indent: Indentation level for pretty printing
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def weighted_average(scores: List[float], weights: Optional[List[float]] = None) -> float:
    """
    Compute weighted average of scores.
    
    Args:
        scores: List of scores
        weights: Optional list of weights (defaults to equal weights)
        
    Returns:
        Weighted average score
    """
    if not scores:
        return 0.0
    
    if weights is None:
        weights = [1.0] * len(scores)
    
    if len(weights) != len(scores):
        weights = [1.0] * len(scores)
    
    weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
    total_weight = sum(weights)
    
    return weighted_sum / total_weight if total_weight > 0 else 0.0


def generate_timestamp() -> str:
    """
    Generate ISO timestamp for filenames.
    
    Returns:
        ISO format timestamp string (e.g., "2024-01-15T14-30-45")
    """
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def save_report(result: Dict[str, Any], reports_dir: str = "reports") -> Path:
    """
    Save counsel report to JSON file with timestamp.
    
    Args:
        result: Report data to save
        reports_dir: Directory to save reports in
        
    Returns:
        Path to saved file
    """
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = generate_timestamp()
    idea_name = result.get("project", {}).get("idea_name", "unknown")
    # Sanitize idea name for filename
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in idea_name)
    
    filename = f"{safe_name}_{timestamp}.json"
    filepath = reports_path / filename
    
    save_json(result, filepath)
    
    return filepath
