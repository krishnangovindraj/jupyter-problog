"""
Allows us to take advantage of the compile-once, query-many approach.
Assumes the user will make the decision on which queries should be grouped in a session.
"""
from sys import stderr as sys_stderr

from problog.formula import LogicFormula, LogicDAG
from problog.logic import And, Not, Term, Clause
from problog.ddnnf_formula import DDNNF
from problog.cnf_formula import CNF

class QuerySession:

    TIQ_HEAD_PREFIX = "_tiq"

    def __init__(self, engine, base_db):
        self.engine = engine
        self.db = self.engine.prepare(base_db.extend())
        self.tiq_count = 0 # transformed_inline_query

        self._compiled = False
        self.query_count = 0

        self.lf = LogicFormula()
        self.ddnnf = None
    def _compile(self):
        dag = LogicDAG.create_from(self.lf)     # break cycles in the ground program
        cnf = CNF.create_from(dag)         # convert to CNF
        self.ddnnf = DDNNF.create_from(cnf)       # compile CNF to ddnnf
        self._compiled = True
        return self.ddnnf

    """ Add a set of queries which share the same evidence """
    def prepare_query(self, queries, evidence):
        if self._compiled:
            raise ProblogKernelException("QuerySession was compiled. You cannot prepare_query anymore.")

        i = self.query_count
        for eterm, ebool in evidence:
            elabel = LogicFormula.LABEL_EVIDENCE_POS if ebool else LogicFormula.LABEL_EVIDENCE_NEG
            self.lf = self.engine.ground(self.db, eterm, target=self.lf, label=elabel, assume_prepared=True)      # For them
            self.lf = self.engine.ground(self.db, eterm, target=self.lf, label=(i, elabel), assume_prepared=True) # For me
        for qterm in queries:
            self.lf = self.engine.ground(self.db, qterm, target=self.lf, label=(i,LogicFormula.LABEL_QUERY), assume_prepared=True)

        self.query_count += 1

    """ Evaluates all queries added with queries """
    def evaluate_queries(self):
        if not self._compiled:
            self._compile()

        results = []
        for i in range(self.query_count):
            evidence = {}
            evidence.update({name:True for name,_ in self.ddnnf.get_names((i, LogicFormula.LABEL_EVIDENCE_POS))})
            evidence.update({name:False for name,_ in self.ddnnf.get_names((i, LogicFormula.LABEL_EVIDENCE_NEG))})
            q_nodes = self.ddnnf.get_names( (i, LogicFormula.LABEL_QUERY) )

            qresult = []
            for name,q in q_nodes:
                qresult.append( (name, self.ddnnf.evaluate(q, evidence=evidence)) )
            results.append( (qresult, evidence) )

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