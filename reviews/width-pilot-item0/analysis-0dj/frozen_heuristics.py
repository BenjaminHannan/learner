"""FROZEN before any TEST-11 number was computed (validity / depth / invalid-shallow). Three candidate heuristics for the HO cell
(prompt form  GRID ; =(K)*(J) ).  Each maps a prompt to an integer answer using only the prompt and the spreadsheet calculator
(domain.tools.sheet.evaluate); no model. 'valid' = heuristic answer == gold answer.

H1  J-ONLY.      Answer = the value of the second piece J alone (the join is skipped / the last piece's result is the answer).
H2  PLUS-JOIN.   Answer = K + J (values of the two pieces) -- the join is done with the training layouts' '+' instead of '*'.
H3  SHARED-CELLS. One set of cells for both pieces: rewrite J by replacing its cell references, in written order, with K's references
                 in written order (cycling through K's if J has more; a range put into a single-cell slot becomes its first cell; a
                 single cell put into a range slot becomes a one-cell range), then Answer = value(K) * value(rewritten J).
"""
import re
from lib import formula, split_formula, grid_of, sheet_tool
TOK = re.compile(r'[A-Z]\d+:[A-Z]\d+|[A-Z]\d+')

def _val(g, expr):
    v = sheet_tool.evaluate(f'{g} ; ={expr}')['value']
    return int(v) if str(v).isdigit() else None

def _pieces(prompt):
    sp = split_formula(formula(prompt)); return grid_of(prompt), sp[1], sp[2]

def H1(prompt):
    g, K, J = _pieces(prompt); return _val(g, J)

def H2(prompt):
    g, K, J = _pieces(prompt); k, j = _val(g, K), _val(g, J)
    return None if k is None or j is None else k + j

def H3(prompt):
    g, K, J = _pieces(prompt)
    kt, jt = TOK.findall(K), TOK.findall(J)
    out, i = [], 0
    def coerce(src, slot):
        s_rng, t_rng = ':' in src, ':' in slot
        if s_rng == t_rng: return src
        if s_rng: return src.split(':')[0]              # range into a cell slot -> its first cell
        return f'{src}:{src}'                           # cell into a range slot -> one-cell range
    cnt = [0]
    def sub(m):
        t = kt[cnt[0] % len(kt)]; cnt[0] += 1
        return coerce(t, m.group())
    J2 = TOK.sub(sub, J)
    k, j = _val(g, K), _val(g, J2)
    return None if k is None or j is None else k * j
