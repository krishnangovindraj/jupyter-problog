from ipykernel.kernelbase import Kernel
from problog.program import PrologString

from .problog_wrapper import ProblogWrapper

class ProblogKernel(Kernel):
    implementation = 'Problog'
    implementation_version = '1.0'
    language = 'prolog'  # will be used for
                         # syntax highlighting
    language_version = '2.1'
    language_info = {'name': 'problog',
                     'mimetype': 'text/x-prolog',
                     'extension': '.pl'}
    banner = "Problog notebook poc"

    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        if not hasattr(self, "pbl") or self.pbl is None:
            self.pbl = ProblogWrapper()

        # First: Get the cell_id if it has one. The first line with a %#
        # TODO: A version with a generator would be cooler
        lines = code.splitlines()
        mode = 0
        cell_id = None
        for ll in lines:
            l = ll.strip()
            if l:
                if l[:2] == "%#":
                    cell_id = ll[2:].strip()
                break


        queries, evidence = self.pbl.process_cell(cell_id, PrologString(code))
        query_probs = self.pbl.query(queries,evidence)
        # That is a dict[Term, prob]. Convert it to string, prob
        resp = "\n".join(["%s: %f"%(str(k), query_probs[k]) for k in query_probs])
        # print(res)
        if not silent:
            stream_content = {'name': 'stdout', 'text': resp}
            self.send_response(self.iopub_socket, 'stream', stream_content)

        return {'status': 'ok',
                # The base class increments the execution count
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
               }
