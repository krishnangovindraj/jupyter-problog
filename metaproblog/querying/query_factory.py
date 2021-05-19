from enum import Enum

from problog.evaluator import SemiringProbability
from problog.tasks.mpe import SemiringMPEState, SemiringMinPEState

from .sample_query import SampleQuery
from .amc_query import AMCQuery

class QueryFactory:
    class QueryType(Enum):
        PROBABILITY = 1
        MPE = 2
        MINPE = 3
        SAMPLE = 4
        # More coming?
    
    @staticmethod
    def create_query(query_type, queries, evidence, formula_wrapper, **kwargs):
        if query_type == QueryFactory.QueryType.PROBABILITY:
            return AMCQuery(queries, evidence, formula_wrapper, semiring=SemiringProbability(), **kwargs)
        elif query_type == QueryFactory.QueryType.MPE:
            return AMCQuery(queries, evidence, formula_wrapper, semiring = SemiringMPEState(), **kwargs)
        elif query_type == QueryFactory.QueryType.MINPE:
            return AMCQuery(queries, evidence, formula_wrapper, semiring = SemiringMinPEState(), **kwargs)
        elif query_type == QueryFactory.QueryType.SAMPLE:
            return SampleQuery(queries, evidence, formula_wrapper, **kwargs)
        else:
            raise NotImplementedError("query_type not yet supported: %s"%str(query_type))
    

