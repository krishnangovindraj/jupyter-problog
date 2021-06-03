from os import stat

from traitlets.traitlets import _deprecated_method
from .output_formatting import HTMLOutput
from sys import stderr as sys_stderr
import traceback
from ipykernel.kernelbase import Kernel

from problog.program import PrologString, DefaultPrologFactory
from problog.parser import PrologParser, Token

from .problog_wrapper import ProblogWrapper
from .query_session import QuerySession
from .kernel_options import default_options, OptionKeys
from metaproblog.querying.query_factory import QueryFactory

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_parser = ProblogKernel._create_custom_parser()
        self.outputter = HTMLOutput()
        self.options = {}
        self.options.update( default_options )

    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        try:
            active_options = dict(self.options)

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


            cell_queries, cell_evidence, questions = self.pbl.process_cell(cell_id, PrologString(code, parser=self.custom_parser))

            # TODO: Handle prepare failures
            qs = self.pbl.create_query_session()
            queries = []
            query_info = {}

            for q in questions:
                mode, inlineq = (q.args[0], q.args[1]) if q.arity == 2 else (None, q.args[0])
                if mode is not None and mode.functor == "set":
                    self._update_options(inlineq, self.options)
                    self._update_options(inlineq, active_options)
                elif mode is not None and mode.functor == "with":
                    self._update_options(inlineq, active_options)
                else:
                    query_type_spec = active_options[OptionKeys.QUERY_TYPE] if mode is None else mode
                    iq_query, iq_evidence = qs.transform_inline_query(inlineq)

                    qobj = qs.prepare_query(iq_query, iq_evidence, query_type_spec)
                    queries.append(qobj)
                    query_info[qobj] = {"query": (iq_query, iq_evidence), "inline_query": inlineq}

            if cell_queries:
                qobj = qs.prepare_query(cell_queries, cell_evidence, active_options[OptionKeys.QUERY_TYPE])
                queries.append(qobj)
                query_info[qobj] = {"query": (cell_queries, cell_evidence)}

            results = qs.evaluate_queries()
            # TODO: Error handling / acknowledgement of cells without queries running successfully

            if not silent:
                # Format and send the response
                output_type, content = self.outputter.format_all(queries, query_info)
                self.send_response(self.iopub_socket, output_type, content)


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

    """ deprecating """
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

    def _update_options(self, body, which_options):
        key, value = (body.args[0], body.args[1]) if body.functor == "'='" \
                            else (body.args[0], True)
        which_options[key] = value

    @staticmethod
    def _create_custom_parser():
        PrologParser._custom_token_question = _custom_token_question
        parser = PrologParser(DefaultPrologFactory(identifier=0))
        parser._token_act2[ord('?')-58] = parser._custom_token_question
        return parser


def _custom_token_question(self, s, pos):
    return (
            Token(
                "?",
                pos,
                unop=(1500, "fy", self.factory.build_unop),
                binop=(1500, "yfx", self.factory.build_binop),
                functor=self._next_paren_open(s, pos),
            ),
            pos + 1,
        )
