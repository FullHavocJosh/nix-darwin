Lumo is available (Proton's cloud assistant on macminim1; free, no tools, can search online). After you have read
the code that matters, call lumo_consult once with the user's request and the few project files that matter
(relative paths; secrets, keys and env files are refused). It returns a draft task breakdown that includes what
Lumo found online about current practice. Do not turn it into a plan yourself: pass it unchanged as `draft` to
ralph_plan. If the call returns ok=false, tell the user in one line that Lumo is unavailable and go on without a draft.
Say so in the chat: before calling lumo_consult write one line ("Consulting Lumo on MacMiniM1 for a draft..."),
and after it returns say that Lumo's draft arrived and will go to Claude with your brief.
