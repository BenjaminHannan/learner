// Glim setup (Windows, Nov 4): one file to download and double-click. The app's zip rides inside this exe as a resource.
// It unpacks to %LOCALAPPDATA%\Programs\Premonition (no admin rights needed), puts "Glim" on the Desktop and in the Start menu,
// and starts the app, whose first run then downloads Glim's brain by itself. Running it again updates the app in place
// (the user's chats and notes live in %APPDATA%\Premonition and are never touched here).
// Built by build-win.sh with mono's mcs against the .NET Framework 4.8 reference assemblies (Windows 10/11 ship 4.8).
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;

static class GlimSetup {
    const string AppName = "Premonition", Shown = "Glim", Resource = "app.zip";

    [STAThread]
    static int Main(string[] args) {
        bool quiet = Array.IndexOf(args, "/quiet") >= 0;          // tests: no window, no shortcuts, no launch
        string target = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", AppName);
        for (int i = 0; i + 1 < args.Length; i++) if (args[i] == "/dir") target = args[i + 1];
        if (quiet) { try { Unpack(target, null); Console.WriteLine("installed " + target); return 0; } catch (Exception e) { Console.Error.WriteLine(e.Message); return 1; } }

        Application.EnableVisualStyles();
        var form = new Form { Text = "Setting up " + Shown, Width = 460, Height = 170, FormBorderStyle = FormBorderStyle.FixedDialog, MaximizeBox = false, MinimizeBox = false, StartPosition = FormStartPosition.CenterScreen };
        var label = new Label { Text = "Getting " + Shown + " ready on this computer…", Left = 20, Top = 20, Width = 410, Height = 24, Font = new Font("Segoe UI", 11f) };
        var bar = new ProgressBar { Left = 20, Top = 56, Width = 405, Height = 22, Minimum = 0, Maximum = 100 };
        var small = new Label { Text = "This takes about a minute. Nothing to do.", Left = 20, Top = 88, Width = 410, Height = 22, ForeColor = Color.DimGray };
        form.Controls.Add(label); form.Controls.Add(bar); form.Controls.Add(small);
        int code = 0;
        form.Shown += (s, e) => new Thread(() => {
            try {
                Unpack(target, p => form.BeginInvoke((Action)(() => bar.Value = Math.Max(0, Math.Min(100, p)))));
                string exe = Path.Combine(target, AppName + ".exe");
                Shortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), Shown + ".lnk"), exe);
                Shortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs), Shown + ".lnk"), exe);
                Process.Start(new ProcessStartInfo(exe) { WorkingDirectory = target, UseShellExecute = true });
                form.BeginInvoke((Action)(() => form.Close()));
            } catch (Exception ex) {
                code = 1;
                string why = ex is IOException || ex is UnauthorizedAccessException ? "Close " + Shown + " (right-click its icon near the clock, then Quit) and run this again." : ex.Message;
                form.BeginInvoke((Action)(() => { MessageBox.Show(form, "Setup could not finish.\n\n" + why, "Setting up " + Shown); form.Close(); }));
            }
        }) { IsBackground = true }.Start();
        Application.Run(form);
        return code;
    }

    // app.zip holds "Premonition-win32-x64\..."; the first folder is dropped so the app lands directly in target
    static void Unpack(string target, Action<int> progress) {
        using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream(Resource))
        using (var zip = new ZipArchive(s, ZipArchiveMode.Read)) {
            Directory.CreateDirectory(target);
            string root = Path.GetFullPath(target) + Path.DirectorySeparatorChar;
            long total = 0, done = 0;
            foreach (var e in zip.Entries) total += e.Length;
            foreach (var e in zip.Entries) {
                string rel = e.FullName.Replace('/', '\\');
                int cut = rel.IndexOf('\\');
                if (cut < 0) continue;
                rel = rel.Substring(cut + 1);
                if (rel.Length == 0) continue;
                string dest = Path.GetFullPath(Path.Combine(target, rel));
                if (!dest.StartsWith(root, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("bad path in the package: " + e.FullName);
                if (rel.EndsWith("\\")) { Directory.CreateDirectory(dest); continue; }
                Directory.CreateDirectory(Path.GetDirectoryName(dest));
                using (var from = e.Open()) using (var to = File.Create(dest)) from.CopyTo(to);
                done += e.Length;
                if (progress != null && total > 0) progress((int)(done * 100 / total));
            }
        }
    }

    static void Shortcut(string lnk, string exe) {
        try {
            Type t = Type.GetTypeFromProgID("WScript.Shell");
            object sh = Activator.CreateInstance(t);
            object sc = t.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, sh, new object[] { lnk });
            Type st = sc.GetType();
            st.InvokeMember("TargetPath", BindingFlags.SetProperty, null, sc, new object[] { exe });
            st.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, sc, new object[] { Path.GetDirectoryName(exe) });
            st.InvokeMember("Description", BindingFlags.SetProperty, null, sc, new object[] { Shown });
            st.InvokeMember("Save", BindingFlags.InvokeMethod, null, sc, null);
        } catch { /* a missing shortcut is not worth failing setup over */ }
    }
}
