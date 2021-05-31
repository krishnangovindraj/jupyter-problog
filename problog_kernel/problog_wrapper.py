from problog import get_evaluatable
from problog.engine import DefaultEngine
from problog.formula import LogicFormula
from problog.program import PrologString

from problog.logic import And, Not, Term, AnnotatedDisjunction, Clause

from .query_session import QuerySession


from metaproblog.theory_manager import TheoryManager

class ProblogWrapper:
    
    def __init__(self):
        self.engine = DefaultEngine()
        self.db = self.engine.prepare([])
        self.theory_manager = TheoryManager.initialize(self.db)
        self.cell_heads = {} # cell_id -> set(Tuple[head, node_index])
        self.cell_range = {}

    # public
    def process_cell(self, cell_id_user, code: "problog.program.PrologString"):
        cell_id = self._cell_theory_id(cell_id_user) # Rename it a little

        if cell_id is not None and self.theory_manager.theory_exists(cell_id):
            self.theory_manager.remove_theory(cell_id)

        statement_list = []
        queries = []
        evidence = []
        questions = []
        for stmt in code:
            if stmt.signature == "?/1" or stmt.signature == "?/2":
                questions.append(stmt)
            elif stmt.signature == "query/1":
                queries.append(stmt.args[0])
            elif stmt.signature == "evidence/1":
                ev = (stmt.args[0].args[0], False)  if isinstance(stmt.args[0], Not) else (stmt.args[0], True)
                evidence.append( ev ) # TODO: handle negations
            else:
                statement_list.append(stmt)

        self.theory_manager.add_theory(cell_id, statement_list)
        self.db = self.engine.prepare(self.db) # Does a process_directives

        return queries, evidence, questions

    def _cell_theory_id(self, cell_id):
        return None if cell_id is None else "_pbl_cell_%s"%cell_id 

    """ Run a single query - ground, compile and evaluate. For multiple queries, Use a QuerySession """
    def query(self, queries: "List[problog.logic.Term]", evidence: "List[problog.logic.Term]"):
        lf = self.engine.ground_all(self.db, queries=queries, evidence=evidence)
        return get_evaluatable().create_from(lf).evaluate()

    def create_query_session(self):
        return QuerySession(self.engine, self.db)


def _run_tests():
    def _format_evidence(et):
        return "%s%s"%("" if et[1] else "~", et[0])

    def _print_result(queries, evidence, query_probs):
        print("----")
        if e:
            print("% Evidence: ", ", ".join(_format_evidence(ev) for ev in e))
            print(" . . . ")
        print("\n".join(["%s: %f"%(str(k), query_probs[k]) for k in query_probs]))
        print("----")

    pbl = ProblogWrapper()
    p1 = (1, """
    0.2::foo(2); 0.3::foo(3); 0.5::foo(5):- bar(Z).
    """)

    p2 = (None, """
    bar(a).
    0.7::bar(b).

    evidence(\+bar(b)).
    query(foo(X)).
    """)

    for cid, p in [p1, p2]:
        q, e = pbl.process_cell(cid, PrologString(p))
        res = pbl.query(q,e)
        if q:
            _print_result(q, e, res)

    p1 = (1, """ 0.1::foo(a); 0.25::foo(b); 0.65::foo(c):- bar(Z).""")

    for (cid, p) in [p1, p2]:
        q ,e = pbl.process_cell(cid, PrologString(p))
        res = pbl.query(q,e)
        if q:
            _print_result(q, e, res)

if __name__ == "__main__":
    _run_tests()
