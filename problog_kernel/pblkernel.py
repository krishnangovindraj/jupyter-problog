from metaproblog.querying.query_factory import QueryFactory
from sys import stderr as sys_stderr
import traceback
from ipykernel.kernelbase import Kernel
from problog.program import PrologString

from .problog_wrapper import ProblogWrapper
from .query_session import QuerySession
class ProblogKernelException(RuntimeError):
    pass

class ProblogKernel(Kernel):

    HTML_OUTPUT = True

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
        try:
            tasks = []

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

            # TODO: Handle prepare failures
            qs = self.pbl.create_query_session()
            q_desc = []
            if cell_queries:
                tasks.append( (cell_queries, cell_evidence) )
                qs.prepare_query(cell_queries, cell_evidence, QueryFactory.QueryType.PROBABILITY)
                q_desc.append(None)

            for ll in lines:
                l = ll.strip()
                if l:
                    if l[:2] == "%?":
                        inlineq = PrologString( l[2:].strip("-") )[0]
                        iq_query, iq_evidence = qs.transform_inline_query(inlineq)
                        tasks.append((iq_query, iq_evidence))
                        qs.prepare_query(iq_query, iq_evidence, QueryFactory.QueryType.PROBABILITY)
                        q_desc.append(inlineq)

            results = qs.evaluate_queries()
            # TODO: Error handling / acknowledgement of cells without queries running successfully

            if not silent:
                # Format and send the response
                if ProblogKernel.HTML_OUTPUT:
                    # If we feel like html
                    resp_html = self.format_results_html(results, tasks, q_desc)
                    html_content = {'data': {'text/html': resp_html}}
                    self.send_response(self.iopub_socket, 'display_data', html_content)
                else:
                    resp_text = self.format_results_text(results, tasks, q_desc)
                    stream_content = {'name': 'stdout', 'text': resp_text}
                    self.send_response(self.iopub_socket, 'stream', stream_content)


            return {'status': 'ok',
                    # The base class increments the execution count
                    'execution_count': self.execution_count,
                    'payload': [],
                    'user_expressions': {},
                }
        except Exception as e:
            error_text = "An error occured: %s\nTraceback:\n %s\n"%(str(e), traceback.format_exc())
            stream_content = {'name': 'stdout', 'text': error_text}
            self.send_response(self.iopub_socket, 'stream', stream_content)
            return {'status': 'error',
                'execution_count': self.execution_count,
                'ename': 'ename: ' + str(e),
                'evalue': 'evalue: ' + str(e),
                'traceback': traceback.format_exc() # TODO: this
            }
            print(traceback)

    def format_results_text(self, results, tasks, q_desc):
        resp = ""
        for i, (query_probs, evidence) in enumerate(results):
            if q_desc[i]:
                resp += "? %s\n"%str(q_desc[i])
            if evidence:
                resp += "evidence: %s\n"%evidence

            if q_desc[i]:
                q_head = tasks[i][0][0]
                assert(q_head.functor[:len(QuerySession.TIQ_HEAD_PREFIX)] == QuerySession.TIQ_HEAD_PREFIX)
                if len(query_probs)==1 and isinstance(query_probs[0][1], dict):
                    resp += "QUERY FAILED!\n---\n"
                else:
                    for q,p in query_probs:
                        subs =  ", ".join( ("%s=%s"%(varname,varval)) for varname,varval in zip(q_head.args,q.args) )
                        resp += "\t%s\n\tp: %f\n---\n"%(subs, p)
            else:
                resp += "(Cell queries)\n"
                if len(query_probs)==1 and isinstance(query_probs[0][1], dict):
                    resp += "QUERY FAILED!\n---\n"
                else:
                    resp += "\n".join(["\t%s:\t%f"%(q, p) for q,p in query_probs])
            resp += "\n= = = = = = \n"

        return resp

    def format_results_html(self, results, tasks, q_desc):
        from html import escape as html_escape
        resp = "<div class=\"reponse\">"
        for i, (query_probs, evidence) in enumerate(results):
            resp += "<table class=\"query_results\">"

            if q_desc[i]:
                q_head = tasks[i][0][0]
                assert(q_head.functor[:len(QuerySession.TIQ_HEAD_PREFIX)] == QuerySession.TIQ_HEAD_PREFIX)

                resp += "\t<tr><th colspan=\"2\"><b>?</b> %s</th></tr>\n"%html_escape(str(q_desc[i]))
                if evidence:
                    resp += "\t<th colspan=\"2\"><b>evidence:</b> %s</th></tr>\n"%html_escape(str(evidence))
                if len(query_probs)==1 and isinstance(query_probs[0][1], dict):
                    resp += "\t<tr class=\"query_model\"><td colspan=\"2\"><b>FAILED</b></td></tr>\n"
                else:
                    for q,p in query_probs:
                        subs =  html_escape(", ".join( ("%s=%s"%(varname,varval)) for varname,varval in zip(q_head.args,q.args) ))
                        resp += "\t<tr class=\"query_model\"><td>%f</td><td>%s</td></tr>\n"%(p, subs)
            else:
                resp += "\t<tr><th colspan=\"2\">(Cell queries)</th></tr>\n"
                if evidence:
                    resp += "\t<tr><th colspan=\"2\"><b>evidence:</b> %s</th></tr>\n"%html_escape(str(evidence))
                if len(query_probs)==1 and isinstance(query_probs[0][1], dict):
                    resp += "\t<tr class=\"query_model\"><td colspan=\"2\"><b>FAILED</b></td></tr>\n"
                else:
                    resp += "\n".join(["<tr><td>%f</td><td>%s</td></tr>\n"%(p, html_escape(str(q))) for q,p in query_probs])
            resp += "</table>"
        resp += "</div>"
        return resp
