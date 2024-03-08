from src.models.mcda.vector_preprocessing.base import VectorPreprocessorBase
import structlog

logger = structlog.get_logger(__name__)


class Waterdeel(VectorPreprocessorBase):
    criteria = "waterdeel"

    def specific_preprocess(self) -> None:
        self._set_suitability_values()

    @staticmethod
    def _set_suitability_values():
        logger.info("Setting suitability values.")
        pass
