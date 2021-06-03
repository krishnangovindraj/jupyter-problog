from metaproblog.querying.query_factory import QueryFactory
from problog.logic import Term
class OptionKeys:
    QUERY_TYPE = Term("query_type")

default_options = {
    OptionKeys.QUERY_TYPE: QueryFactory.QueryType.PROBABILITY,
}