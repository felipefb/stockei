"""
Knowledge Base
Topic-indexed knowledge store with optional JSON file persistence.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """In-memory knowledge store organized by topic."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        """
        Initialize the knowledge base.

        Args:
            storage_path: Optional JSON file path used by
                ``export_to_file``/``import_from_file`` defaults.
        """
        self.storage_path = storage_path
        self.data: Dict[str, List[Dict[str, Any]]] = {}

    def store(self, topic: str, entry: Any) -> Dict[str, Any]:
        """
        Store an entry under a topic.

        Args:
            topic: Topic key.
            entry: Content to store.

        Returns:
            The stored record (timestamp + entry).
        """
        record: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "entry": entry,
        }
        self.data.setdefault(topic, []).append(record)
        logger.info("KnowledgeBase: stored entry under '%s'", topic)
        return record

    def retrieve(self, topic: str) -> List[Dict[str, Any]]:
        """
        Retrieve all entries for a topic.

        Args:
            topic: Topic key.

        Returns:
            List of records (empty if unknown topic).
        """
        return list(self.data.get(topic, []))

    def search(self, term: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search topics and entries containing a term (case-insensitive).

        Args:
            term: Search term.

        Returns:
            Mapping topic -> matching records.
        """
        term_lower = term.lower()
        results: Dict[str, List[Dict[str, Any]]] = {}
        for topic, records in self.data.items():
            matches = [r for r in records
                       if term_lower in topic.lower()
                       or term_lower in str(r["entry"]).lower()]
            if matches:
                results[topic] = matches
        return results

    def export_to_file(self, path: Optional[str] = None) -> str:
        """
        Export the knowledge base to a JSON file.

        Args:
            path: Target file; defaults to ``storage_path``.

        Returns:
            The path written.

        Raises:
            ValueError: If no path is available.
        """
        target = path or self.storage_path
        if not target:
            raise ValueError("No path provided for knowledge base export")
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)
        logger.info("KnowledgeBase: exported to '%s'", target)
        return target

    def import_from_file(self, path: Optional[str] = None) -> None:
        """
        Import (merge) knowledge from a JSON file.

        Args:
            path: Source file; defaults to ``storage_path``.

        Raises:
            ValueError: If no path is available.
        """
        source = path or self.storage_path
        if not source:
            raise ValueError("No path provided for knowledge base import")
        with open(source, "r", encoding="utf-8") as fh:
            loaded: Dict[str, List[Dict[str, Any]]] = json.load(fh)
        for topic, records in loaded.items():
            self.data.setdefault(topic, []).extend(records)
        logger.info("KnowledgeBase: imported from '%s'", source)
