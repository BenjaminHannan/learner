"""Writes tools.json: the fixed local-assistant tool set (OpenAI function format)."""
import json, pathlib
def T(name, desc, props, req):
    return {"type":"function","function":{"name":name,"description":desc,
        "parameters":{"type":"object","properties":props,"required":req,"additionalProperties":False}}}
S=lambda d,**k:{"type":"string","description":d,**k}
I=lambda d,**k:{"type":"integer","description":d,**k}
B=lambda d:{"type":"boolean","description":d}
tools=[
 T("read_file","Read a text file from the local disk.",{"path":S("Absolute or ~-relative path"),"max_lines":I("Max lines to return",minimum=1,maximum=2000)},["path"]),
 T("write_file","Write (create or overwrite) a text file.",{"path":S("File path"),"content":S("Full file contents"),"append":B("Append instead of overwrite")},["path","content"]),
 T("list_dir","List files and folders in a directory.",{"path":S("Directory path"),"recursive":B("Recurse into subfolders")},["path"]),
 T("search_files","Search file names or file contents under a directory.",{"query":S("Text or glob to search for"),"path":S("Directory to search in"),"mode":S("What to match",enum=["name","content"])},["query"]),
 T("run_shell","Run a shell command on the MacBook (zsh) and return stdout, stderr and exit code.",{"command":S("Command line to run"),"cwd":S("Working directory")},["command"]),
 T("web_search","Search the web and return result titles, URLs and snippets.",{"query":S("Search query"),"num_results":I("Number of results",minimum=1,maximum=10)},["query"]),
 T("fetch_url","Fetch a web page and return its text content.",{"url":S("http(s) URL")},["url"]),
 T("calendar_list_events","List calendar events in a date range.",{"start_date":S("YYYY-MM-DD"),"end_date":S("YYYY-MM-DD"),"calendar":S("Calendar name, e.g. Personal, School")},["start_date","end_date"]),
 T("calendar_create_event","Create a calendar event.",{"title":S("Event title"),"start":S("ISO 8601 start datetime"),"end":S("ISO 8601 end datetime"),"calendar":S("Calendar name"),"location":S("Location"),"attendees":{"type":"array","items":S("Email address"),"description":"Invitee emails"}},["title","start","end"]),
 T("email_search","Search the mailbox.",{"query":S("Search text, supports from:/subject:/after:"),"folder":S("Mail folder",enum=["inbox","sent","drafts","archive"]),"limit":I("Max results",minimum=1,maximum=50)},["query"]),
 T("email_draft","Save an email draft (does not send).",{"to":{"type":"array","items":S("Email address"),"minItems":1},"subject":S("Subject"),"body":S("Plain text body"),"cc":{"type":"array","items":S("Email address")}},["to","subject","body"]),
 T("send_email","Send an email immediately. IRREVERSIBLE: always confirm recipients and content with the user first.",{"to":{"type":"array","items":S("Email address"),"minItems":1},"subject":S("Subject"),"body":S("Plain text body"),"cc":{"type":"array","items":S("Email address")}},["to","subject","body"]),
 T("set_reminder","Set a reminder that notifies the user at a given time.",{"text":S("Reminder text"),"when":S("ISO 8601 datetime"),"repeat":S("Repeat rule",enum=["none","daily","weekly","monthly"])},["text","when"]),
 T("notes_search","Search the user's notes app.",{"query":S("Search text"),"limit":I("Max results",minimum=1,maximum=20)},["query"]),
 T("notes_append","Append text to a note, creating it if missing.",{"title":S("Note title"),"text":S("Text to append")},["title","text"]),
]
pathlib.Path(__file__).with_name("tools.json").write_text(json.dumps(tools,indent=1))
print(len(tools),"tools")
