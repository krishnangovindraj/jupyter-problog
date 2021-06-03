import sys
from problog.clausedb import ClauseDB
from problog.logic import Term

from sys import stderr as sys_stderr

class TheoryManager:
    _static_instance = None

    @staticmethod
    def initialize(db):
        TheoryManager._static_instance = TheoryManager(db)
        return TheoryManager._static_instance

    def __init__(self, db):
        self._db = db
        self._range = {} # TheoryKey -> (StartNode, EndNode)

    def theory_exists(self, theory_key):
        assert( theory_key is not None )
        return theory_key in self._range

    def add_theory(self, theory_key, statement_list):
        assert( theory_key is not None )
        if theory_key not in self._range:
            start = len(self._db)
            for stmt in statement_list:
                self._db.add_statement(stmt)
            end = len(self._db)
            self._range[theory_key] = (start, end)
            return True
        else: # Fail
            print("Trying to add to a theory that already exists: %s"%str(theory_key), file=sys_stderr)
            return False

    def remove_theory(self, theory_key):
        assert( theory_key is not None )
        def _is_impl_node(node):
            return isinstance(node, ClauseDB._clause) or isinstance(node, ClauseDB._fact)

        if theory_key in self._range:
            start, end = self._range[theory_key]
            for idx in range(start, end):
                node = self._db.get_node(idx)
                if _is_impl_node(node):
                    template_node = Term(node.functor, node.args)
                    define_idx = self._db.find(template_node)
                    if define_idx is not None:
                        define_node = self._db.get_node(define_idx)
                        define_node.children.erase( {idx} )

            self._range.pop(theory_key)
            return True
        else:
            print("Trying to remove a theory that doesn't exist: %s"%str(theory_key), file=sys_stderr)
            return False
