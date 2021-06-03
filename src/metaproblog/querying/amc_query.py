from problog import _evaluatables
from problog.evaluator import Semiring, SemiringProbability
from problog.formula import LogicFormula

from problog.ddnnf_formula import DDNNF

class AMCQuery:

    def __init__(self, queries, evidence, formula_wrapper, target_class=DDNNF, semiring=None):
        self.queries = queries
        self.evidence = evidence
        self.formula_wrapper = formula_wrapper
        self.target_class = target_class
        self.semiring = semiring

        self.formula_version = None
        self.result = None        

    def ground(self, engine):
        self.formula_version = self.formula_wrapper.next_version()
        labels = ((self.formula_version, LogicFormula.LABEL_QUERY), (self.formula_version, LogicFormula.LABEL_EVIDENCE_NEG),(self.formula_version, LogicFormula.LABEL_EVIDENCE_POS))

        return AMCQuery.ground_query_evidence(
            engine, self.formula_wrapper.db, 
            self.queries, self.evidence,
            self.formula_wrapper.lf, labels)

    def evaluate(self, _engine):
        labels = ((self.formula_version, LogicFormula.LABEL_QUERY), (self.formula_version, LogicFormula.LABEL_EVIDENCE_NEG),(self.formula_version, LogicFormula.LABEL_EVIDENCE_POS))
        circuit = self.formula_wrapper.compile_to(self.target_class)

        self.results = AMCQuery.evaluate_circuit(circuit, labels, semiring=self.semiring)
        return self.results

    @staticmethod
    def ground_query_evidence(engine, db, queries, evidence, target_lf, labels):
        # Remember to set the formula version if you override
        q_label, epos_label, eneg_label = labels
        for eterm, ebool in evidence:
            elabel = epos_label if ebool else eneg_label
            elabel_raw = LogicFormula.LABEL_EVIDENCE_POS if ebool else LogicFormula.LABEL_EVIDENCE_NEG
            target_lf = engine.ground(db, eterm, target=target_lf, label=elabel_raw, assume_prepared=True) # For them (without formula version)
            target_lf = engine.ground(db, eterm, target=target_lf, label=elabel, assume_prepared=True)    # For me
        
        for qterm in queries:
            target_lf = engine.ground(db, qterm, target=target_lf, label=q_label, assume_prepared=True)
        
        return target_lf

    """ 
        lf: A LogicFormula or similar
        circuit_class_key: one of the keys in problog(.__init__ )._evaluatables
    """
    @staticmethod
    def compile_to_circuit(lf, circuit_class_key):
       return _evaluatables[circuit_class_key].create_from(lf)

    @staticmethod
    def evaluate_circuit(circuit, labels=None, semiring=None):
        if labels is None:
            labels = (LogicFormula.LABEL_QUERY, LogicFormula.LABEL_EVIDENCE_POS, LogicFormula.LABEL_EVIDENCE_NEG)
        
        q_label, epos_label, eneg_label = labels
        
        ev_nodes = {}
        ev_nodes.update({name:True for name,_ in circuit.get_names(epos_label)})
        ev_nodes.update({name:False for name,_ in circuit.get_names(eneg_label)})
        q_nodes = circuit.get_names( q_label )

        qresult = []
        for name,q in q_nodes:
            qresult.append( (name, circuit.evaluate(q, evidence=ev_nodes, semiring=semiring)) )
        
        return qresult, ev_nodes


# Devtime testing
def run_tests_with_static_methods():
    from problog.program import PrologString
    from problog.engine import DefaultEngine
    from problog.logic import Term, Var
    p = PrologString("""
    coin(c1). coin(c2).
    0.4::heads(C); 0.6::tails(C) :- coin(C).
    win :- heads(C).
    """)

    qs, evs = ([Term("win")], [(Term("heads", Term("c1")), False)]) # For now

    engine = DefaultEngine()
    db = engine.prepare(p)
    labels = (LogicFormula.LABEL_QUERY, LogicFormula.LABEL_EVIDENCE_POS, LogicFormula.LABEL_EVIDENCE_NEG)
    lf = LogicFormula()
    lf = AMCQuery.ground_query_evidence(engine, db, qs, evs, lf, labels)
    
    circuit = AMCQuery.compile_to_circuit(lf, "ddnnf")
    prob_sr = SemiringProbability()
    results, ground_evidence = AMCQuery.evaluate_circuit(circuit, labels, prob_sr)
    print("evidence: ", ground_evidence)
    for r in results:
        print(r)
    print("---")

def run_test_with_query_instance():

    from problog.program import PrologString
    from problog.engine import DefaultEngine
    from problog.logic import Term, Var
    p = PrologString("""
    coin(c1). coin(c2).
    0.4::heads(C); 0.6::tails(C) :- coin(C).
    win :- heads(C).
    """)
    from .formula_wrapper import FormulaWrapper
            
    s_qs, s_evs = ([Term("win")], [(Term("heads", Term("c1")), False)]) # For now
    
    engine = DefaultEngine()
    probsr = SemiringProbability()
    fw = FormulaWrapper(engine.prepare(p))
    qobj = AMCQuery(s_qs, s_evs, fw, target_class=DDNNF, semiring=probsr)
    
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
