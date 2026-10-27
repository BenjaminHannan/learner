// UI Automation part of deskhelper.exe (look / press). Kept in its own class so help and the input commands never load UIAutomationClient.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Automation;

namespace Premonition
{
    static class Ui
    {
        static readonly string[] Actionable = { "Button", "CheckBox", "RadioButton", "ComboBox", "Edit", "Hyperlink", "ListItem", "MenuItem", "TabItem", "TreeItem", "Slider", "SplitButton", "Spinner", "DataItem", "Document" };
        static readonly string[] TextRoles = { "Edit", "ComboBox", "Spinner" };
        static readonly string[] LeafRoles = { "Button", "CheckBox", "RadioButton", "ComboBox", "Edit", "MenuItem", "TabItem", "Slider", "SplitButton", "Spinner", "Hyperlink" };

        class Found { public int[] Path; public string Role; public string Label; public string Value; public Rect Frame; public bool IsText; }

        static CacheRequest cr;
        static TreeWalker tw;
        static int visited, budget = 2500, textCount;
        const int MaxText = 40;
        static List<Found> found = new List<Found>();
        static Stopwatch sw = Stopwatch.StartNew();
        static System.Drawing.Rectangle screen;

        static void Init()
        {
            cr = new CacheRequest();
            cr.Add(AutomationElement.NameProperty); cr.Add(AutomationElement.ControlTypeProperty); cr.Add(AutomationElement.BoundingRectangleProperty);
            cr.Add(AutomationElement.IsOffscreenProperty); cr.Add(AutomationElement.IsPasswordProperty); cr.Add(AutomationElement.HelpTextProperty); cr.Add(AutomationElement.AutomationIdProperty);
            cr.Add(ValuePattern.Pattern); cr.Add(ValuePattern.ValueProperty);
            cr.TreeScope = TreeScope.Element;
            tw = TreeWalker.ControlViewWalker;
            screen = System.Windows.Forms.SystemInformation.VirtualScreen;
        }

        static string Trim80(string s)
        {
            if (s == null) return "";
            string t = s.Replace("\r", " ").Replace("\n", " ").Trim();
            return t.Length > 80 ? t.Substring(0, 80) : t;
        }
        static string RoleOf(AutomationElement.AutomationElementInformation c) { return c.ControlType.ProgrammaticName.Replace("ControlType.", ""); }
        static string CachedValue(AutomationElement el)
        {
            try { object o; if (el.TryGetCachedPattern(ValuePattern.Pattern, out o)) return ((ValuePattern)o).Cached.Value ?? ""; } catch (Exception) { }
            return "";
        }
        static bool Visible(AutomationElement.AutomationElementInformation c, out Rect r)
        {
            r = Rect.Empty;
            try
            {
                if (c.IsOffscreen) return false;
                r = c.BoundingRectangle;
                if (r.IsEmpty || r.Width <= 0 || r.Height <= 0) return false;
                if (r.X + r.Width <= screen.X || r.Y + r.Height <= screen.Y || r.X >= screen.X + screen.Width || r.Y >= screen.Y + screen.Height) return false;
                return true;
            }
            catch (Exception) { return false; }
        }
        static string LabelOf(AutomationElement el, AutomationElement.AutomationElementInformation c, string role)
        {
            string n = Trim80(c.Name); if (n.Length > 0) return n;
            string h = Trim80(c.HelpText); if (h.Length > 0) return h;
            if (Array.IndexOf(LeafRoles, role) >= 0 && role != "Edit") { string v = Trim80(CachedValue(el)); if (v.Length > 0) return v; }
            return "";
        }

