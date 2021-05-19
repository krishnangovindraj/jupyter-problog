from sys import stderr as sys_stderr

from problog.engine import DefaultEngine
from problog.formula import LogicFormula
from problog.tasks.sample import FunctionStore, SampledFormula, verify_evidence as verify_evidence_propagated


from metaproblog.querying.query_base import QueryBase


class SampleQuery(QueryBase):
    def __init__(self, queries, evidence, formula_wrapper, n_samples=1, propagate_evidence=False):
        super().__init__(queries, evidence, formula_wrapper)
        self.n_samples = n_samples
        self.propagate_evidence = propagate_evidence

        self.propagated_ev_facts = []
        self.propagated_ev_target = None

    def ground(self, engine):
        if self.propagate_evidence:
            self.propagated_ev_facts, self.propagated_ev_target = \
                SampleQuery.do_propagate_evidence(engine, self.formula_wrapper.db,  self.evidence)
    

    def evaluate(self, engine):
        sample_result = list(SampleQuery.sample(
            DefaultEngine(), self.formula_wrapper.db,
            self.queries, self.evidence, self.n_samples,
            (self.propagated_ev_facts, self.propagated_ev_target)))
        
        sampled_terms = [r[0] for r in sample_result]
        ev_result = {}

        if self.propagate_evidence:
            ev_read_formula = self.propagated_ev_target
        elif len(sample_result) > 0:
            ev_read_formula = sample_result[0][1]
        else:
            ev_read_formula = None

        if ev_read_formula is not None:
            ev_result.update({name:True for name,_ in ev_read_formula.get_names(LogicFormula.LABEL_EVIDENCE_POS)})
            ev_result.update({name:False for name,_ in ev_read_formula.get_names(LogicFormula.LABEL_EVIDENCE_NEG)})
        
        self.results = (sampled_terms, ev_result)

        return self.results
    
    @staticmethod
    def do_propagate_evidence(engine, db, evidence, ev_target=None):
        if ev_target is None:
            ev_target = LogicFormula()
        
        engine.ground_evidence(db, ev_target, evidence)
        ev_target.lookup_evidence = {}
        ev_nodes = [
            node
            for name, node in ev_target.evidence()
            if node != 0 and node is not None
        ]
        ev_target.propagate(ev_nodes, ev_target.lookup_evidence)

        ev_facts = []
        for index, value in ev_target.lookup_evidence.items():
            node = ev_target.get_node(index)
            if ev_target.is_true(value):
                ev_facts.append((node[0], 1.0) + node[2:])
            elif ev_target.is_false(value):
                ev_facts.append((node[0], 0.0) + node[2:])

        return ev_facts, ev_target

    @staticmethod
    def verify_evidence_wrapper(engine, db, ev_target, q_target, raw_evidence):
        if ev_target is None:
            engine.ground_evidence(db, q_target, raw_evidence)
            for _name, node in q_target.evidence():
                if q_target.is_false(node):
                    return False
            return True
        else:
            return verify_evidence_propagated(engine, db, ev_target, q_target)
    
    @staticmethod
    def sample(engine, db, queries, evidence, n_samples, propagated_facts_target=([], None)):
        ev_facts, ev_target = propagated_facts_target
        i = 0
        r = 0
        labelled_queries = [(SampledFormula.LABEL_QUERY, q) for q in queries]
        try:
            while i < n_samples or n_samples==0:
                target = SampledFormula()
                # if distributions is not None:
                #     target.distributions.update(distributions)

                for ev_fact in ev_facts:
                    target.add_atom(*ev_fact)

                engine.functions = FunctionStore(target=target, database=db, engine=engine)
                
                engine.ground_queries(db, target, labelled_queries)
                result = target
                if SampleQuery.verify_evidence_wrapper(engine, db, ev_target, target, evidence):
                    yield result.to_dict(), target
                    i += 1
                else:
                    r += 1
                engine.previous_result = result
        except KeyboardInterrupt:
            pass
        
        print("Rejected samples: %s" % r, file=sys_stderr)
        return None

# Devtime testing
def run_tests_with_static_methods():
    for PROPAGATE in [True, False]:
        print("PROPAGATE=", PROPAGATE)
        from problog.program import PrologString
        from problog.engine import DefaultEngine
        from problog.logic import Term, Var
        p = PrologString("""
        coin(c1). coin(c2).
        0.4::heads(C); 0.6::tails(C) :- coin(C).
        """)

        s_qs, s_evs = ([ Term("heads", Var("X")) ], [(Term("heads", Term("c1")), True)]) # For now

        engine = DefaultEngine()
        db = engine.prepare(p)

        if PROPAGATE:
            pp = SampleQuery.do_propagate_evidence(engine, db, s_evs)
        else:
            pp = ([], None)
        result = list(SampleQuery.sample(engine, db, s_qs, s_evs, n_samples=5, propagated_facts_target=pp))
        for r, _target in result:
            print(r)
        print("---")

def run_test_with_query_instance():

    for PROPAGATE in [True, False]:
        print("PROPAGATE=", PROPAGATE)
        from problog.program import PrologString
        from problog.engine import DefaultEngine
        from problog.logic import Term, Var
        p = PrologString("""
        coin(c1). coin(c2).
        0.4::heads(C); 0.6::tails(C) :- coin(C).
        """)
        from .formula_wrapper import FormulaWrapper
                
        s_qs, s_evs = ([ Term("heads", Var("X"))], [(Term("heads", Term("c1")), True)]) # For now
        
        engine = DefaultEngine()
        fw = FormulaWrapper(engine.prepare(p))
        qobj = SampleQuery(s_qs, s_evs, fw, 5, PROPAGATE)

        qobj.ground(engine)
        result, ground_evidence = qobj.evaluate(engine)
        print("evidence: ", ground_evidence)
        for r in result:
            print(r)
        print("---")

if __name__ == "__main__":
    print("Static methods:")
    run_tests_with_static_methods()
    print("\nWith query instance:")
    run_test_with_query_instance()