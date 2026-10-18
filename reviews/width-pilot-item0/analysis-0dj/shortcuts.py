"""Candidate shortcut rules for the HO cell (K)*(J). Each: prompt -> int answer, or None when the rule is not defined on that prompt.
No model anywhere. Uses only domain.tools.sheet.evaluate as the calculator."""
from lib import *
RANGE = re.compile(r'[A-Z]\d+:[A-Z]\d+')
CELL = re.compile(r'[A-Z]\d+')
def val(prompt_grid, expr):
    v = sheet_tool.evaluate(f'{prompt_grid} ; ={expr}')['value']
    return int(v) if str(v).lstrip('-').isdigit() else None
def parts(prompt):
    f = formula(prompt); sp = split_formula(f)
    return grid_of(prompt), sp[1], sp[2]
def rule_K(prompt):  g,K,J=parts(prompt); return val(g,K)
def rule_J(prompt):  g,K,J=parts(prompt); return val(g,J)
def rule_KplusJ(prompt):
    g,K,J=parts(prompt); k,j=val(g,K),val(g,J); return None if None in (k,j) else k+j
def rule_KminusJ(prompt):
    g,K,J=parts(prompt); k,j=val(g,K),val(g,J); return None if None in (k,j) or k<j else k-j
def rule_absdiff(prompt):
    g,K,J=parts(prompt); k,j=val(g,K),val(g,J); return None if None in (k,j) else abs(k-j)
def rule_first_call(prompt):
    s=sheet_tool.evaluate(prompt)['steps']; return int(s[0][3]) if s and s[0][3].isdigit() else None
def rule_range_echo_K(prompt):
    """both pieces read the FIRST piece's range (defined only when each piece holds exactly one range, and they differ)"""
    g,K,J=parts(prompt); rk,rj=RANGE.findall(K),RANGE.findall(J)
    if len(rk)!=1 or len(rj)!=1: return None
    return val(g,K)*val(g,J.replace(rj[0],rk[0])) if val(g,K) is not None and val(g,J.replace(rj[0],rk[0])) is not None else None
def rule_range_echo_J(prompt):
    g,K,J=parts(prompt); rk,rj=RANGE.findall(K),RANGE.findall(J)
    if len(rk)!=1 or len(rj)!=1: return None
    a,b=val(g,K.replace(rk[0],rj[0])),val(g,J)
    return None if None in (a,b) else a*b
def rule_noparen(prompt):
    """brackets dropped, ordinary precedence (* before +): K_expr*J_expr read as written without ( )"""
    g,K,J=parts(prompt); return val(g,K+'*'+J) 
def rule_drop_join(prompt):
    """no join: K applied then J applied, the final answer is the last piece's result = J (same as rule_J)"""
    return rule_J(prompt)
