"""Home dashboard state."""

import logging

import reflex as rx

from utils.db_utils import get_db_stats, test_connection
from utils.providers import get_model_info

logger = logging.getLogger(__name__)


class HomeState(rx.State):
    """Dashboard statistics and status."""

    doc_count: int = 0
    chunk_count: int = 0
    db_connected: bool = False
    llm_model: str = ""
    embedding_model: str = ""
    loading: bool = True

    async def load_stats(self):
        """Load dashboard stats on page load."""
        self.loading = True
        try:
            connected = await test_connection()
            self.db_connected = connected

            if connected:
                stats = await get_db_stats()
                self.doc_count = stats["documents"]
                self.chunk_count = stats["chunks"]

            info = get_model_info()
            self.llm_model = info["llm_model"]
            self.embedding_model = info["embedding_model"]
        except Exception as e:
            logger.error(f"Failed to load stats: {e}")
            self.db_connected = False
        finally:
            self.loading = False