        static void Walk(AutomationElement el, int[] path, int depth)
        {
            if (visited >= budget || depth > 30 || sw.ElapsedMilliseconds > 14000) return;
            visited++;
            bool descend = true;
            try
            {
                AutomationElement.AutomationElementInformation c = el.Cached;
                string role = RoleOf(c);
                Rect rect;
                if (Visible(c, out rect))
                {
                    if (role == "Text")
                    {
                        string v = Trim80(c.Name);
                        if (v.Length > 0 && textCount < MaxText) { textCount++; found.Add(new Found { Path = path, Role = "Text", Label = v, Value = "", Frame = rect, IsText = true }); }
                    }
                    else if (Array.IndexOf(Actionable, role) >= 0)
                    {
                        string label = LabelOf(el, c, role);
                        bool keep = true;
                        if (role == "ListItem" || role == "DataItem" || role == "TreeItem") keep = label.Length > 0;
                        if (role == "Edit" || role == "ComboBox" || role == "Document") keep = true; // Document: e.g. the Windows 11 Notepad text area
                        if (keep)
                        {
                            string value = "", outRole = role;
                            if (c.IsPassword) { outRole = "SecureEdit"; value = ""; } // never read a password field
                            else if (Array.IndexOf(TextRoles, role) >= 0) value = Trim80(CachedValue(el));
                            found.Add(new Found { Path = path, Role = outRole, Label = label, Value = value, Frame = rect, IsText = false });
                            if (Array.IndexOf(LeafRoles, role) >= 0 && (label.Length > 0 || Array.IndexOf(TextRoles, role) >= 0)) descend = false;
                        }
                    }
                }
            }
            catch (Exception) { }
            if (!descend) return;
            int i = 0;
            AutomationElement ch = null;
            try { ch = tw.GetFirstChild(el, cr); } catch (Exception) { ch = null; }
            while (ch != null)
            {
                if (visited >= budget) break;
                int[] p = new int[path.Length + 1]; Array.Copy(path, p, path.Length); p[path.Length] = i;
                Walk(ch, p, depth + 1);
                i++;
                try { ch = tw.GetNextSibling(ch, cr); } catch (Exception) { ch = null; }
            }
        }

        static int[] FrameArr(Rect r) { return new int[] { (int)Math.Round(r.X), (int)Math.Round(r.Y), (int)Math.Round(r.Width), (int)Math.Round(r.Height) }; }

