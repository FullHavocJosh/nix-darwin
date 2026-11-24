#!/usr/bin/env python3
"""Print this device's llm.rollet.family gateway key on stdout, for pi's apiKey "!command" (the key is read at
request time and never stored in models.json). Order: AIDEV_REMOTE_BUILDER_KEY_FILE, AIDEV_REMOTE_BUILDER_KEY,
~/.config/llm-gateway/key, Doppler LLM_KEY_<LLM_DEVICE>, Doppler LLM_PUBLIC_API_KEY (see remote_builder.read_key).
Exit 1 with no output when no key resolves. Stdlib only."""
import importlib.util
import os
import sys

spec = importlib.util.spec_from_file_location("remote_builder", os.path.join(os.path.dirname(os.path.abspath(__file__)), "remote_builder.py"))
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)
key = rb.read_key()
if not key:
    sys.exit(1)
sys.stdout.write(key)
