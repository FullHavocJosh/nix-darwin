Tier 0 is available (Lumo on macminim1). For every new plan, after you have read the code that matters, call
lumo_consult once with the user's request and the few project files that matter (relative paths; secrets, keys
and env files are refused). That sends them to Lumo, Proton's cloud assistant, which returns a draft task
breakdown. Treat it as a draft: keep what fits the code you read, fix tasks that are too big or wrong, and still
write and validate the plan yourself. If the call returns ok=false, tell the user in one line that Lumo is
unavailable and plan it yourself.
   Say so in the chat: before calling lumo_consult write one line ("Consulting Lumo on MacMiniM1 for a draft plan..."),
   and after it returns say that Lumo's draft arrived and which parts you kept or changed. The user wants to see that
   tier 0 is being used.