        // ---- typing: find where the keystrokes should land, and whether they did ----------------------------------------
        static bool Editable(AutomationElement e)
        {
            try
            {
                ControlType t = e.Current.ControlType;
                return (t == ControlType.Edit || t == ControlType.Document) && e.Current.IsEnabled;
            }
            catch (Exception) { return false; }
        }
        // The focused element if it takes text; else the biggest visible text box / document of the front window, focused
        // (and clicked, if focusing is refused). Returns null when there is nothing to type into (the keys go wherever).
        public static AutomationElement FocusEditable()
        {
            try
            {
                AutomationElement f = AutomationElement.FocusedElement;
                if (f != null && Editable(f)) return f;
                IntPtr h = Native.GetForegroundWindow();
                if (h == IntPtr.Zero) return null;
                AutomationElement root = AutomationElement.FromHandle(h);
                Condition cond = new AndCondition(
                    new OrCondition(new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Document), new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Edit)),
                    new PropertyCondition(AutomationElement.IsOffscreenProperty, false),
                    new PropertyCondition(AutomationElement.IsEnabledProperty, true));
                AutomationElement best = null; double area = 0;
                foreach (AutomationElement e in root.FindAll(TreeScope.Descendants, cond))
                {
                    try { Rect r = e.Current.BoundingRectangle; double a = r.Width * r.Height; if (!r.IsEmpty && a > area) { area = a; best = e; } } catch (Exception) { }
                }
                if (best == null) return null;
                try { best.SetFocus(); }
                catch (Exception)
                {
                    try { Rect r = best.Current.BoundingRectangle; Input.ClickRaw((int)(r.X + r.Width / 2), (int)(r.Y + r.Height / 2)); } catch (Exception) { }
                }
                System.Threading.Thread.Sleep(80);
                return best;
            }
            catch (Exception) { return null; }
        }
        // The element's text, only to tell whether typing changed it (never printed). null = can't tell (or a password field).
        public static string TextOf(AutomationElement e)
        {
            if (e == null) return null;
            try
            {
                if (e.Current.IsPassword) return null;
                object o;
                if (e.TryGetCurrentPattern(TextPattern.Pattern, out o)) return ((TextPattern)o).DocumentRange.GetText(20000);
                if (e.TryGetCurrentPattern(ValuePattern.Pattern, out o)) return ((ValuePattern)o).Current.Value;
            }
            catch (Exception) { }
            return null;
        }

        public static void Look(string appName, int max)
        {
            Init();
            sw.Restart();
            IntPtr h;
            if (!string.IsNullOrEmpty(appName))
            {
                Process p = Apps.Match(appName);
                if (p == null) { Program.Die("no running app matches '" + appName + "'"); return; }
                h = p.MainWindowHandle;
            }
            else h = Apps.FrontWindow();
            int pid = Native.WindowPid(h);
            AutomationElement root = AutomationElement.FromHandle(h).GetUpdatedCache(cr);
            Dictionary<string, object> wd = Apps2.D("title", Trim80(root.Cached.Name));
            try { wd["frame"] = FrameArr(root.Cached.BoundingRectangle); } catch (Exception) { }
            List<object> winInfo = new List<object>(); winInfo.Add(wd);

            Walk(root, new int[] { 0 }, 0);

            List<Found> chosen = new List<Found>();
            foreach (Found f in found) if (!f.IsText && chosen.Count < max) chosen.Add(f);
            foreach (Found f in found) if (f.IsText && chosen.Count < max) chosen.Add(f);
            List<Found> sorted = chosen.OrderBy(f => f.Frame.Y).ThenBy(f => f.Frame.X).ToList();

            List<object> elements = new List<object>(), cache = new List<object>();
            int id = 0;
            foreach (Found f in sorted)
            {
                id++;
                int[] fa = FrameArr(f.Frame);
                elements.Add(Apps2.D("id", id, "role", f.Role, "title", f.Label, "value", f.Value, "frame", fa));
                cache.Add(Apps2.D("id", id, "path", f.Path, "role", f.Role, "label", f.Label, "frame", fa));
            }
            try
            {
                Directory.CreateDirectory(Program.CacheFolder);
                File.WriteAllText(Program.Cache, J.Ser(Apps2.D("pid", pid, "hwnd", (long)h, "elements", cache)), new UTF8Encoding(false));
            }
            catch (Exception e) { Program.Die("could not write look cache: " + e.Message); return; }
            Program.Out(Apps2.D("app", Apps.Label(pid, h), "pid", pid, "windows", winInfo, "elements", elements));
        }

        static AutomationElement Resolve(IntPtr h, int[] path)
        {
            AutomationElement cur = AutomationElement.FromHandle(h).GetUpdatedCache(cr);
            for (int k = 1; k < path.Length; k++)
            {
                AutomationElement ch = tw.GetFirstChild(cur, cr);
                for (int j = 0; j < path[k] && ch != null; j++) ch = tw.GetNextSibling(ch, cr);
                if (ch == null) return null;
                cur = ch;
            }
            return cur;
        }

        public static void Press(int id)
        {
            Init();
            if (!File.Exists(Program.Cache)) { Program.Die("no saved look; run look first"); return; }
            Dictionary<string, object> obj = (Dictionary<string, object>)new JavaScriptSerializer { MaxJsonLength = int.MaxValue }.DeserializeObject(File.ReadAllText(Program.Cache));
            Dictionary<string, object> entry = null;
            foreach (object e in (IEnumerable)obj["elements"]) { Dictionary<string, object> d = (Dictionary<string, object>)e; if (Convert.ToInt32(d["id"]) == id) entry = d; }
            if (entry == null) { Program.Die("no element with id " + id + " in the last look"); return; }
            List<int> fr = new List<int>(); foreach (object o in (IEnumerable)entry["frame"]) fr.Add(Convert.ToInt32(o));
            int cx = (int)(fr[0] + fr[2] / 2.0), cy = (int)(fr[1] + fr[3] / 2.0);
            string role = Convert.ToString(entry["role"]);
            IntPtr h = new IntPtr(Convert.ToInt64(obj["hwnd"]));
            if (role == "Edit" || role == "ComboBox" || role == "SecureEdit")
            {
                try
                {
                    List<int> path = new List<int>(); foreach (object o in (IEnumerable)entry["path"]) path.Add(Convert.ToInt32(o));
                    AutomationElement el = Resolve(h, path.ToArray());
                    if (el != null) { el.SetFocus(); Program.Out(Apps2.D("ok", true, "id", id, "method", "focus")); }
                }
                catch (ExitException) { throw; }
                catch (Exception) { }
            }
            // everything else: a real click on its centre (patterns like Invoke can block on dialogs), after bringing its window forward
            try { Native.Activate(h); System.Threading.Thread.Sleep(80); } catch (Exception) { }
            Input.Click(cx, cy, false, false);
            Program.Out(Apps2.D("ok", true, "id", id, "method", "click"));
        }
    }
}
