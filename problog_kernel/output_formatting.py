from sys import stderr as sys_stderr
from html import escape as html_escape

from metaproblog.querying.sample_query import SampleQuery
from metaproblog.querying.amc_query import AMCQuery
from .query_session import QuerySession

class OutputFormat:
    def format_result(self, query, result, query_info):
        raise NotImplementedError("OutputFormat is abstract")


class HTMLOutput(OutputFormat):

    def format_all(self, queries, query_info):
        from html import escape as html_escape
        resp = "<div class=\"reponse\">"
        for query in queries:
            resp += self.format_result(query, query_info[query])
        resp += "</div>"
        # print("RESP IS:", resp, file=sys_stderr)
        return 'display_data', {'data': {'text/html': resp}}


    def format_result(self, query, query_info):
        if isinstance(query, AMCQuery):
            return self._format_result_amcquery(query, query_info)
        elif isinstance(query, SampleQuery):
            return self._format_result_samplequery(query, query_info)
        else:
            return "<pre>Unsupported yet<br/>: %s</pre>"%(str(query.results))

    def _format_result_amcquery(self, query, query_info):
        resp = ""
        resp += "<table class=\"query_results\">"
        query_probs, evidence = query.results
        q_terms, ev_terms = query_info["query"]
        if "inline_query" in query_info:
            iq  = query_info["inline_query"]
            original_iq= iq # iq.args[0] if iq.functor == "|" else iq

            resp += "\t<tr><th colspan=\"2\"><b>?</b> %s</th></tr>\n"%html_escape(str(original_iq))
            if evidence:
                resp += "\t<th colspan=\"2\"><b>evidence:</b> %s</th></tr>\n"%html_escape(str(evidence))
            if len(query_probs)==1 and isinstance(query_probs[0][1], dict):
                resp += "\t<tr class=\"query_model\"><td colspan=\"2\"><b>FAILED</b></td></tr>\n"
            else:
                for q,p in query_probs:
                    subs =  html_escape(", ".join( ("%s=%s"%(varname,varval)) for varname,varval in zip(q_terms[0].args,q.args) ))
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

        return resp


    def _format_result_samplequery(self, query, query_info):
        resp = ""
        resp += "<table class=\"query_results\">"
        samples, evidence = query.results
        q_terms, ev_terms = query_info["query"]
        if "inline_query" in query_info:
            original_iq = query_info["inline_query"]
            resp += "\t<tr><th><b>?</b> %s</th></tr>\n"%html_escape(str(original_iq))
        else:
            resp += "\t<tr><th>(Cell queries)</th></tr>\n"


        if evidence:
            resp += "\t<th><b>evidence:</b> %s</th></tr>\n"%html_escape(str(evidence))
        if False: # TODO: What does sampling look like on failure?
            resp += "\t<tr class=\"query_model\"><td colspan=\"2\"><b>FAILED</b></td></tr>\n"
        else:
            for sample_dict in samples:
                resp += "\t<tr class=\"query_model\"><td>%s</td></tr>\n"%( ", ".join(str(k) for k in sample_dict if sample_dict[k]))

        resp += "</table>"

        return resp

#TODO: Add TextOutputter
