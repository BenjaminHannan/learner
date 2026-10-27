import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SH_RUNNER = ROOT / "scripts" / "remote_benspc.sh"
PS_RUNNER = ROOT / "scripts" / "remote_benspc.ps1"
REMOTE_PROJECT = "C:/Users/benja/beautiful-model"
RUN_ID = "20260918T141500Z-0a1b2c3d"
TRANSPORT_TIMEOUT_OPTIONS = {
    "ConnectTimeout=10",
    "ServerAliveInterval=15",
    "ServerAliveCountMax=2",
}


class RemoteRunnerTests(unittest.TestCase):
    def assert_transport_timeouts(self, log, *, expected_commands=None):
        lines = [
            line
            for line in log.splitlines()
            if line.startswith("ssh\t") or line.startswith("scp\t")
        ]
        self.assertTrue(lines, "expected at least one fake ssh/scp invocation")
        if expected_commands is not None:
            commands = {line.split("\t", 1)[0] for line in lines}
            self.assertEqual(commands, set(expected_commands))

        for line in lines:
            fields = line.split("\t")
            if fields[0] == "ssh":
                self.assertIn("-n", fields, line)
            for option in TRANSPORT_TIMEOUT_OPTIONS:
                self.assertIn(option, fields, line)
                index = fields.index(option)
                self.assertGreater(index, 0, line)
                self.assertEqual(fields[index - 1], "-o", line)

    def run_shell(self, *args, env_overrides=None):
        with tempfile.TemporaryDirectory() as temporary:
            fake_bin = Path(temporary) / "bin"
            fake_bin.mkdir()
            marker = Path(temporary) / "ssh-invoked"
            fake_ssh = fake_bin / "ssh"
            fake_ssh.write_text(
                "#!/bin/sh\nprintf 'ssh invoked\\n' > \"$SSH_MARKER\"\nexit 99\n",
                encoding="utf-8",
            )
            fake_ssh.chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{fake_bin}{os.pathsep}{env.get('PATH', '')}",
                    "SSH_MARKER": str(marker),
                    "BENSPC_HOST": "offline.invalid",
                }
            )
            if env_overrides:
                env.update(env_overrides)

            result = subprocess.run(
                ["sh", str(SH_RUNNER), *args],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=False,
            )
            self.assertFalse(marker.exists(), "test unexpectedly reached ssh")
            return result

    def run_shell_captured(
        self, *args, env_overrides=None, ssh_stdout="", project=None, scp_writes=False
    ):
        """Run against fake ssh/scp binaries and return their argv log.

        The fake ssh prints ``ssh_stdout``. With ``scp_writes`` the fake scp
        writes "remote copy" to its destination path. With ``project`` the
        runner is copied into that directory so local writes land there.
        """
        runner = SH_RUNNER
        if project is not None:
            (project / "scripts").mkdir(parents=True, exist_ok=True)
            runner = project / "scripts" / "remote_benspc.sh"
            shutil.copy(SH_RUNNER, runner)
        with tempfile.TemporaryDirectory() as temporary:
            fake_bin = Path(temporary) / "bin"
            fake_bin.mkdir()
            command_log = Path(temporary) / "commands.log"
            stdout_file = Path(temporary) / "ssh-stdout.txt"
            stdout_file.write_bytes(ssh_stdout.encode("utf-8"))
            extra = {
                "ssh": 'cat "$FAKE_SSH_STDOUT"\n',
                "scp": (
                    'if [ -n "${FAKE_SCP_WRITES:-}" ]; then\n'
                    '    for arg in "$@"; do last=$arg; done\n'
                    "    printf 'remote copy\\n' > \"$last\"\n"
                    "fi\n"
                ),
            }
            for name in ("ssh", "scp"):
                executable = fake_bin / name
                executable.write_text(
                    "#!/bin/sh\n"
                    f"printf '{name}' >> \"$COMMAND_LOG\"\n"
                    "for arg in \"$@\"; do printf '\\t%s' \"$arg\" >> \"$COMMAND_LOG\"; done\n"
                    "printf '\\n' >> \"$COMMAND_LOG\"\n"
                    + extra[name]
                    + "exit 0\n",
                    encoding="utf-8",
                )
                executable.chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{fake_bin}{os.pathsep}{env.get('PATH', '')}",
                    "COMMAND_LOG": str(command_log),
                    "FAKE_SSH_STDOUT": str(stdout_file),
                    "BENSPC_HOST": "offline.invalid",
                }
            )
            if scp_writes:
                env["FAKE_SCP_WRITES"] = "1"
            if env_overrides:
                env.update(env_overrides)

            result = subprocess.run(
                ["sh", str(runner), *args],
                cwd=ROOT if project is None else project,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                check=False,
            )
            log = command_log.read_text(encoding="utf-8") if command_log.exists() else ""
            return result, log

    @staticmethod
    def powershell_function(name):
        text = PS_RUNNER.read_text(encoding="utf-8")
        body = text.split(f"function {name} {{", 1)[1]
        return re.split(r"^(?:function |switch \(\$Action\))", body, maxsplit=1, flags=re.M)[0]

    def test_help_is_local_and_documents_commands(self):
        result = self.run_shell("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("preflight|sync|test|pilot|launch|status|fetch|stop", result.stdout)
        self.assertIn("BENSPC_PILOT_SECONDS", result.stdout)
        for command in ("launch [run.py args...]", "status RUN_ID", "fetch RUN_ID", "stop RUN_ID"):
            self.assertIn(command, result.stdout)

    def test_unsafe_host_is_rejected_before_ssh(self):
        result = self.run_shell(
            "preflight", env_overrides={"BENSPC_HOST": "unsafe host;example"}
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("BENSPC_HOST contains unsafe characters", result.stderr)

    def test_unsafe_remote_project_is_rejected_before_ssh(self):
        result = self.run_shell(
            "preflight",
            env_overrides={"BENSPC_REMOTE_PROJECT": "C:/Users/other/beautiful-model"},
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("must stay below C:/Users/benja/", result.stderr)

    def test_invalid_pilot_limit_is_rejected_before_ssh(self):
        result = self.run_shell(
            "pilot", env_overrides={"BENSPC_PILOT_SECONDS": "601"}
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("must be between 1 and 600", result.stderr)

    def test_preflight_reports_pilot_readiness_without_low_vram_rejection(self):
        result, log = self.run_shell_captured(
            "preflight", env_overrides={"BENSPC_MIN_FREE_MIB": "15000"}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nvidia-smi", log)
        self.assertIn("PILOT_GPU_READY=false", log)
        self.assertIn("PILOT_GPU_STATUS=LOW_VRAM", log)
        self.assertNotIn("Refusing to run: GPU free memory", log)
        self.assert_transport_timeouts(log, expected_commands={"ssh"})

    def test_cpu_test_command_has_no_gpu_gate(self):
        result, log = self.run_shell_captured(
            "test",
            env_overrides={
                "BENSPC_MIN_FREE_MIB": "not-used-by-test",
                "BENSPC_GPU_INDEX": "also-not-used",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-Action Test", log)
        self.assertNotIn("nvidia-smi", log)
        self.assertNotIn("-MinFreeMiB", log)
        self.assertNotIn("-GpuIndex", log)
        self.assert_transport_timeouts(log, expected_commands={"ssh"})

        powershell_text = PS_RUNNER.read_text(encoding="utf-8")
        fast_tests = powershell_text.split("function Invoke-FastTests {", 1)[1].split(
            "function New-PilotRuntime {", 1
        )[0]
        self.assertIn("Assert-Ready -RequireProject", fast_tests)
        self.assertNotIn("RequireGpuCapacity", fast_tests)
        self.assertIn('$env:CUDA_VISIBLE_DEVICES = "-1"', fast_tests)
        self.assertIn("Push-Location -LiteralPath $project", fast_tests)
        self.assertIn('$_.Name -ne "test_remote_runner.py"', fast_tests)
        self.assertIn('"tests." + $_.BaseName', fast_tests)

    def test_pilot_command_alone_carries_gpu_floor_timeout_and_real_cli_args(self):
        result, log = self.run_shell_captured(
            "pilot",
            "audit",
            "--save",
            env_overrides={
                "BENSPC_MIN_FREE_MIB": "15000",
                "BENSPC_GPU_INDEX": "1",
                "BENSPC_PILOT_SECONDS": "37",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-Action Pilot", log)
        self.assertIn("-MinFreeMiB 15000", log)
        self.assertIn("-GpuIndex 1", log)
        self.assertIn("-PilotSeconds 37", log)
        self.assertIn('-PilotArgsText "audit --save"', log)
        self.assert_transport_timeouts(log, expected_commands={"ssh"})

        powershell_text = PS_RUNNER.read_text(encoding="utf-8")
        pilot = powershell_text.split("function Invoke-Pilot {", 1)[1].split(
            "switch ($Action)", 1
        )[0]
        self.assertIn("Assert-Ready -RequireProject -RequireGpuCapacity", pilot)
        self.assertIn('@("-B", $runPy, "--runtime", $runtime) + $pilotTokens', pilot)

    def test_pilot_without_args_uses_run_py_default_not_fake_pilot_subcommand(self):
        result, log = self.run_shell_captured("pilot")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-Action Pilot", log)
        self.assertNotIn("-PilotArgsText", log)
        self.assert_transport_timeouts(log, expected_commands={"ssh"})

        powershell_text = PS_RUNNER.read_text(encoding="utf-8")
        self.assertIn('[string] $PilotArgsText = ""', powershell_text)
        self.assertNotIn('[string] $PilotArgsText = "pilot"', powershell_text)

    def test_sync_is_gpu_independent_non_deleting_and_excludes_runtime_state(self):
        result, log = self.run_shell_captured(
            "sync",
            env_overrides={
                "BENSPC_MIN_FREE_MIB": "not-used-by-sync",
                "BENSPC_GPU_INDEX": "also-not-used",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("nvidia-smi", log)
        self.assertNotIn("-MinFreeMiB", log)
        self.assertNotIn("-GpuIndex", log)
        self.assert_transport_timeouts(log, expected_commands={"ssh", "scp"})

        excluded_dirs = {".budget", ".runtime", ".git", "__pycache__", "artifacts", "cache"}
        expected = []
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
            if any(part in excluded_dirs for part in relative.parts[:-1]):
                continue
            relative_text = relative.as_posix()
            self.assertRegex(relative_text, r"^[A-Za-z0-9_./-]+$")
            expected.append(relative_text)

        scp_lines = [line for line in log.splitlines() if line.startswith("scp\t")]
        copied = set()
        for line in scp_lines:
            fields = line.split("\t")
            self.assertGreaterEqual(len(fields), 6)
            local_path = Path(fields[-2])
            remote_path = fields[-1]
            relative = local_path.relative_to(ROOT).as_posix()
            copied.add(relative)
            self.assertTrue(remote_path.endswith("/" + relative), remote_path)
            self.assertFalse(any(part in excluded_dirs for part in Path(relative).parts[:-1]))
        self.assertEqual(copied, set(expected))

        shell_text = SH_RUNNER.read_text(encoding="utf-8")
        self.assertNotRegex(shell_text, re.compile(r"^\s*(?:rm|rmdir|del)\b", re.MULTILINE | re.I))
        self.assertIn("-name cache", shell_text)

    def test_transport_binaries_are_only_called_inside_timeout_wrappers(self):
        shell_text = SH_RUNNER.read_text(encoding="utf-8")
        executable_lines = [
            line.strip()
            for line in shell_text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        direct_ssh = [line for line in executable_lines if re.match(r"^ssh\s", line)]
        direct_scp = [line for line in executable_lines if re.match(r"^scp\s", line)]
        self.assertEqual(direct_ssh, ["ssh \\"])
        self.assertEqual(direct_scp, ["scp \\"])
        self.assertIn('-o "ConnectTimeout=$SSH_CONNECT_TIMEOUT_SECONDS"', shell_text)
        self.assertIn('-o "ServerAliveInterval=$SSH_SERVER_ALIVE_INTERVAL_SECONDS"', shell_text)
        self.assertIn('-o "ServerAliveCountMax=$SSH_SERVER_ALIVE_COUNT_MAX"', shell_text)

    def test_windows_runtime_budget_scope_is_explicitly_project_local(self):
        powershell_text = PS_RUNNER.read_text(encoding="utf-8")
        self.assertIn("hard_bytes = 100000000000", powershell_text)
        self.assertIn("steady_bytes = 80000000000", powershell_text)
        self.assertIn('budget_scope = "remote_project_and_registered_roots_only"', powershell_text)
        self.assertIn("global_100gb_enforced = $false", powershell_text)
        self.assertIn("Host-global aggregation is not enforced", powershell_text)

    def test_scripts_have_no_indiscriminate_process_stop_commands(self):
        shell_text = SH_RUNNER.read_text(encoding="utf-8")
        powershell_text = PS_RUNNER.read_text(encoding="utf-8")

        shell_commands = "\n".join(
            line for line in shell_text.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotRegex(
            shell_commands,
            re.compile(r"^\s*(?:kill|killall|pkill|taskkill(?:\.exe)?)\b", re.MULTILINE),
        )

        ps_commands = [
            line.strip()
            for line in powershell_text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        stop_commands = [line for line in ps_commands if line.startswith("Stop-Process")]
        self.assertEqual(
            stop_commands,
            ["Stop-Process -Id $process.Id -Force -ErrorAction Stop"],
            "only the exact child pilot PID may be stopped",
        )
        self.assertFalse(
            any(re.match(r"^(?:Get-Process|taskkill(?:\.exe)?|kill|killall|pkill)\b", line, re.I)
                for line in ps_commands),
            "runner must not enumerate or indiscriminately terminate processes",
        )

        # The only other termination is Stop's Kill of the verified run process.
        self.assertEqual(powershell_text.count(".Kill()"), 1)
        self.assertIn("$process.Kill()", self.powershell_function("Invoke-Stop"))

        remove_commands = [line for line in ps_commands if line.startswith("Remove-Item")]
        self.assertEqual(
            remove_commands,
            ["Remove-Item -LiteralPath $runtime -Force"],
            "only the per-invocation temporary runtime file may be removed",
        )

    def test_run_id_arguments_are_validated_before_ssh(self):
        unsafe = ["", "../x", "a/b", "a b", "a;b", "a$b", "C:x", "a\\b", "-Action", "x" * 65, "abc\n"]
        for command in ("status", "fetch", "stop"):
            for run_id in unsafe:
                with self.subTest(command=command, run_id=run_id):
                    result = self.run_shell(command, run_id)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("run_id", result.stderr)
            for args in ((), (RUN_ID, RUN_ID)):
                with self.subTest(command=command, args=args):
                    result = self.run_shell(command, *args)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("exactly one RUN_ID", result.stderr)

    def test_launch_rejects_unsafe_arguments_before_ssh(self):
        for args in (("pilot", "--x=1;calc"), ("pilot", ""), ("a b",), ('say"hi"',), ("x" * 2001,)):
            with self.subTest(args=args):
                result = self.run_shell("launch", *args)
                self.assertEqual(result.returncode, 2)
        result = self.run_shell("launch", "audit", env_overrides={"BENSPC_MIN_FREE_MIB": "0"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("BENSPC_MIN_FREE_MIB", result.stderr)

    def test_launch_generates_safe_unique_run_id_and_carries_gpu_gate(self):
        run_ids = []
        for _ in range(2):
            result, log = self.run_shell_captured(
                "launch",
                "bench",
                "--device=cuda",
                env_overrides={"BENSPC_MIN_FREE_MIB": "15000", "BENSPC_GPU_INDEX": "1"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_transport_timeouts(log, expected_commands={"ssh"})
            ssh_lines = [line for line in log.splitlines() if line.startswith("ssh\t")]
            self.assertEqual(len(ssh_lines), 1)
            remote = ssh_lines[0].split("\t")[-1]
            self.assertIn(
                f"-File {REMOTE_PROJECT}/scripts/remote_benspc.ps1 -Action Launch -ProjectPath {REMOTE_PROJECT}",
                remote,
            )
            self.assertIn("-MinFreeMiB 15000", remote)
            self.assertIn("-GpuIndex 1", remote)
            self.assertIn('-PilotArgsText "bench --device=cuda"', remote)
            self.assertNotIn("-PilotSeconds", remote)
            run_id = re.search(r"-RunId (\S+)", remote).group(1)
            self.assertRegex(run_id, r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")
            self.assertEqual(result.stdout.splitlines()[-1], f"RUN_ID={run_id}")
            run_ids.append(run_id)
        self.assertNotEqual(run_ids[0], run_ids[1])

        result, log = self.run_shell_captured("launch")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("-PilotArgsText", log)

    def test_launch_helper_gates_vram_detaches_and_records_identity(self):
        launch = self.powershell_function("Invoke-Launch")
        self.assertIn("Assert-Ready -RequireProject -RequireGpuCapacity", launch)
        self.assertIn("$null = New-Item -ItemType Directory -Path $runDir\n", launch)
        self.assertIn("Invoke-CimMethod -ClassName Win32_Process -MethodName Create", launch)
        self.assertIn("-Action Supervise", launch)

        supervise = self.powershell_function("Invoke-Supervise")
        self.assertIn('-RedirectStandardOutput (Join-Path $runDir "stdout.log")', supervise)
        self.assertIn('-RedirectStandardError (Join-Path $runDir "stderr.log")', supervise)
        self.assertIn("$null = $process.Handle", supervise)
        for key in ("run_id", "pid", "process_start_time", "command_line", "started_at"):
            self.assertRegex(supervise, rf"\n\s+{key} = ")
        self.assertIn('"run.json"', supervise)
        self.assertIn('"exit.json"', supervise)
        self.assertIn("exit_code = $process.ExitCode", supervise)

        # PowerShell's -match is case-insensitive; \z also rejects a trailing newline.
        self.assertIn("'^[A-Za-z0-9_][A-Za-z0-9_-]{0,63}\\z'", self.powershell_function("Get-RunDirectory"))

    def test_status_and_stop_are_run_scoped_and_verify_process_identity(self):
        for command, action in (("status", "Status"), ("stop", "Stop")):
            with self.subTest(command=command):
                result, log = self.run_shell_captured(command, RUN_ID)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assert_transport_timeouts(log, expected_commands={"ssh"})
                self.assertIn(
                    f"-Action {action} -ProjectPath {REMOTE_PROJECT} -RunId {RUN_ID}", log
                )
                self.assertNotIn("-MinFreeMiB", log)
        result, log = self.run_shell_captured(
            "status", RUN_ID, env_overrides={"BENSPC_GPU_INDEX": "1"}
        )
        self.assertIn("-GpuIndex 1", log)

        identity = self.powershell_function("Get-LiveRunProcess")
        self.assertIn("$null = $process.Handle", identity)
        self.assertIn("$started -cne [string]$Run.process_start_time", identity)
        self.assertIn("$cim.CommandLine -cne [string]$Run.command_line", identity)
        stop = self.powershell_function("Invoke-Stop")
        self.assertLess(stop.index("Get-LiveRunProcess $run"), stop.index("$process.Kill()"))
        self.assertIn("if ($null -eq $process)", stop)
        status = self.powershell_function("Invoke-Status")
        self.assertIn("Get-GpuState", status)
        self.assertIn("-Tail 20", status)

    def test_fetch_copies_listed_files_without_overwriting_local_files(self):
        listing = (
            "HOST=BENSPC\r\n"
            "RUNFILE=exit.json\r\n"
            "RUNFILE=run.json\r\n"
            "RUNFILE=stdout.log\r\n"
            "ARTIFACT=artifacts/result-1.json\r\n"
            "ARTIFACT=artifacts/kept.json\r\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            local_run = project / "artifacts" / "benspc" / RUN_ID
            (local_run / "artifacts").mkdir(parents=True)
            (local_run / "stdout.log").write_text("local original\n", encoding="utf-8")
            (local_run / "artifacts" / "kept.json").write_text("local kept\n", encoding="utf-8")

            result, log = self.run_shell_captured(
                "fetch", RUN_ID, ssh_stdout=listing, project=project, scp_writes=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_transport_timeouts(log, expected_commands={"ssh", "scp"})
            self.assertIn(f"-Action Files -ProjectPath {REMOTE_PROJECT} -RunId {RUN_ID}", log)

            scp_sources = [
                line.split("\t")[-2] for line in log.splitlines() if line.startswith("scp\t")
            ]
            remote_run = f"offline.invalid:{REMOTE_PROJECT}/.runtime/runs/{RUN_ID}"
            self.assertEqual(
                sorted(scp_sources),
                sorted(
                    [
                        f"{remote_run}/exit.json",
                        f"{remote_run}/run.json",
                        f"offline.invalid:{REMOTE_PROJECT}/artifacts/result-1.json",
                    ]
                ),
            )
            self.assertEqual((local_run / "stdout.log").read_text(encoding="utf-8"), "local original\n")
            self.assertEqual(
                (local_run / "artifacts" / "kept.json").read_text(encoding="utf-8"), "local kept\n"
            )
            for fetched in ("exit.json", "run.json", "artifacts/result-1.json"):
                self.assertEqual((local_run / fetched).read_text(encoding="utf-8"), "remote copy\n")
            self.assertEqual(list(project.rglob("*.partial")), [])
            self.assertIn("kept existing artifacts/benspc/", result.stdout)
            self.assertNotIn("HOST=", "".join(p.name for p in project.rglob("*")))

    def test_fetch_rejects_unsafe_listing_names(self):
        for line in (
            "RUNFILE=../evil",
            "RUNFILE=..",
            "RUNFILE=.hidden",
            "RUNFILE=a/b",
            "ARTIFACT=artifacts/../../evil",
            "ARTIFACT=artifacts/sub/x.json",
            "ARTIFACT=C:/Windows/win.ini",
            "RUNFILE",
        ):
            with self.subTest(line=line):
                with tempfile.TemporaryDirectory() as temporary:
                    project = Path(temporary) / "project"
                    result, log = self.run_shell_captured(
                        "fetch", RUN_ID, ssh_stdout=line + "\n", project=project, scp_writes=True
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertNotIn("scp\t", log)
                    self.assertFalse((project / "artifacts").exists())
                    self.assertFalse((Path(temporary) / "evil").exists())


if __name__ == "__main__":
    unittest.main()
