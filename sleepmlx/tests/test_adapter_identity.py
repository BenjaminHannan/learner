import json
from pathlib import Path
import tempfile
import unittest

from sleepmlx.model import adapter_base_identity, validate_adapter_base
from sleepmlx.profile import load_profile


class AdapterIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.model = self.root / "model"
        self.model.mkdir()
        (self.model / "config.json").write_text('{"quantization":{"bits":3}}')
        self.adapter = self.root / "adapter"
        self.adapter.mkdir()
        self.profile = load_profile("apex35b_mlx", {})
        self.record = adapter_base_identity(self.profile, str(self.model))
        self.write_record(self.record)

    def write_record(self, record):
        data = {} if record is None else {"sleepmlx_base": record}
        (self.adapter / "adapter_config.json").write_text(json.dumps(data))

    def test_matching_base_is_accepted(self):
        validate_adapter_base(self.adapter, self.profile, str(self.model))

    def test_source_revision_and_quantization_mismatches_are_rejected(self):
        for field, value in (("hf_id", "Qwen/Qwen3.6-35B-A3B"), ("source_revision", "different"),
                             ("config_sha256", "0" * 64)):
            with self.subTest(field=field):
                self.write_record(dict(self.record, **{field: value}))
                with self.assertRaisesRegex(ValueError, "does not match"):
                    validate_adapter_base(self.adapter, self.profile, str(self.model))

    def test_pinned_base_can_move_to_another_directory(self):
        relocated = self.root / "relocated"
        relocated.mkdir()
        (relocated / "config.json").write_bytes((self.model / "config.json").read_bytes())
        validate_adapter_base(self.adapter, self.profile, str(relocated))

    def test_apex_refuses_missing_identity_but_legacy_k2_remains_readable(self):
        self.write_record(None)
        with self.assertRaisesRegex(ValueError, "no recorded base"):
            validate_adapter_base(self.adapter, self.profile, str(self.model))
        validate_adapter_base(self.adapter, load_profile("k2", {}), str(self.model))


if __name__ == "__main__":
    unittest.main()
