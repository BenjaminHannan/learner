"""Import the repo's templates.py by path without writing bytecode into the repo."""
import importlib.util, sys
from common import REPO
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("lg_templates", REPO + "/logicgen/templates.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
TEMPLATES, heldout_ids, train_ids = m.TEMPLATES, m.heldout_ids, m.train_ids
