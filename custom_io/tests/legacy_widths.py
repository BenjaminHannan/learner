"""T1SDR's operand cells and tape width (11 / 40, as at 17a356e62) for the uncapped tool tests. The no-truncation audit (1d69257a99) raised them to
21 / 68, which needs the caps' place table (n_reg + 1 = 37 rows); uncapped, the reader has 16 place rows and Tool refuses to build. The real widths
are tested under the caps (test_b3 child_caps). Call apply() before anything imports CELLS, LE or SPAN_MAX by value."""
import importlib


def apply():
    for name in ('custom_io.models.tool', 'custom_io.models.tool_h1', 'custom_io.models.b3'):
        mod = importlib.import_module(name)
        for k, v in dict(CELLS=11, LE=40, SPAN_MAX=40).items():
            if hasattr(mod, k):
                setattr(mod, k, v)
