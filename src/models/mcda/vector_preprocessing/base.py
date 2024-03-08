import abc
import datetime
import structlog

logger = structlog.get_logger(__name__)


class VectorPreprocessorBase(abc.ABC):
    @property
    @abc.abstractmethod
    def criteria(self) -> str:
        """Name of the criteria"""

    def execute(self) -> str:
        start = datetime.datetime.now()
        logger.info(f"Start preprocessing: {self.criteria}.")
        self.setup()
        self.specific_preprocess()
        self.validate_result()
        self.write_to_file()
        end = datetime.datetime.now()
        logger.info(f"Finished {self.criteria} in: {end - start} time.")
        return self.criteria

    @abc.abstractmethod
    def specific_preprocess(self) -> None:
        """Subclasses must implement this abstract method which contains logic for handling the criteria."""

    def setup(self):
        """Prepare geopackage?"""
        # TODO
        pass

    def validate_result(self):
        """Validate the result if all values are set and within expected tolerances."""
        # TODO
        pass

    def write_to_file(self):
        """Write to the geopackage."""
        # TODO
        pass
