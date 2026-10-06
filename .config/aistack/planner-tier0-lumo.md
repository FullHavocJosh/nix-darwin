Tier 0 is available (Lumo on macminim1). For every new plan, after you have read the code that matters, call
lumo_consult once with the user's request and the few project files that matter (relative paths; secrets, keys
and env files are refused). That sends them to Lumo, Proton's cloud assistant, which returns a draft task
breakdown. Treat it as a draft: keep what fits the code you read, fix tasks that are too big or wrong, and still
write and validate the plan yourself. If the call returns ok=false, tell the user in one line that Lumo is
unavailable and plan it yourself.
