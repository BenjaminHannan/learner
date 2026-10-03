import hashlib, json
from pathlib import Path
H = Path(__file__).resolve().parent
files = ["EVAL-FORM-v2.json", "templates_eval2.json", "templates_train.json", "gen.py", "gen2.py", "model.py", "train.py", "PASS-MARKS-6.md", "EVAL2-CHECK-REPORT.md"]
seal = {f: hashlib.sha256((H / f).read_bytes()).hexdigest() for f in files}
(H / "SEAL-v2.json").write_text(json.dumps(seal, indent=1)); print("sealed", len(seal))
