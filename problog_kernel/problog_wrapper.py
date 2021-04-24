from problog import get_evaluatable
from problog.engine import DefaultEngine
from problog.formula import LogicFormula
from problog.program import PrologString

from problog.logic import And, Not, Term, AnnotatedDisjunction, Clause

class ProblogWrapper:

    def __init__(self):
        self.engine = DefaultEngine()
        self.db = self.engine.prepare([])

        self.cell_heads = {} # cell_id -> set(Tuple[head, node_index])
        self.cell_range = {}

    # public 

    def process_cell(self, cell_id, code: "problog.program.PrologString"):
        # TODO: consider not removing and re-adding unmodified clauses? (Beware: clause-ordering)
        if cell_id is not None and cell_id in self.cell_heads:
            self._forget_cell(cell_id)

        self.cell_heads[cell_id] = []
        self.cell_range[cell_id] = (-1, -1)
        range_start = len(self.db)

        queries = []
        evidence = []

        for stmt in code:
            if stmt.signature == "query/1":
                queries.append(stmt.args[0])
            elif stmt.signature == "evidence/1":
                ev = (stmt.args[0].args[0], False)  if isinstance(stmt.args[0], Not) else (stmt.args[0], True)
                evidence.append( ev ) # TODO: handle negations
            else:
                self.db.add_statement(stmt)
                # Go in reverse to find a 
                if isinstance(stmt, AnnotatedDisjunction):
                    heads = stmt.heads
                elif isinstance(stmt, Clause):
                    heads = [stmt.head]
                else:
                    heads = [stmt]

                for h in heads:
                    self.cell_heads[cell_id].append( h )

        self.cell_range[cell_id] = (range_start, len(self.db))

        self.db = self.engine.prepare(self.db) # Does a process_directives

        return queries, evidence

    def query(self, queries: "List[problog.logic.Term]", evidence: "List[problog.logic.Term]"):
        lf = self.engine.ground_all(self.db, queries=queries, evidence=evidence)
        return get_evaluatable().create_from(lf).evaluate()

    def inline_query(self, c):
        def _conj2list(conj):
            def _conj2list_rec(conj, acc):
                if isinstance(conj, And):
                    acc.append(conj.args[0])
                    return _conj2list_rec(conj.args[1], acc)
                else:
                    acc.append(conj)
                    return acc

            return _conj2list_rec(conj, [])

        # Can be And, Or, query/1, inline [conditional] query 
        result_str = io.StringIO()
        try:
            if c.signature == "listing/0":
                self._listing(result_str)
            elif c.signature in ["consult/1", "use_module/1"]:
                self._consult(c)
                # show('%% Consulted file %s' % c.args[0])
            elif c.signature == "query/1":
                self._query1(c, result_str)
            else:
                if c.functor == "'|'":
                    queries = [c.args[0]]
                    evidence = _conj2list(c.args[1]) # I hope it was a conj
                else:
                    queries = [c]
                    evidence = []

        except ProbLogError as err:
            print(str(err), file=result_str)
        except Exception as err:
            print(str(err), file=result_str)
            from traceback import print_exc
            print_exc(file=result_str)

        result = result_str.getvalue()
        result_str.close()
        return result

    # private
    def _forget_cell(self, cell_id):
        range_start, range_end = self.cell_range[cell_id]

        for head in self.cell_heads[cell_id]:
            define_node = self.db.get_node(self.db.find(head))
            all_matching_children = define_node.children.find(head)

            to_erase = set(c for c in all_matching_children if  range_start < c  and c < range_end)
            define_node.children.erase( to_erase )

        self.cell_heads[cell_id] = []
        self.cell_range[cell_id] = (-1,-1)


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
