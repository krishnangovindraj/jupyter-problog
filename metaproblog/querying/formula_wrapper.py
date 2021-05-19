from sys import stderr as sys_stderr

from problog.formula import LogicFormula

class FormulaWrapper:
    def __init__(self, db):
        self.db = db
        self.lf = LogicFormula()
        self._current_version = 0
        self._compiled = {}

    """ Use this if you want to be grounding stuff """
    def next_version(self):
        self._current_version += 1
        return self._current_version

    def compile_to(self, target_class, target_version = None):
        # TODO: Should we cache intermediate steps to save effort?
        if target_version is None:
            target_version = self._current_version
        
        if target_class not in self._compiled:
            self._compiled[target_class] = (self._current_version, target_class.create_from(self.lf))
        
        version, target = self._compiled[target_class]
        if version < target_version:
            print("Outdated compilation. Recompiling.", file=sys_stderr)
            self._compiled[target_class] = (self._current_version, target_class.create_from(self.lf))
            version, target = self._compiled[target_class]
        
        return target
