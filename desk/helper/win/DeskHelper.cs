// deskhelper.exe: screen-control CLI for Premonition on Windows. Same commands, arguments and JSON output as the Mac deskhelper
// (deskhelper.swift) and as the old deskhelper.ps1 (removed: Microsoft Defender flagged the script as a hack tool).
// Compiled against .NET Framework 4.8, which ships with Windows 10/11. Build: helper/win/build.sh
//
//   deskhelper check                         {"accessibility":true,"screenRecording":true}   (Windows needs no permission for any of this)
//   deskhelper ask-permissions               same
//   deskhelper look [--app NAME] [--max N]   {"app","pid","windows":[{"title","frame"}],"elements":[{"id","role","title","value","frame":[x,y,w,h]}]}
//                                            and saves id -> element to %LOCALAPPDATA%\premonition-desk\last_look.json
//   deskhelper press ID                      focus (text fields) or click the element with that id from the last look
//   deskhelper click X Y [--double] [--right]
//   deskhelper type TEXT                     Unicode keystrokes (SendInput)
//   deskhelper key COMBO                     ctrl/shift/alt/win + key name or letter; cmd -> ctrl and option -> alt
//   deskhelper scroll DY                     wheel lines, negative = down
//   deskhelper open-app NAME                 focus a running app, else start it (Start menu shortcut, Start-menu app id, or the name itself)
//   deskhelper screenshot PATH [--max 1280]  JPEG of the primary display, scaled
//   deskhelper --help                        this list
// Errors: {"error": "..."} and exit code 1. Password fields are reported with role SecureEdit and their value is never read.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace Premonition
{
    // ---- JSON out (tiny, no dependencies) -----------------------------------------------------------------
    static class J
    {
        public static string Ser(object o)
        {
            StringBuilder sb = new StringBuilder();
            Write(sb, o);
            return sb.ToString();
        }
        static void Write(StringBuilder sb, object o)
        {
            if (o == null) { sb.Append("null"); return; }
            if (o is string) { Str(sb, (string)o); return; }
            if (o is bool) { sb.Append((bool)o ? "true" : "false"); return; }
            if (o is int || o is long || o is uint) { sb.Append(Convert.ToString(o, CultureInfo.InvariantCulture)); return; }
            if (o is double) { sb.Append(((double)o).ToString("R", CultureInfo.InvariantCulture)); return; }
            IDictionary d = o as IDictionary;
            if (d != null)
            {
                sb.Append('{');
                bool first = true;
                foreach (DictionaryEntry e in d)
                {
                    if (!first) sb.Append(',');
                    first = false;
                    Str(sb, Convert.ToString(e.Key));
                    sb.Append(':');
                    Write(sb, e.Value);
                }
                sb.Append('}');
                return;
            }
            IEnumerable en = o as IEnumerable;
            if (en != null)
            {
                sb.Append('[');
                bool first = true;
                foreach (object x in en)
                {
                    if (!first) sb.Append(',');
                    first = false;
                    Write(sb, x);
                }
                sb.Append(']');
                return;
            }
            Str(sb, Convert.ToString(o, CultureInfo.InvariantCulture));
        }
        static void Str(StringBuilder sb, string s)
        {
            sb.Append('"');
            foreach (char c in s)
            {
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4"));
                        else sb.Append(c);
                        break;
                }
            }
            sb.Append('"');
        }
    }

    class ExitException : Exception
    {
        public int Code;
        public ExitException(int code) { Code = code; }
    }

    // ---- user32 ---------------------------------------------------------------------------------------------
    static class Native
    {
        [StructLayout(LayoutKind.Sequential)] public struct MOUSEINPUT { public int dx; public int dy; public uint mouseData; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
        [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
        [StructLayout(LayoutKind.Explicit)] public struct INPUTUNION { [FieldOffset(0)] public MOUSEINPUT mi; [FieldOffset(0)] public KEYBDINPUT ki; }
        [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public INPUTUNION u; }

        [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
        [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
        [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
        [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
        [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
        [DllImport("user32.dll")] public static extern IntPtr GetWindow(IntPtr h, uint cmd);
        [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
        [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
        [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
        [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, int data, UIntPtr extra);
        [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
        [DllImport("user32.dll")] public static extern uint SendInput(uint n, INPUT[] inputs, int size);
        [DllImport("user32.dll")] public static extern short VkKeyScan(char c);

        public static void Key(ushort vk, uint flags)
        {
            INPUT[] a = new INPUT[1];
            a[0].type = 1; a[0].u.ki.wVk = vk; a[0].u.ki.wScan = 0; a[0].u.ki.dwFlags = flags; a[0].u.ki.time = 0; a[0].u.ki.dwExtraInfo = IntPtr.Zero;
            SendInput(1, a, Marshal.SizeOf(typeof(INPUT)));
        }
        public static void Uni(char c)
        {
            INPUT[] a = new INPUT[2];
            a[0].type = 1; a[0].u.ki.wVk = 0; a[0].u.ki.wScan = (ushort)c; a[0].u.ki.dwFlags = 0x4;
            a[1].type = 1; a[1].u.ki.wVk = 0; a[1].u.ki.wScan = (ushort)c; a[1].u.ki.dwFlags = 0x4 | 0x2;
            SendInput(2, a, Marshal.SizeOf(typeof(INPUT)));
        }
        public static void Activate(IntPtr h)
        {
            if (IsIconic(h)) ShowWindow(h, 9);
            keybd_event(0x12, 0, 0, UIntPtr.Zero); keybd_event(0x12, 0, 2, UIntPtr.Zero); // a bare Alt tap lets SetForegroundWindow through
            SetForegroundWindow(h);
        }
        public static int WindowPid(IntPtr h) { uint p; GetWindowThreadProcessId(h, out p); return (int)p; }
    }

    static class Program
    {
        const string Usage = "usage: deskhelper check|ask-permissions|look [--app NAME] [--max N]|press ID|click X Y [--double] [--right]|type TEXT|key COMBO|scroll DY|open-app NAME|screenshot PATH [--max 1280]";

        static string CacheDir { get { return Path.Combine(Environment.GetEnvironmentVariable("LOCALAPPDATA") ?? Path.GetTempPath(), "premonition-desk"); } }
        static string CacheFile { get { return Path.Combine(CacheDir, "last_look.json"); } }

        static Stream stdout;
        static void Emit(object o, int code)
        {
            byte[] b = new UTF8Encoding(false).GetBytes(J.Ser(o) + "\n");
            if (stdout == null) stdout = Console.OpenStandardOutput();
            stdout.Write(b, 0, b.Length);
            stdout.Flush();
            throw new ExitException(code);
        }
        static void Emit(object o) { Emit(o, 0); }
        static void Fail(string msg)
        {
            Dictionary<string, object> d = new Dictionary<string, object>();
            d["error"] = msg;
            Emit(d, 1);
        }
        static Dictionary<string, object> D(params object[] kv)
        {
            Dictionary<string, object> d = new Dictionary<string, object>();
            for (int i = 0; i + 1 < kv.Length; i += 2) d[(string)kv[i]] = kv[i + 1];
            return d;
        }

        [STAThread]
        static int Main(string[] argv)
        {
            try { Native.SetProcessDPIAware(); } catch (Exception) { } // real pixels everywhere: UIA rectangles, clicks and screenshots agree
            try
            {
                Run(argv);
                return 0;
            }
            catch (ExitException e) { return e.Code; }
            catch (Exception e)
            {
                try { Fail(e.Message); } catch (ExitException x) { return x.Code; }
                return 1;
            }
        }

        // ---- flags -----------------------------------------------------------------------------------------
        static bool TakeFlag(List<string> a, string name) { int i = a.IndexOf(name); if (i < 0) return false; a.RemoveAt(i); return true; }
        static string TakeValue(List<string> a, string name)
        {
            int i = a.IndexOf(name);
            if (i < 0) return null;
            if (i + 1 >= a.Count) Fail(name + " needs a value");
            string v = a[i + 1];
            a.RemoveAt(i + 1); a.RemoveAt(i);
            return v;
        }
        static int TakePosInt(List<string> a, string name, int dflt)
        {
            string v = TakeValue(a, name);
            if (v == null) return dflt;
            int n;
            if (!int.TryParse(v, NumberStyles.Integer, CultureInfo.InvariantCulture, out n) || n <= 0) Fail(name + " needs a positive number");
            return n;
        }

        static void Run(string[] argv)
        {
            if (argv.Length < 1) Fail(Usage);
            string command = argv[0];
            List<string> rest = new List<string>();
            for (int i = 1; i < argv.Length; i++) rest.Add(argv[i]);
            switch (command)
            {
                case "--help": case "-h": case "help": case "/?":
                    {
                        byte[] b = new UTF8Encoding(false).GetBytes(Usage + "\n");
                        Stream o = Console.OpenStandardOutput(); o.Write(b, 0, b.Length); o.Flush();
                        return;
                    }
                case "check":
                case "ask-permissions":
                    Emit(D("accessibility", true, "screenRecording", true)); break;
                case "look":
                    {
                        string app = TakeValue(rest, "--app");
                        int max = TakePosInt(rest, "--max", 150);
                        DoLook(app, max);
                        break;
                    }
                case "press":
                    {
                        int n;
                        if (rest.Count < 1 || !int.TryParse(rest[0], NumberStyles.Integer, CultureInfo.InvariantCulture, out n)) Fail("usage: press ID");
                        n = int.Parse(rest[0], CultureInfo.InvariantCulture);
                        DoPress(n);
                        break;
                    }
                case "click":
                    {
                        bool right = TakeFlag(rest, "--right");
                        bool dbl = TakeFlag(rest, "--double");
                        double x, y;
                        if (rest.Count < 2 || !double.TryParse(rest[0], NumberStyles.Float, CultureInfo.InvariantCulture, out x) || !double.TryParse(rest[1], NumberStyles.Float, CultureInfo.InvariantCulture, out y)) { Fail("usage: click X Y [--double] [--right]"); return; }
                        Input.Click((int)Math.Round(x), (int)Math.Round(y), right, dbl);
                        Emit(D("ok", true));
                        break;
                    }
                case "type":
                    if (rest.Count < 1) Fail("usage: type TEXT");
                    Input.Type(string.Join(" ", rest.ToArray()));
                    break;
                case "key":
                    if (rest.Count < 1) Fail("usage: key COMBO");
                    Input.KeyCombo(string.Join("", rest.ToArray()));
                    break;
                case "scroll":
                    {
                        double dy;
                        if (rest.Count < 1 || !double.TryParse(rest[0], NumberStyles.Float, CultureInfo.InvariantCulture, out dy)) { Fail("usage: scroll DY"); return; }
                        Native.mouse_event(0x800, 0, 0, (int)(Math.Round(dy) * 120), UIntPtr.Zero);
                        Emit(D("ok", true));
                        break;
                    }
                case "open-app":
                    if (rest.Count < 1) Fail("usage: open-app NAME");
                    Apps.Open(string.Join(" ", rest.ToArray()));
                    break;
                case "screenshot":
                    {
                        int max = TakePosInt(rest, "--max", 1280);
                        if (rest.Count < 1) Fail("usage: screenshot PATH [--max 1280]");
                        DoShot(rest[0], max);
                        break;
                    }
                default:
                    Fail("unknown command: " + command);
                    break;
            }
        }

        // UI Automation lives behind these two methods so that --help, input and the other commands never load UIAutomationClient
        [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)] static void DoLook(string app, int max) { Ui.Look(app, max); }
        [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)] static void DoPress(int id) { Ui.Press(id); }

        [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)] static void DoShot(string path, int max) { Shot.Take(path, max); }

        // shared by the other classes
        public static void Out(object o) { Emit(o, 0); }
        public static void Die(string m) { Fail(m); }
        public static string Cache { get { return CacheFile; } }
        public static string CacheFolder { get { return CacheDir; } }
    }

    // ---- processes and windows --------------------------------------------------------------------------------
    static class Apps
    {
        public static string Label(int pid, IntPtr hwnd)
        {
            string name = "", desc = "";
            try
            {
                Process p = Process.GetProcessById(pid);
                name = p.ProcessName;
                try { desc = p.MainModule.FileVersionInfo.FileDescription ?? ""; } catch (Exception) { desc = ""; }
            }
            catch (Exception) { }
            if (name == "ApplicationFrameHost")
            {
                foreach (Process w in Process.GetProcesses())
                {
                    try { if (w.MainWindowHandle == hwnd && w.MainWindowTitle.Length > 0) return w.MainWindowTitle; } catch (Exception) { }
                }
            }
            return desc.Length > 0 ? desc : name;
        }

        static string ProcName(int pid) { try { return Process.GetProcessById(pid).ProcessName; } catch (Exception) { return ""; } }

        // The window to look at: the foreground window, but not Premonition's own (Ben is usually typing in it): the next visible window down.
        public static IntPtr FrontWindow()
        {
            IntPtr h = Native.GetForegroundWindow();
            for (int guard = 0; h != IntPtr.Zero && guard < 60; guard++)
            {
                string n = ProcName(Native.WindowPid(h));
                bool own = string.Equals(n, "Premonition", StringComparison.OrdinalIgnoreCase) || string.Equals(n, "electron", StringComparison.OrdinalIgnoreCase);
                if (!own && Native.IsWindowVisible(h) && !Native.IsIconic(h) && Native.GetWindowTextLength(h) > 0) return h;
                h = Native.GetWindow(h, 2); // GW_HWNDNEXT
            }
            Program.Die("no front window");
            return IntPtr.Zero;
        }

        public static Process Match(string name)
        {
            string q = name.ToLowerInvariant();
            if (q.EndsWith(".exe")) q = q.Substring(0, q.Length - 4);
            List<Process> procs = new List<Process>();
            foreach (Process p in Process.GetProcesses()) { try { if (p.MainWindowHandle != IntPtr.Zero) procs.Add(p); } catch (Exception) { } }
            for (int mode = 1; mode <= 3; mode++)
            {
                foreach (Process p in procs)
                {
                    string[] cands;
                    try { cands = new string[] { p.ProcessName.ToLowerInvariant(), (p.MainWindowTitle ?? "").ToLowerInvariant() }; } catch (Exception) { continue; }
                    foreach (string c in cands)
                    {
                        if (c.Length == 0) continue;
                        if (mode == 1 && c == q) return p;
                        if (mode == 2 && c.StartsWith(q)) return p;
                        if (mode == 3 && c.Contains(q)) return p;
                    }
                }
            }
            return null;
        }

        static string StartMenuShortcut(string q)
        {
            string[] roots = new string[] {
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonStartMenu), "Programs"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.StartMenu), "Programs") };
            List<string> all = new List<string>();
            foreach (string r in roots) { try { if (Directory.Exists(r)) all.AddRange(Directory.GetFiles(r, "*.lnk", SearchOption.AllDirectories)); } catch (Exception) { } }
            for (int mode = 1; mode <= 3; mode++)
            {
                foreach (string f in all)
                {
                    string n = Path.GetFileNameWithoutExtension(f).ToLowerInvariant();
                    if ((mode == 1 && n == q) || (mode == 2 && n.StartsWith(q)) || (mode == 3 && n.Contains(q))) return f;
                }
            }
            return null;
        }

        // Store apps have no shortcut file: ask Windows for the Start-menu app list (a one-line built-in command)
        static string StartAppId(string q)
        {
            try
            {
                string ps = "Get-StartApps | Where-Object { $_.Name -like '*" + q.Replace("'", "''") + "*' } | Sort-Object { $_.Name.Length } | Select-Object -First 1 -ExpandProperty AppID";
                ProcessStartInfo si = new ProcessStartInfo("powershell.exe", "-NoProfile -NonInteractive -Command \"" + ps.Replace("\"", "\\\"") + "\"");
                si.UseShellExecute = false; si.RedirectStandardOutput = true; si.CreateNoWindow = true;
                using (Process p = Process.Start(si))
                {
                    string o = p.StandardOutput.ReadToEnd().Trim();
                    p.WaitForExit(15000);
                    return o.Length > 0 ? o.Split('\n')[0].Trim() : null;
                }
            }
            catch (Exception) { return null; }
        }

        public static void Open(string name)
        {
            string q = name.Trim().ToLowerInvariant();
            if (q.EndsWith(".exe")) q = q.Substring(0, q.Length - 4);
            Process p = Match(q);
            if (p != null)
            {
                Native.Activate(p.MainWindowHandle);
                Program.Out(Apps2.D("opened", Label(p.Id, p.MainWindowHandle), "pid", p.Id));
            }
            bool launched = false;
            try
            {
                string lnk = StartMenuShortcut(q);
                if (lnk != null) { Process.Start(new ProcessStartInfo(lnk) { UseShellExecute = true }); launched = true; }
            }
            catch (Exception) { }
            if (!launched)
            {
                string id = StartAppId(q);
                if (id != null) { try { Process.Start("explorer.exe", "shell:AppsFolder\\" + id); launched = true; } catch (Exception) { } }
            }
            if (!launched)
            {
                try { Process.Start(new ProcessStartInfo(name) { UseShellExecute = true }); launched = true; }
                catch (Exception) { Program.Die("app not found: " + name); }
            }
            DateTime deadline = DateTime.UtcNow.AddSeconds(12);
            while (DateTime.UtcNow < deadline)
            {
                Thread.Sleep(300);
                p = Match(q);
                if (p != null)
                {
                    try { Native.Activate(p.MainWindowHandle); } catch (Exception) { }
                    Program.Out(Apps2.D("opened", Label(p.Id, p.MainWindowHandle), "pid", p.Id));
                }
            }
            Program.Out(Apps2.D("opened", name, "pid", 0, "note", "started; no window seen yet"));
        }
    }

    // ---- mouse and keyboard --------------------------------------------------------------------------------------
    static class Input
    {
        public static void Click(int x, int y, bool right, bool dbl)
        {
            Native.SetCursorPos(x, y);
            Thread.Sleep(30);
            uint down = right ? 0x8u : 0x2u, up = right ? 0x10u : 0x4u;
            Native.mouse_event(down, 0, 0, 0, UIntPtr.Zero);
            Native.mouse_event(up, 0, 0, 0, UIntPtr.Zero);
            if (dbl)
            {
                Thread.Sleep(40);
                Native.mouse_event(down, 0, 0, 0, UIntPtr.Zero);
                Native.mouse_event(up, 0, 0, 0, UIntPtr.Zero);
            }
        }

        static readonly Dictionary<string, int> Vk = new Dictionary<string, int> {
            {"enter",0x0D},{"return",0x0D},{"tab",0x09},{"esc",0x1B},{"escape",0x1B},{"space",0x20},{"backspace",0x08},{"delete",0x2E},{"del",0x2E},
            {"up",0x26},{"down",0x28},{"left",0x25},{"right",0x27},{"home",0x24},{"end",0x23},{"pageup",0x21},{"pagedown",0x22},{"insert",0x2D} };
        static readonly int[] Extended = new int[] { 0x26, 0x28, 0x25, 0x27, 0x24, 0x23, 0x21, 0x22, 0x2D, 0x2E };

        static void Tap(int vk)
        {
            uint ext = Array.IndexOf(Extended, vk) >= 0 ? 0x1u : 0u;
            Native.Key((ushort)vk, ext);
            Native.Key((ushort)vk, ext | 0x2u);
        }

        // -> modifiers (vk codes) and the key's vk, or false for an unknown combo
        public static bool ParseCombo(string combo, List<int> mods, out int code)
        {
            code = 0;
            List<string> parts = new List<string>();
            foreach (string s in combo.ToLowerInvariant().Split('+')) if (s.Length > 0) parts.Add(s);
            if (combo.EndsWith("++") || combo == "+") parts.Add("plus");
            string key = null;
            foreach (string p in parts)
            {
                switch (p)
                {
                    case "ctrl": case "control": case "cmd": case "command": case "meta": if (!mods.Contains(0x11)) mods.Add(0x11); break;
                    case "alt": case "opt": case "option": if (!mods.Contains(0x12)) mods.Add(0x12); break;
                    case "shift": if (!mods.Contains(0x10)) mods.Add(0x10); break;
                    case "win": case "windows": case "super": if (!mods.Contains(0x5B)) mods.Add(0x5B); break;
                    case "fn": break;
                    default: key = p; break;
                }
            }
            if (key == null) return false;
            if (key == "plus") { code = 0xBB; if (!mods.Contains(0x10)) mods.Add(0x10); return true; }
            if (Vk.ContainsKey(key)) { code = Vk[key]; return true; }
            if (key.Length >= 2 && key[0] == 'f')
            {
                int n;
                if (int.TryParse(key.Substring(1), NumberStyles.Integer, CultureInfo.InvariantCulture, out n) && n >= 1 && n <= 12) { code = 0x70 + n - 1; return true; }
            }
            if (key.Length == 1)
            {
                int r = Native.VkKeyScan(key[0]);
                if (r == -1) return false;
                code = r & 0xFF;
                if ((r & 0x100) != 0 && !mods.Contains(0x10)) mods.Add(0x10);
                return true;
            }
            return false;
        }

        public static void KeyCombo(string combo)
        {
            List<int> mods = new List<int>(); int code;
            if (!ParseCombo(combo, mods, out code)) { Program.Die("unknown key combo: " + combo); return; }
            foreach (int m in mods) { Native.Key((ushort)m, 0); Thread.Sleep(10); }
            Tap(code);
            Thread.Sleep(10);
            for (int i = mods.Count - 1; i >= 0; i--) Native.Key((ushort)mods[i], 0x2);
            Program.Out(Apps2.D("ok", true));
        }

        public static void Type(string text)
        {
            int n = 0;
            foreach (char ch in text)
            {
                if (ch == '\r') continue;
                if (ch == '\n') Tap(0x0D);
                else if (ch == '\t') Tap(0x09);
                else Native.Uni(ch);
                n++;
                if (n % 20 == 0) Thread.Sleep(15);
            }
            Program.Out(Apps2.D("ok", true, "chars", text.Length));
        }
    }
    static class Apps2
    {
        public static Dictionary<string, object> D(params object[] kv)
        {
            Dictionary<string, object> d = new Dictionary<string, object>();
            for (int i = 0; i + 1 < kv.Length; i += 2) d[(string)kv[i]] = kv[i + 1];
            return d;
        }
    }

    // ---- screenshot -------------------------------------------------------------------------------------------------
    static class Shot
    {
        public static void Take(string rawPath, int max)
        {
            string path = rawPath;
            if (path.StartsWith("~")) path = Path.Combine(Environment.GetEnvironmentVariable("USERPROFILE") ?? "", path.Substring(1).TrimStart('\\', '/'));
            Rectangle b = Screen.PrimaryScreen.Bounds;
            using (Bitmap src = new Bitmap(b.Width, b.Height))
            {
                using (Graphics g = Graphics.FromImage(src)) g.CopyFromScreen(b.X, b.Y, 0, 0, src.Size);
                int longest = Math.Max(b.Width, b.Height);
                double ratio = longest > max ? (double)max / longest : 1.0;
                int w = Math.Max(1, (int)Math.Round(b.Width * ratio)), h = Math.Max(1, (int)Math.Round(b.Height * ratio));
                using (Bitmap dst = new Bitmap(w, h))
                {
                    using (Graphics g2 = Graphics.FromImage(dst))
                    {
                        g2.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
                        g2.DrawImage(src, 0, 0, w, h);
                    }
                    string dir = Path.GetDirectoryName(path);
                    if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                    ImageCodecInfo codec = null;
                    foreach (ImageCodecInfo c in ImageCodecInfo.GetImageEncoders()) if (c.MimeType == "image/jpeg") codec = c;
                    EncoderParameters ep = new EncoderParameters(1);
                    ep.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.Quality, 70L);
                    dst.Save(path, codec, ep);
                    Program.Out(Apps2.D("path", path, "width", w, "height", h, "scale", Math.Round((double)b.Width / w, 4)));
                }
            }
        }
    }
}
