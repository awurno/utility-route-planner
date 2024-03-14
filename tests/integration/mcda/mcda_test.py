from src.models.mcda.mcda_engine import McdaCostSurfaceEngine


class TestVectorPreprocessing:
    def test_process_vector_criteria(self):
        mcda_engine = McdaCostSurfaceEngine("preset_benchmark_raw")
        mcda_engine.preprocess_vectors()


class TestRasterPreprocessing:
    # TODO
    pass
