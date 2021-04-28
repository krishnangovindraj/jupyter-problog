from ipykernel.kernelbase import Kernel
from problog.program import PrologString

from .problog_wrapper import ProblogWrapper
from .query_session import QuerySession
class ProblogKernelException(RuntimeError):
    pass

class ProblogKernel(Kernel):
    implementation = 'Problog'
    implementation_version = '1.0'
    language = 'problog'
    language_version = '2.1'
    language_info = {'name': 'problog',
                     'mimetype': 'text/x-prolog',
                     'codemirror_mode': {'name': 'prolog'},
                     'pygments_lexer': 'prolog',
                     'extension': '.pl'}
    banner = "Problog notebook poc"


    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        tasks = []
        resp = ""

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

        cell_queries, cell_evidence = self.pbl.process_cell(cell_id, PrologString(code))


        qs = self.pbl.create_query_session()
        q_desc = []
        if cell_queries:
            tasks.append( (cell_queries, cell_evidence) )
            qs.prepare_query(cell_queries, cell_evidence)
            q_desc.append(None)

        for ll in lines:
            l = ll.strip()
            if l:
                if l[:2] == "%?":
                    inlineq = PrologString( l[2:].strip("-") )[0]
                    iq_query, iq_evidence = qs.transform_inline_query(inlineq)
                    tasks.append((iq_query, iq_evidence))
                    qs.prepare_query(iq_query, iq_evidence)
                    q_desc.append(inlineq)

        results = qs.evaluate_queries()
        # TODO: Error handling / acknowledgement of cells without queries running successfully
        # Format the response
        resp += self.format_results(results, tasks, q_desc)
        # Send the response
        if not silent:
            stream_content = {'name': 'stdout', 'text': resp}
            self.send_response(self.iopub_socket, 'stream', stream_content)

        return {'status': 'ok',
                # The base class increments the execution count
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
               }

    def format_results(self, results, tasks, q_desc):
        resp = ""
        for i, (query_probs, evidence) in enumerate(results):
            from sys import stderr
            if q_desc[i]:
                resp += "? %s\n"%str(q_desc[i])
            if evidence:
                resp += "evidence: %s\n"%evidence

            if q_desc[i]:
                q_head = tasks[i][0][0]
                assert(q_head.functor[:len(QuerySession.TIQ_HEAD_PREFIX)] == QuerySession.TIQ_HEAD_PREFIX)
                for q,p in query_probs:
                    subs =  ", ".join( ("%s=%s"%(varname,varval)) for varname,varval in zip(q_head.args,q.args) )
                    resp += "\t%s\n\tp: %f\n---\n"%(subs, p)
            else:
                resp += "(Cell queries)\n"
                resp += "\n".join(["\t%s:\t%f"%(q, p) for q,p in query_probs])
            resp += "\n= = = = = = \n"

        return resp
