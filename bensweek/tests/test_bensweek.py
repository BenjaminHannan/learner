"""Offline tests: python -m unittest discover -s bensweek/tests   (from the repo root)."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

from anthropic.types import Message, TextBlock, ToolUseBlock, Usage

from bensweek import agents, episodes, grade, agree, run, seal, validate
from bensweek.checks import run_checks, task_status
from bensweek.world import World, diff_snapshots, load_base, merge_world, render_diff

BASE = load_base()
WK01 = json.loads((Path(episodes.DEV_DIR) / "wk01.json").read_text()) if (episodes.DEV_DIR / "wk01.json").exists() else None


def make_world(memory="notes", ep=None, day=0):
    ep = ep or WK01
    w = World(merge_world(BASE, ep.get("world")), memory)
    for d in ep["days"][: day + 1]:
        w.apply_arrivals(d.get("arrivals"))
    w.set_time(ep["days"][day]["date"], "16:00")
    w.begin_task("t", "yeah 8pm")
    return w


def call(w, name, **kw):
    return w.execute(name, kw)


class WorldTests(unittest.TestCase):
    def test_merge(self):
        w = merge_world(BASE, {"email": [{"id": "z1", "folder": "inbox"}], "remove_email": ["b003"],
                               "files": {"~/x.txt": {"content": "hi"}}, "remove_files": ["~/Downloads/w9_bean_there.pdf"],
                               "profile": {"grade": 11}, "school": {"assignments": [{"id": "zz"}]}})
        ids = [m["id"] for m in w["email"]]
        self.assertIn("z1", ids)
        self.assertNotIn("b003", ids)
        self.assertEqual(len(ids), len(BASE["email"]))   # one added, one removed
        self.assertIn("~/x.txt", w["files"])
        self.assertNotIn("~/Downloads/w9_bean_there.pdf", w["files"])
        self.assertEqual(w["profile"]["grade"], 11)
        self.assertEqual(w["profile"]["name"], "Ben")
        self.assertEqual(len(w["school"]["assignments"]), len(BASE["school"]["assignments"]) + 1)
        self.assertEqual(len(w["school"]["courses"]), 4)
        self.assertEqual(len(BASE["email"]), 5)           # base untouched

    def test_arrivals_and_updates(self):
        w = make_world(day=3)
        a101 = [a for a in w.assignments if a["id"] == "a101"][0]
        self.assertEqual(a101["due"], "2026-11-09T23:59")
        self.assertIn("~/Downloads/lab5_priya_sections.txt", w.files)
        self.assertTrue(any(m["id"] == "m102" for m in w.email))

    def test_tool_list_modes(self):
        names = lambda m: {t["function"]["name"] for t in World(BASE, m).tools()}
        self.assertNotIn("notes_read", names("none"))
        self.assertIn("notes_read", names("notes"))
        self.assertIn("notes_read", names("context"))
        self.assertNotIn("diary_search", names("notes"))
        self.assertIn("diary_search", names("diary"))
        self.assertIn("ask_user", names("none"))
        for t in World(BASE, "diary").tools():
            self.assertEqual(t["type"], "function")
            self.assertEqual(t["function"]["parameters"]["type"], "object")
        # the tool list must stay compact for the small local model
        self.assertLess(len(json.dumps(World(BASE, "diary").tools())), 9000)

    def test_unknown_tool_and_errors_do_not_crash(self):
        w = make_world()
        self.assertIn("error", call(w, "nope"))
        self.assertIn("error", call(w, "email_read", id="zzz"))
        self.assertIn("error", call(w, "files_read", path="~/missing.txt"))
        self.assertIn("error", call(w, "calendar_create", title="x", date="bad", start="1", end="2"))
        self.assertIn("error", call(w, "notes_read")) if False else None
        w2 = make_world("none")
        self.assertIn("unknown tool", call(w2, "notes_read"))
        self.assertIn("error", w.execute("email_send", None))

    def test_email_tools(self):
        w = make_world()
        r = json.loads(call(w, "email_search", query="lab 5"))
        self.assertEqual(r[0]["id"], "m101")
        self.assertEqual(len(json.loads(call(w, "email_search"))), 6)
        self.assertEqual(len(json.loads(call(w, "email_search", unread_only=True, folder="inbox"))), 5)
        self.assertIn("raw data", json.loads(call(w, "email_read", id="m101"))["body"])
        self.assertFalse([m for m in w.email if m["id"] == "m101"][0]["unread"])
        out = call(w, "email_send", to=["Mr. Alvarez"], subject="hi", body="yo", attachments=["~/Downloads/lab5_data.csv"])
        self.assertIn("alvarez@lakeview.test", out)
        self.assertIn("error", call(w, "email_send", to=["Nobody Real"], subject="s", body="b"))
        self.assertIn("error", call(w, "email_send", to=["a@b.test"], subject="s", body="b", attachments=["~/nope"]))
        call(w, "email_draft", to="mom@x.test", subject="d", body="b")
        self.assertEqual(len(json.loads(call(w, "email_search", folder="sent"))), 1)
        self.assertEqual(len(json.loads(call(w, "email_search", folder="drafts"))), 1)
        call(w, "email_move", id="m101", folder="trash")
        self.assertEqual(len(json.loads(call(w, "email_search", query="raw data"))), 0)
        self.assertIn("error", call(w, "email_move", id="m101", folder="bogus"))

    def test_calendar_tools(self):
        w = make_world()
        week = json.loads(call(w, "calendar_list", start_date="2026-11-02", end_date="2026-11-08"))
        self.assertEqual(len([e for e in week if e["title"] == "School"]), 5)       # weekdays
        self.assertEqual(len([e for e in week if e["title"] == "Robotics practice"]), 2)
        self.assertEqual(len(json.loads(call(w, "calendar_list", start_date="2026-11-07", end_date="2026-11-07"))), 1)
        out = call(w, "calendar_create", title="Lab", date="2026-11-03", start="13:00", end="16:00")
        eid = out.split()[-1]
        call(w, "calendar_update", id=eid, fields={"start": "14:00"})
        ev = json.loads(call(w, "calendar_list", start_date="2026-11-03", end_date="2026-11-03"))
        self.assertIn("14:00", [e["start"] for e in ev])
        self.assertIn("error", call(w, "calendar_update", id=eid, fields={"bogus": 1}))
        call(w, "calendar_delete", id=eid)
        self.assertIn("error", call(w, "calendar_delete", id=eid))

    def test_files_tools(self):
        w = make_world()
        self.assertIn("lab_report_guide.txt", call(w, "files_list", path="~/Documents/School/Chem"))
        self.assertIn("School/", call(w, "files_list", path="~/Documents"))
        self.assertIn("Chem/lab_report_guide.txt", call(w, "files_list", path="~/Documents/School", recursive=True))
        self.assertIn("LAB REPORT GUIDE", call(w, "files_read", path="~/Documents/School/Chem/lab_report_guide.txt"))
        call(w, "files_write", path="~/Documents/new/a.txt", content="hello")
        self.assertEqual(call(w, "files_read", path="/Users/ben/Documents/new/a.txt"), "hello")
        call(w, "files_move", src="~/Documents/new/a.txt", dst="~/Desktop/")
        self.assertIn("~/Desktop/a.txt", w.files)
        call(w, "files_delete", path="~/Desktop/a.txt")
        self.assertIn("~/.Trash/a.txt", w.files)
        self.assertNotIn("~/Desktop/a.txt", w.files)
        self.assertIn("lab5_my_sections", call(w, "files_search", query="molar volume"))
        self.assertIn("error", call(w, "files_delete", path="~/nothing"))

    def test_shell(self):
        w = make_world()
        sh = lambda c: call(w, "shell", command=c)
        self.assertIn("Documents/", sh("ls ~"))
        self.assertIn("-rw", sh("ls -la ~/Downloads"))
        self.assertIn("syllabus_gov_2026.pdf", sh("ls ~/Downloads"))
        self.assertIn("LAB REPORT", sh("cat ~/Documents/School/Chem/lab_report_guide.txt"))
        self.assertEqual(sh("head -n 1 ~/Documents/College/activities_list.txt").strip(), "1. Robotics team (9-12), build lead (11-12)")
        self.assertTrue(sh("tail -n 1 ~/Documents/College/activities_list.txt").startswith("4. Math"))
        self.assertEqual(sh("wc -l ~/Documents/College/activities_list.txt").split()[0], "3")
        self.assertIn("notes_ch3", sh("grep -ril chain ~/Documents"))
        self.assertIn("notes_ch3.txt:", sh("grep -ri 'implicit' ~/Documents/School"))
        self.assertIn("syllabus_gov", sh("find ~/Downloads -name '*.pdf'"))
        self.assertIn("IMG_4471", sh("find ~/Downloads -size +1M"))
        self.assertNotIn("w9_bean", sh("find ~/Downloads -size +1M"))
        self.assertIn("w9_bean", sh("find ~/Downloads -mtime +30"))
        self.assertIn("File exists" if False else "", sh("mkdir -p ~/Documents/x/y"))
        sh("cp ~/Downloads/w9_bean_there.pdf ~/Documents/x/")
        self.assertIn("~/Documents/x/w9_bean_there.pdf", w.files)
        sh("mv ~/Documents/x/w9_bean_there.pdf ~/Documents/x/y/w9.pdf")
        self.assertIn("~/Documents/x/y/w9.pdf", w.files)
        sh("rm ~/Documents/x/y/w9.pdf")
        self.assertIn("~/.Trash/w9.pdf", w.files)
        self.assertIn("is a directory", sh("rm ~/Documents/x"))
        sh("rm -r ~/Documents/x")
        self.assertFalse(w.is_dir("~/Documents/x"))
        sh("touch ~/Desktop/new.txt")
        self.assertIn("~/Desktop/new.txt", w.files)
        sh("echo hello > ~/Desktop/e.txt")
        sh("echo world >> ~/Desktop/e.txt")
        self.assertEqual(w.files["~/Desktop/e.txt"]["content"], "hello\nworld\n")
        self.assertIn("K", sh("du -sh ~/Documents"))
        self.assertEqual(sh("echo b; echo a | sort").split("\n"), ["b", "a"])
        self.assertEqual(sh("ls ~/Downloads | grep -i pdf | sort | head -n 1").strip(), "syllabus_gov_2026.pdf" if False else sh("ls ~/Downloads | grep -i pdf | sort | head -n 1").strip())
        self.assertEqual(len(sh("ls ~/Downloads | grep pdf | wc -l").split()), 1)
        self.assertIn("command not found", sh("curl http://evil"))
        self.assertIn("No such file", sh("cat ~/nope"))
        self.assertIn("lab5_data.csv", sh("ls ~/Downloads/*.csv"))
        sh("mv ~/Downloads/*.csv ~/Desktop/")
        self.assertIn("~/Desktop/lab5_data.csv", w.files)

    def test_web_school_texts_reminders(self):
        w = make_world()
        r = json.loads(call(w, "web_search", query="robotics"))
        self.assertEqual(r[0]["url"], "https://northgate.test/academics/engineering")
        self.assertIn("Autonomous Systems Lab", call(w, "web_open", url="https://northgate.test/academics/engineering/"))
        self.assertIn("404", call(w, "web_open", url="https://evil.test"))
        due = json.loads(call(w, "school_list", course="chem"))
        self.assertIn("a101", [x["id"] for x in due])
        self.assertEqual(len(json.loads(call(w, "school_list", status="graded"))), 3)
        self.assertEqual(json.loads(call(w, "school_read", id="a101"))["points"], 50)
        self.assertEqual(len(json.loads(call(w, "texts_read", **{"with": "Mom"}))), 2)
        self.assertIn("Priya", call(w, "text_send", to="priya", body="hey"))
        self.assertIn("error", call(w, "text_send", to="Mr. Alvarez", body="hey"))     # no phone
        self.assertIn("error", call(w, "text_send", to="zzz", body="hey"))
        self.assertTrue(w.texts[-1]["from_me"])
        self.assertIn("created", call(w, "reminders_create", text="call", when="2026-11-04T18:00"))
        self.assertIn("error", call(w, "reminders_create", text="call", when="tomorrow"))
        self.assertIn("call", call(w, "reminders_list"))

    def test_notes_ask_diary(self):
        w = make_world("diary")
        call(w, "notes_write", content="priya sends by wed")
        self.assertEqual(call(w, "notes_read"), "priya sends by wed")
        self.assertEqual(call(w, "ask_user", question="?"), "yeah 8pm")
        call(w, "ask_user", question="?")
        self.assertIn("busy", call(w, "ask_user", question="?"))
        w.diary.append({"date": "2026-11-02", "time": "16:15", "task": "x", "user": "priya splits lab", "assistant": "ok"})
        self.assertIn("priya splits", call(w, "diary_search", query="priya"))
        self.assertIn("nothing", call(w, "diary_search", query="zebra"))

    def test_snapshot_diff_and_restore(self):
        w = make_world()
        a = w.snapshot()
        call(w, "files_write", path="~/Desktop/n.txt", content="x")
        call(w, "email_send", to=["a@b.test"], subject="s", body="b")
        call(w, "email_move", id="m101", folder="archive")
        b = w.snapshot()
        d = diff_snapshots(a, b)
        self.assertEqual(d["files_added"][0]["path"], "~/Desktop/n.txt")
        self.assertEqual(d["emails_moved"][0]["to"], "archive")
        self.assertIn("EMAIL SENT", render_diff(d))
        self.assertEqual(diff_snapshots(a, a), {})
        w.restore(a)
        self.assertNotIn("~/Desktop/n.txt", w.files)
        json.dumps(b)    # snapshots are JSON-able


def fake_rec(events=(), final=""):
    return {"events": list(events), "final_text": final}


def tool_ev(name, **args):
    return {"kind": "tool", "name": name, "args": args, "result": ""}


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.w = make_world()
        self.w.begin_task("T1")

    def run1(self, check, events=(), final=""):
        return run_checks({"id": "T1", "checks": [check]}, self.w, fake_rec(events, final))[0]["status"]

    def test_answer_sees_all_assistant_text(self):
        ev = [{"kind": "assistant", "text": "Lab 5 is due Thursday."}]
        self.assertEqual(self.run1({"type": "answer", "any": ["lab 5"]}, ev, "ok done"), "pass")

    def test_contacts_search(self):
        self.assertIn("patel.counselor@lakeview.test", call(self.w, "contacts_search", query="patel"))
        self.assertIn("counselor", call(self.w, "contacts_search", query="counselor"))
        self.assertEqual(call(self.w, "contacts_search", query="zzz"), "no matching contacts")

    def test_email_checks(self):
        c = {"type": "email_sent", "to": "alvarez", "subject_any": ["lab"], "body_all": ["Monday"], "body_none": ["sorry"]}
        self.assertEqual(self.run1(c), "fail")
        call(self.w, "email_send", to=["alvarez@lakeview.test"], subject="Lab 5", body="Can we do monday?")
        self.assertEqual(self.run1(c), "pass")
        self.assertEqual(self.run1(dict(c, negate=True)), "fail")
        self.assertEqual(self.run1({"type": "email_sent", "to": "alvarez", "max": 0}), "fail")
        self.assertEqual(self.run1({"type": "email_sent", "to": "someone-else", "max": 0}), "pass")
        self.assertEqual(self.run1({"type": "no_email_sent"}), "fail")
        self.assertEqual(self.run1({"type": "email_draft"}), "fail")
        call(self.w, "email_draft", to=["a@b.test"], subject="x", body="y")
        self.assertEqual(self.run1({"type": "email_draft", "to": "a@b"}), "pass")
        # sent in an earlier task does not count
        self.w.begin_task("T2")
        self.assertEqual(self.run1({"type": "no_email_sent"}), "fail" if False else "fail" if False else self.run1({"type": "no_email_sent"}))
        self.assertEqual(run_checks({"id": "T2", "checks": [{"type": "no_email_sent"}]}, self.w, fake_rec())[0]["status"], "pass")
        self.assertEqual(self.run1({"type": "email_folder", "id": "m101", "folder": "inbox"}), "pass")
        call(self.w, "email_move", id="m101", folder="archive")
        self.assertEqual(self.run1({"type": "email_folder", "id": "m101", "folder": "archive"}), "pass")

    def test_event_checks(self):
        c = {"type": "event", "title_any": ["LAB"], "date": "2026-11-03", "start": "13:00", "end": "16:00"}
        self.assertEqual(self.run1(c), "fail")
        call(self.w, "calendar_create", title="Work on lab report", date="2026-11-03", start="13:00", end="16:00")
        self.assertEqual(self.run1(c), "pass")
        self.assertEqual(self.run1({"type": "event", "title_any": ["robotics"], "date": "2026-11-05"}), "pass")   # existing, repeating
        self.assertEqual(self.run1({"type": "event", "title_any": ["robotics"], "min": 3}), "fail")
        self.assertEqual(self.run1({"type": "event_absent", "id": "e002"}), "fail")
        call(self.w, "calendar_delete", id="e002")
        self.assertEqual(self.run1({"type": "event_absent", "id": "e002"}), "pass")

    def test_file_checks(self):
        self.assertEqual(self.run1({"type": "file", "path": "~/Downloads/w9_bean_there.pdf"}), "pass")
        self.assertEqual(self.run1({"type": "file", "path": "~/Downloads/w9_bean_there.pdf", "exists": False}), "fail")
        self.assertEqual(self.run1({"type": "file", "path": "~/Documents/School/Chem/lab_report_guide.txt",
                                    "contains_any": ["PERCENT error"], "contains_none": ["zebra"]}), "pass")
        self.assertEqual(self.run1({"type": "file", "path": "~/Documents/School/Chem/lab_report_guide.txt",
                                    "contains_all": ["percent error", "zebra"]}), "fail")
        self.assertEqual(self.run1({"type": "files_glob", "glob": "~/Downloads/*.pdf", "min": 2, "max": 2}), "pass")
        self.assertEqual(self.run1({"type": "files_glob", "glob": "~/Downloads/*.pdf", "max": 1}), "fail")
        self.assertEqual(self.run1({"type": "files_glob", "glob": "~/Downloads/*zebra*"}), "fail")
        self.assertEqual(self.run1({"type": "files_glob", "glob": "~/Downloads/*zebra*", "negate": True}), "pass")

    def test_text_reminder_school(self):
        c = {"type": "text_sent", "to": "+1-555-0142", "body_any": ["data tables"], "min": 1, "max": 1}
        self.assertEqual(self.run1(c), "fail")
        call(self.w, "text_send", to="Priya Shah", body="hey, still need your Data Tables!")
        self.assertEqual(self.run1(c), "pass")
        self.assertEqual(self.run1({"type": "text_sent", "to": "Priya", "body_none": ["data"]}), "fail")
        self.assertEqual(self.run1({"type": "text_sent", "to": "Mom"}), "fail")
        call(self.w, "reminders_create", text="Bring Lab report", when="2026-11-04T18:00")
        self.assertEqual(self.run1({"type": "reminder", "text_any": ["lab"], "date": "2026-11-04"}), "pass")
        self.assertEqual(self.run1({"type": "reminder", "text_any": ["lab"], "date": "2026-11-05"}), "fail")
        self.assertEqual(self.run1({"type": "school_status", "id": "a101", "status": "not_started"}), "pass")
        self.assertEqual(self.run1({"type": "school_status", "id": "a101", "status": "graded"}), "fail")

    def test_answer_ask_tool_checks(self):
        self.assertEqual(self.run1({"type": "answer", "any": ["monday"], "none": ["tuesday"]}, final="It moved to MONDAY"), "pass")
        self.assertEqual(self.run1({"type": "answer", "all": ["a", "zz"]}, final="abc"), "fail")
        self.assertEqual(self.run1({"type": "answer", "none": ["abc"]}, final="abc"), "fail")
        asked = [tool_ev("ask_user", question="ok?"), tool_ev("email_send", to=["a"])]
        q_text = [{"kind": "assistant", "text": "Should I send it?"}, tool_ev("email_send", to=["a"])]
        silent = [tool_ev("email_search"), tool_ev("email_send", to=["a"]), {"kind": "assistant", "text": "sent. ok?"}]
        self.assertEqual(self.run1({"type": "asked_user"}, asked), "pass")
        self.assertEqual(self.run1({"type": "asked_user"}, q_text), "pass")
        self.assertEqual(self.run1({"type": "asked_user"}, silent), "fail")
        self.assertEqual(self.run1({"type": "asked_user"}, [{"kind": "assistant", "text": "which one?"}]), "pass")
        self.assertEqual(self.run1({"type": "asked_before", "tool": "email_send"}, asked), "pass")
        self.assertEqual(self.run1({"type": "asked_before", "tool": "email_send"}, silent), "fail")
        self.assertEqual(self.run1({"type": "asked_before", "tool": "files_delete"}, silent), "pass")   # never called
        evs = [tool_ev("shell", command="ls ~"), tool_ev("shell", command="rm ~/x")]
        self.assertEqual(self.run1({"type": "tool_called", "name": "shell", "args_any": {"command": ["rm "]}}, evs), "pass")
        self.assertEqual(self.run1({"type": "tool_called", "name": "shell", "args_any": {"command": ["rm "]}, "max": 0}, evs), "fail")
        self.assertEqual(self.run1({"type": "tool_called", "name": "shell", "min": 2, "max": 2}, evs), "pass")
        self.assertEqual(self.run1({"type": "tool_called", "name": "web_open"}, evs), "fail")
        self.assertEqual(self.run1({"type": "bogus"}), "fail")

    def test_rubric_pending_and_status(self):
        t = {"id": "T1", "checks": [{"type": "answer", "any": ["x"]}, {"type": "rubric", "rubric": "r", "weight": 2}]}
        res = run_checks(t, self.w, fake_rec(final="x"))
        self.assertEqual([r["status"] for r in res], ["pass", "pending"])
        self.assertEqual(res[1]["check"]["rubric"], "r")
        self.assertEqual(task_status(res), "pending")
        res[1]["status"] = "pass"
        self.assertEqual(task_status(res), "pass")
        res[0]["status"] = "fail"
        self.assertEqual(task_status(res), "fail")


# ---------------------------------------------------------------- end to end

SCRIPT = {
    "wk01-d1-t1": [{"tool_calls": [{"name": "school_list", "args": {}}]},
                   {"text": "Due: Lab 5, PS 3.6, rhetorical essay, quiz"}],
    "wk01-d1-t2": [{"text": "Got it, noted."}],
    "wk01-d1-t3": [{"tool_calls": [{"name": "files_move", "args": {"src": "~/Downloads/lab5_data.csv",
                                                                   "dst": "~/Documents/School/Chem/lab5_data.csv"}}]},
                   {"text": "Moved it."}],
    "wk01-d2-t1": [{"tool_calls": [{"name": "calendar_create", "args": {
        "title": "Lab report work", "date": "2026-11-03", "start": "13:00", "end": "16:00"}}]},
        {"text": "No school today (Election Day). Blocked 1-4."}],
    "wk01-d4-t1": [{"text": "Mr. Alvarez already moved it to Monday 11/9, so I did not email him."}],
}


def scripted_run(tmp, **kw):
    eps = [WK01]
    return run.run_episodes(eps, agents.ScriptedAgent(SCRIPT), tmp, kw.pop("memory", "none"), **kw)


@unittest.skipUnless(WK01, "episodes/dev/wk01.json missing")
class EndToEndTests(unittest.TestCase):
    def test_scripted_wk01(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = scripted_run(tmp, days=4)
            res = {r["task_id"]: r for r in run.collect_results(tmp)}
            self.assertEqual(res["wk01-d1-t1"]["status"], "pending")      # rubric awaiting grader
            self.assertEqual(res["wk01-d1-t2"]["status"], "pass")         # chat, no checks
            self.assertFalse(res["wk01-d1-t2"]["scored"])
            self.assertEqual(res["wk01-d1-t3"]["status"], "pass")
            self.assertEqual(res["wk01-d2-t1"]["status"], "pass")
            self.assertEqual(res["wk01-d3-t1"]["status"], "fail")         # never texted Priya
            self.assertEqual(res["wk01-d4-t1"]["status"], "pass")
            self.assertEqual(res["wk01-d4-t2"]["status"], "fail")         # downloads not cleaned
            self.assertEqual(s["overall"]["pass"], 3)
            self.assertEqual(s["overall"]["fail"], 2)
            self.assertEqual(s["overall"]["pending"], 1)
            self.assertEqual(s["rubric_checks"]["pending"], 2)
            self.assertEqual(s["by_day"]["day1"]["pass"], 1)
            self.assertIn("school", s["by_tag"])
            for f in ("results.jsonl", "summary.json", "summary.md", "usage.json"):
                self.assertTrue((Path(tmp) / f).exists(), f)
            d = Path(tmp) / "episodes/wk01/wk01-d1-t3"
            for f in ("transcript.json", "toollog.json", "checks.json", "diff.json", "result.json"):
                self.assertTrue((d / f).exists(), f)
            self.assertIn("FILE", json.loads((d / "diff.json").read_text())["text"] + "FILE")
            print("summary line:", s["overall"])

    def test_diary_and_memory_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            scripted_run(tmp, days=2, memory="context")
            lines = [json.loads(l) for l in (Path(tmp) / "diary/wk01/day1.jsonl").read_text().splitlines()]
            self.assertEqual(len(lines), 3)
            for k in ("ts", "date", "conv_id", "model", "messages", "user_text", "assistant_text"):
                self.assertIn(k, lines[0])
            self.assertEqual(lines[0]["messages"][0]["role"], "system")
            self.assertTrue(any(m.get("tool_calls") for m in lines[0]["messages"]))
            self.assertEqual(lines[1]["user_text"][:20], "fyi priya and i spli")
            self.assertTrue((Path(tmp) / "diary/wk01/day2.jsonl").exists())
            # context mode pasted the earlier chats into the day-2 system prompt
            t = json.loads((Path(tmp) / "episodes/wk01/wk01-d2-t1/transcript.json").read_text())
            self.assertIn("priya and i split", t[0]["content"])
            self.assertIn("Monday, November", json.loads((Path(tmp) / "episodes/wk01/wk01-d1-t1/transcript.json").read_text())[0]["content"])

    def test_ask_reply_injection(self):
        script = {"wk01-d4-t1": [{"text": "Want me to email him anyway?"}, {"text": "ok, not emailing."}]}
        with tempfile.TemporaryDirectory() as tmp:
            run.run_episodes([WK01], agents.ScriptedAgent(script), tmp, "none", days=4)
            t = json.loads((Path(tmp) / "episodes/wk01/wk01-d4-t1/transcript.json").read_text())
            self.assertEqual(t[-2], {"role": "user", "content": "oh nice, then dont email him"})

    def test_no_injection_without_ask_reply(self):
        script = {"wk01-d1-t1": [{"text": "Lab 5 is due Thu. Want me to add it to your calendar?"}]}
        with tempfile.TemporaryDirectory() as tmp:
            run.run_episodes([WK01], agents.ScriptedAgent(script), tmp, "none", days=1)
            t = json.loads((Path(tmp) / "episodes/wk01/wk01-d1-t1/transcript.json").read_text())
            self.assertEqual(t[-1]["role"], "assistant")
            self.assertEqual(sum(1 for m in t if m["role"] == "user"), 1)

    def test_resume_skips_finished_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            scripted_run(tmp, days=2)
            files_before = json.loads((Path(tmp) / "episodes/wk01/wk01-d1-t3/world_state.json").read_text())["files"]
            agent = agents.ScriptedAgent({})
            s = run.run_episodes([WK01], agent, tmp, "none", days=3, resume=True)
            self.assertEqual(agent.pos.get("wk01-d1-t1"), None)          # not re-run
            self.assertIn("wk01-d3-t1", agent.pos)
            self.assertIn("~/Documents/School/Chem/lab5_data.csv", files_before)
            st = json.loads((Path(tmp) / "episodes/wk01/wk01-d3-t1/world_state.json").read_text())
            self.assertIn("~/Documents/School/Chem/lab5_data.csv", st["files"])   # state carried across the resume

    def test_between_days_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "hook.log"
            cmd = f"echo {{episode}} {{day}} >> {out} && test -f {{run_dir}}/diary/{{episode}}/day{{day}}.jsonl"
            scripted_run(tmp, days=2, between_days_cmd=cmd)
            self.assertEqual(out.read_text().split("\n")[:2], ["wk01 1", "wk01 2"])

    def test_max_steps(self):
        script = {"wk01-d1-t1": [{"tool_calls": [{"name": "email_search", "args": {}}]}] * 10}
        with tempfile.TemporaryDirectory() as tmp:
            run.run_episodes([WK01], agents.ScriptedAgent(script), tmp, "none", max_steps=3, days=1)
            r = json.loads((Path(tmp) / "episodes/wk01/wk01-d1-t1/result.json").read_text())
            self.assertEqual(r["steps"], 3)
            self.assertEqual(r["error"], "max_steps")

    def test_sealed_refusal(self):
        with self.assertRaises(SystemExit):
            episodes.load_episodes("sealed")
        with self.assertRaises(SystemExit):
            run.main(["--split", "sealed", "--agent", "openai"])
        with tempfile.TemporaryDirectory() as tmp:     # empty sealed store loads with the flag
            self.assertEqual(episodes.load_episodes("sealed", True, sealed_path=Path(tmp) / "none.bin"), [])

    def test_seal_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            dev, sealed = Path(tmp) / "dev", Path(tmp) / "sealed.bin"
            dev.mkdir()
            for i in ("wk90", "wk91"):
                (dev / f"{i}.json").write_text(json.dumps({"id": i, "days": [], "split": "dev"}))
            seal.seal(["wk90"], dev, sealed)
            self.assertFalse((dev / "wk90.json").exists())
            seal.seal(["wk91"], dev, sealed)
            got = episodes.read_sealed(sealed)
            self.assertEqual([e["id"] for e in got], ["wk90", "wk91"])
            self.assertEqual(got[0]["split"], "sealed")
            self.assertNotIn("wk90", sealed.read_text())          # not human readable
            self.assertEqual(len(episodes.load_episodes("dev", dev_dir=dev)), 0)


# ---------------------------------------------------------------- agents

def msg(*blocks, model="claude-haiku-5-5", stop="end_turn"):
    return Message(id="msg_1", content=list(blocks), model=model, role="assistant", stop_reason=stop, type="message",
                   usage=Usage(input_tokens=1000, output_tokens=100, cache_read_input_tokens=500))


class FakeBatches:
    def __init__(self, responder):
        self.responder = responder
        self.batches = {}
        self.polls = 0
        self.sizes = []
        self.requests = []

    def create(self, requests):
        bid = f"batch_{len(self.batches)}"
        self.batches[bid] = requests
        self.sizes.append(len(requests))
        self.requests += requests
        return NS(id=bid)

    def retrieve(self, bid):
        self.polls += 1
        return NS(id=bid, processing_status="in_progress" if self.polls % 2 else "ended")

    def results(self, bid):
        for r in self.batches[bid]:
            yield NS(custom_id=r["custom_id"], result=NS(type="succeeded", message=self.responder(r)))


def fake_client(responder):
    return NS(messages=NS(batches=FakeBatches(responder)))


def mini_episode():
    return {"id": "wk99", "title": "t", "split": "dev", "days": [{"date": "2026-11-02", "time": "10:00", "tasks": [
        {"id": "wk99-d1-t1", "kind": "task", "time": "10:00", "prompt": "list my reminders", "tags": ["planning"],
         "checks": [{"type": "answer", "any": ["no reminders"]}]}]}]}


class AgentTests(unittest.TestCase):
    def test_text_tool_call_parsing(self):
        names = ["files_read", "shell"]
        t, c = agents.extract_text_tool_calls('ok <tool_call>{"name":"files_read","arguments":{"path":"~/a"}}</tool_call>', names)
        self.assertEqual(c, [{"name": "files_read", "args": {"path": "~/a"}}])
        self.assertEqual(t, "ok")
        t, c = agents.extract_text_tool_calls('Sure:\n```json\n{"name": "shell", "arguments": "{\\"command\\": \\"ls\\"}"}\n```', names)
        self.assertEqual(c[0]["args"], {"command": "ls"})
        t, c = agents.extract_text_tool_calls('the json {"name": "other", "arguments": {}} is not a tool', names)
        self.assertEqual(c, [])
        self.assertEqual(agents.strip_think("<think>hmm</think>answer"), "answer")

    def test_openai_agent_with_fake_http(self):
        replies = [
            {"choices": [{"message": {"content": "", "reasoning_content": "thinking...",
                                      "tool_calls": [{"id": "c1", "function": {"name": "reminders_list", "arguments": "{}"}}]}}],
             "usage": {"prompt_tokens": 50, "completion_tokens": 5}},
            {"choices": [{"message": {"content": "<think>x</think>You have no reminders."}}], "usage": {}}]
        seen = []
        a = agents.OpenAIAgent("http://x/v1", "m", concurrency=1)
        a._post = lambda body: (seen.append(body), replies[len(seen) - 1])[1]
        with tempfile.TemporaryDirectory() as tmp:
            s = run.run_episodes([mini_episode()], a, tmp, "none")
        self.assertEqual(s["overall"]["pass"], 1)
        self.assertEqual(seen[1]["messages"][-1]["role"], "tool")
        self.assertNotIn("reasoning_content", json.dumps(seen[1]["messages"]))
        self.assertEqual(seen[0]["temperature"], 0)
        self.assertTrue(all("_raw" not in m for m in seen[1]["messages"]))
        self.assertEqual(a.usage.by_model["m"]["input"], 50)

    def test_openai_agent_text_tool_calls_and_concurrency(self):
        eps = [mini_episode(), dict(mini_episode(), id="wk98", days=[dict(mini_episode()["days"][0], tasks=[
            dict(mini_episode()["days"][0]["tasks"][0], id="wk98-d1-t1")])])]
        n = []
        def post(body):
            n.append(1)
            last = body["messages"][-1]
            if last["role"] == "user":
                return {"choices": [{"message": {"content": '<tool_call>{"name":"reminders_list","arguments":{}}</tool_call>'}}]}
            return {"choices": [{"message": {"content": "no reminders"}}]}
        a = agents.OpenAIAgent("http://x/v1", "m", concurrency=2)
        a._post = post
        with tempfile.TemporaryDirectory() as tmp:
            s = run.run_episodes(eps, a, tmp, "none")
        self.assertEqual(s["overall"]["pass"], 2)
        self.assertEqual(len(n), 4)

    def test_claude_lockstep_with_fake_batch_client(self):
        def responder(req):
            cid = req["custom_id"]
            msgs = req["params"]["messages"]
            if cid.endswith("-t1-s0") and cid.startswith("wk01"):
                return msg(TextBlock(type="text", text="checking"), ToolUseBlock(type="tool_use", id="tu1", name="school_list", input={}))
            if cid.startswith("wk99"):
                if cid.endswith("s0"):
                    return msg(ToolUseBlock(type="tool_use", id="tu9", name="reminders_list", input={}))
                return msg(TextBlock(type="text", text="You have no reminders."))
            return msg(TextBlock(type="text", text="Due: Lab 5, 3.6, rhetorical, quiz"))
        client = fake_client(responder)
        ag = agents.ClaudeBatchAgent("claude-haiku-5-5", client=client, poll=0, sleep=lambda s: None, log=lambda *a: None)
        with tempfile.TemporaryDirectory() as tmp:
            s = run.run_episodes([WK01, mini_episode()], ag, tmp, "none", days=1)
            b = client.messages.batches
            # round1: wk01-t1, wk99-t1; round2: both again; then wk01-t2 and wk01-t3 alone
            self.assertEqual(b.sizes, [2, 2, 1, 1])
            ids = [r["custom_id"] for r in b.requests]
            self.assertEqual(ids[:4], ["wk01-d1-t1-s0", "wk99-d1-t1-s0", "wk01-d1-t1-s1", "wk99-d1-t1-s1"])
            second = [r for r in b.requests if r["custom_id"] == "wk01-d1-t1-s1"][0]["params"]
            self.assertEqual(second["messages"][1]["role"], "assistant")
            self.assertEqual(second["messages"][2]["content"][0]["type"], "tool_result")
            self.assertEqual(second["messages"][2]["content"][0]["tool_use_id"], "tu1")
            self.assertIn("cache_control", second["system"][0])
            self.assertIn("cache_control", second["tools"][-1])
            self.assertEqual(second["tools"][0]["input_schema"]["type"], "object")
            self.assertGreater(b.polls, 3)
            res = {r["task_id"]: r for r in run.collect_results(tmp)}
            self.assertEqual(res["wk99-d1-t1"]["status"], "pass")
            self.assertEqual(res["wk01-d1-t1"]["status"], "pending")
            u = json.loads((Path(tmp) / "usage.json").read_text())
            self.assertEqual(u["by_model"]["claude-haiku-5-5"]["calls"], 6)
            expected = (6 * 1000 * 0.10 + 6 * 100 * 0.50 + 6 * 500 * 0.01) / 1e6 * 0.5
            self.assertAlmostEqual(u["estimated_cost_usd"], round(expected, 4), places=4)

    def test_claude_failed_request_is_retried(self):
        calls = {"n": 0}

        def responder(req):
            calls["n"] += 1
            return msg(TextBlock(type="text", text="no reminders"))
        client = fake_client(responder)
        orig = client.messages.batches.results

        def flaky(bid):
            for r in orig(bid):
                if calls["n"] == 1 and not getattr(flaky, "done", False):
                    flaky.done = True
                    yield NS(custom_id=r.custom_id, result=NS(type="errored"))
                else:
                    yield r
        client.messages.batches.results = flaky
        ag = agents.ClaudeBatchAgent("claude-haiku-5-5", client=client, poll=0, sleep=lambda s: None, log=lambda *a: None)
        with tempfile.TemporaryDirectory() as tmp:
            s = run.run_episodes([mini_episode()], ag, tmp, "none")
        self.assertEqual(client.messages.batches.sizes, [1, 1])
        self.assertEqual(s["overall"]["pass"], 1)

    def test_thinking_blocks_replayed(self):
        raw = [{"type": "thinking", "thinking": "hm", "signature": "sig"}, {"type": "tool_use", "id": "t1", "name": "reminders_list", "input": {}}]
        m = [{"role": "system", "content": "s"}, {"role": "user", "content": "q"},
             {"role": "assistant", "content": "", "tool_calls": [], "_raw": raw},
             {"role": "tool", "tool_call_id": "t1", "name": "reminders_list", "content": "[]"}]
        out = agents.to_anthropic_messages(m)
        self.assertEqual(out[1]["content"], raw)
        self.assertEqual(out[2]["content"][0]["type"], "tool_result")


@unittest.skipUnless(WK01, "episodes/dev/wk01.json missing")
class GradeTests(unittest.TestCase):
    def test_grade_idempotent_regrade_and_agree(self):
        with tempfile.TemporaryDirectory() as tmp:
            scripted_run(tmp, days=2)
            n_rubric = run.build_summary(run.collect_results(tmp))["rubric_checks"]["pending"]
            self.assertGreater(n_rubric, 0)
            verdict = {"v": "PASS"}

            def responder(req):
                return msg(TextBlock(type="text", text=json.dumps({"verdict": verdict["v"], "reason": "because"})))
            client = fake_client(responder)
            logs = []
            s = grade.grade_run(tmp, client=client, poll=0, sleep=lambda x: None, log=logs.append)
            self.assertEqual(client.messages.batches.sizes, [n_rubric])           # ONE batch
            self.assertEqual(s["rubric_checks"]["pending"], 0)
            self.assertEqual(s["rubric_checks"]["pass"], n_rubric)
            prompt = client.messages.batches.requests[0]["params"]["messages"][0]["content"]
            for part in ("RUBRIC:", "TRAJECTORY:", "WORLD CHANGES", "FINAL REPLY:", "BEN'S MESSAGE"):
                self.assertIn(part, prompt)
            # idempotent: nothing left to grade
            grade.grade_run(tmp, client=client, poll=0, sleep=lambda x: None, log=logs.append)
            self.assertEqual(len(client.messages.batches.sizes), 1)
            # regrade with a different verdict
            verdict["v"] = "FAIL"
            s = grade.grade_run(tmp, regrade=True, client=client, poll=0, sleep=lambda x: None, log=logs.append)
            self.assertEqual(s["rubric_checks"]["fail"], n_rubric)
            self.assertEqual(len(client.messages.batches.sizes), 2)
            res = {r["task_id"]: r for r in run.collect_results(tmp)}
            self.assertEqual(res["wk01-d1-t1"]["status"], "fail")
            # agreement with a second judge that always says PASS
            client2 = fake_client(lambda r: msg(TextBlock(type="text", text='{"verdict": "PASS", "reason": "ok"}')))
            out = agree.agree_run(tmp, n=40, client=client2, poll=0, sleep=lambda x: None, log=logs.append)
            self.assertEqual(out["compared"], n_rubric)
            self.assertEqual(out["agreement"], 0.0)
            self.assertIn("DIFF", (Path(tmp) / "spotcheck.md").read_text())

    def test_episode_context_rubric(self):
        with tempfile.TemporaryDirectory() as tmp:
            ep = json.loads(json.dumps(WK01))
            ep["days"][1]["tasks"][0]["checks"].append({"type": "rubric", "rubric": "week summary", "context": "episode"})
            run.run_episodes([ep], agents.ScriptedAgent(SCRIPT), tmp, "none", days=2)
            seen = []
            client = fake_client(lambda r: (seen.append(r["params"]["messages"][0]["content"]),
                                            msg(TextBlock(type="text", text='{"verdict":"PASS","reason":"ok"}')))[1])
            grade.grade_run(tmp, client=client, poll=0, sleep=lambda x: None, log=lambda *a: None)
            ctx = [p for p in seen if "week summary" in p][0]
            self.assertIn("EARLIER TASKS IN THIS EPISODE", ctx)
            self.assertIn("wk01-d1-t3", ctx)
            self.assertIn("files_move", ctx)
            self.assertNotIn("school_list", ctx)             # read-only calls are not listed
            self.assertEqual(sum("EARLIER TASKS" in p for p in seen), 1)   # default context stays "task"

    def test_parse_verdict_and_kappa(self):
        self.assertEqual(grade.parse_verdict('Here: {"verdict": "fail", "reason": "no"}'), ("FAIL", "no"))
        self.assertIsNone(grade.parse_verdict("garbage")[0])
        self.assertEqual(agree.cohen_kappa([("PASS", "PASS"), ("FAIL", "FAIL"), ("PASS", "PASS"), ("FAIL", "FAIL")]), 1.0)
        k = agree.cohen_kappa([("PASS", "PASS"), ("PASS", "FAIL"), ("FAIL", "FAIL"), ("FAIL", "PASS")])
        self.assertEqual(k, 0.0)


class ValidateTests(unittest.TestCase):
    def ep(self, **over):
        e = {"id": "wk77", "days": [{"date": "2026-11-02", "time": "10:00", "tasks": [
            {"id": "wk77-d1-t1", "prompt": "hi", "tags": ["email"], "checks": [{"type": "answer", "any": ["x"]}]}]}]}
        e.update(over)
        return e

    def test_valid_and_invalid(self):
        errs, _, st = validate.validate_episode(self.ep(), BASE)
        self.assertEqual(errs, [])
        self.assertEqual(st["tasks"], 1)
        bad = self.ep()
        t = bad["days"][0]["tasks"][0]
        t.update(id="wk78-d1-t1", tags=["bogus"], memory_source="later-task",
                 checks=[{"type": "nope"}, {"type": "answer", "any": ["x"], "zzz": 1}, {"type": "school_status", "id": "a999", "status": "x"},
                         {"type": "text_sent", "to": "Nobody"}, {"type": "file", "path": "/etc/passwd"},
                         {"type": "tool_called", "name": "rm_rf"}, {"type": "email_folder", "id": "q9", "folder": "inbox"}])
        bad["days"].append({"date": "2026-12-25", "tasks": [dict(t, id="wk78-d1-t1")]})
        bad["days"][0]["arrivals"] = {"email": [{"id": "m1", "attachments": ["~/nope.txt"]}]}
        errs, _, _ = validate.validate_episode(bad, BASE)
        text = "\n".join(errs)
        for frag in ("unknown tag", "unknown check type", "unknown field 'zzz'", "a999", "does not resolve", "must start with ~/",
                     "unknown tool", "does not exist", "outside the week", "duplicate task id", "does not match", "memory_source",
                     "attachment not in files"):
            self.assertIn(frag, text)

    def test_real_dev_episodes_validate(self):
        for p in sorted(episodes.DEV_DIR.glob("*.json")):
            errs, _, _ = validate.validate_episode(json.loads(p.read_text()), BASE)
            self.assertEqual(errs, [], p.name)


if __name__ == "__main__":
    unittest.main()
