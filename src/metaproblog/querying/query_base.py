from problog.formula import LogicFormula

from problog.ddnnf_formula import DDNNF

class QueryBase:

    def __init__(self, queries, evidence, formula_wrapper):
        self.queries = queries
        self.evidence = evidence
        self.formula_wrapper = formula_wrapper

    def ground(self, engine):
        raise NotImplementedError("QueryBase.ground is abstract")

    def evaluate(self, engine):
        raise NotImplementedError("QueryBase.evaluate is abstract")
