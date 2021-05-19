"""
Allows us to take advantage of the compile-once, query-many approach.
Assumes the user will make the decision on which queries should be grouped in a session.
"""
from sys import stderr as sys_stderr

from problog.formula import LogicFormula, LogicDAG
from problog.logic import And, Not, Term, Clause
from problog.ddnnf_formula import DDNNF
from problog.cnf_formula import CNF

from metaproblog.querying.formula_wrapper import FormulaWrapper
from metaproblog.querying.query_factory import QueryFactory

class QuerySession:

    TIQ_HEAD_PREFIX = "_tiq"

    def __init__(self, engine, base_db):
        self.engine = engine
        self.db = self.engine.prepare(base_db.extend())
        self.tiq_count = 0 # transformed_inline_query

        self._compiled = False
        self.lf_wrapper = FormulaWrapper(self.db)
        self.queries = []

    def _compile(self):
        self._compiled = True

    """ Add a set of queries which share the same evidence """
    def prepare_query(self, queries, evidence, query_type):
        if self._compiled:
            raise ProblogKernelException("QuerySession was compiled. You cannot prepare_query anymore.")

        qobj = QueryFactory.create_query(query_type, queries, evidence, self.lf_wrapper)

        if qobj:
            self.queries.append(qobj)
            qobj.ground(self.engine)
            return True
        else:
            return False

    """ Evaluates all queries added with queries """
    def evaluate_queries(self):
        if not self._compiled:
            self._compile()

        results = []
        for q in self.queries:
            results.append( q.evaluate(self.engine) )

        return results

    """ Adds a query-node to the program and returns it's signature """
    def transform_inline_query(self, inline_query):
        def _conj2list(conj):
            def _conj2list_rec(conj, acc):
                if isinstance(conj, And):
                    acc.append(conj.args[0])
                    return _conj2list_rec(conj.args[1], acc)
                else:
                    acc.append(conj)
                    return acc

            return _conj2list_rec(conj, [])

        def _rawev_to_tuple(ev):
            if isinstance(ev, Not):
                return (ev.args[0], False)
            else:
                return (ev, True)

        # With evidence?
        if inline_query.functor == "'|'":
            qc = inline_query.args[0]
            evidence = [_rawev_to_tuple(ev) for ev in _conj2list(inline_query.args[1])]
        else:
            qc = inline_query
            evidence = []

        varnames = qc.variables(exclude_local=True)
        tiq_head_functor = "%s_%d"%(QuerySession.TIQ_HEAD_PREFIX, self.tiq_count)
        tiq_head = Term(tiq_head_functor, *varnames)
        self.db.add_statement(Clause(tiq_head, qc))

        return [tiq_head], evidence


def _run_tests():
    from problog.program import PrologString
    from problog.engine import DefaultEngine
    p = PrologString("""
    coin(c1). coin(c2).
    0.4::heads(C); 0.6::tails(C) :- coin(C).
    win :- heads(C).
    """)

    engine = DefaultEngine()
    db = engine.prepare(p)

    # tasks = [
    #     ([Term("win")], []),
    #     ([Term("win")], [(Term("heads", Term("c1")), True)]),
    #     ([Term("win")], [(Term("heads", Term("c1")), False)]),
    # ]
    # for q,e in tasks:
    #     qs.prepare_query(q, e)
    # print(qs.evaluate_queries())

    qs = QuerySession(engine, db)
    inline_queries = [" win | heads(c1).", "win | \+heads(c1).", "win."]
    for iq in inline_queries:
        q,e = qs.transform_inline_query(PrologString(iq)[0])
        qs.prepare_query(q,e)

    result = qs.evaluate_queries()
    print(result)

if __name__ == "__main__":
    _run_tests()