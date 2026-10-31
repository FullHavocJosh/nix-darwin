import hashlib
import json
import os
import subprocess


def claude_available(timeout: int = 20, runner: callable = subprocess.run) -> tuple[bool, str]:
    """
    Check if Claude is available.
    
    Returns:
        Tuple[bool, str]: (ok, why) where ok is True if Claude is available
        and why is a description of the result.
    """
    try:
        result = runner(
            ['claude', '-p', 'Reply with the single word ok.', '--model', 'haiku', '--no-session-persistence', '--output-format', 'text'],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            check=False
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return (True, "")
        else:
            # Get last 200 characters of output for error message
            output = result.stdout.strip() + result.stderr.strip()
            if len(output) > 200:
                output = output[-200:]
            return (False, f"claude exited {result.returncode}: {output}")
            
    except subprocess.TimeoutExpired:
        return (False, f"claude did not answer in {timeout} s")
    except FileNotFoundError:
        return (False, "claude is not installed")


def choose_planner(env: dict[str, str], probe: callable = claude_available) -> tuple[str, str]:
    """
    Choose the planner based on environment and probe results.
    
    Returns:
        Tuple[str, str]: (planner, reason) where planner is 'claude' or 'local'
        and reason is the reason for the choice.
    """
    if 'AIDEV_TUIOS_PLANNER' in env:
        planner = env['AIDEV_TUIOS_PLANNER']
        if planner in ('claude', 'local'):
            return (planner, 'forced by AIDEV_TUIOS_PLANNER')
    
    # Probe Claude availability
    ok, why = probe()
    if ok:
        return ('claude', '')
    else:
        return ('local', why)


def planner_models(base_url: str, model_id: str, ctx: int) -> dict:
    """
    Return planner model configuration.
    
    Returns:
        Dict: Configuration for the planner provider.
    """
    return {
        'providers': {
            'planner': {
                'baseUrl': base_url.rstrip('/') + '/v1',
                'api': 'openai-completions',
                'apiKey': 'sk-local',
                'models': [{
                    'id': model_id,
                    'reasoning': False,
                    'contextWindow': ctx,
                    'maxTokens': 4096
                }]
            }
        }
    }


def read_events(run_dir: str) -> list[dict]:
    """
    Read events from JSONL files in run_dir.
    
    Returns:
        List[Dict]: List of event dictionaries, or empty list if no events.
    """
    events = []
    
    try:
        for filename in os.listdir(run_dir):
            if filename.endswith('.jsonl'):
                filepath = os.path.join(run_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    event = json.loads(line)
                                    events.append(event)
                                except json.JSONDecodeError:
                                    # Skip bad lines
                                    continue
                except OSError:
                    # Skip files that can't be read
                    continue
    except OSError:
        # Directory doesn't exist
        pass
    
    return events


def gate_message(events: list[dict], planner: str, has_research: bool, env: dict[str, str]) -> str:
    """
    Generate gate message for local planner.
    
    Returns:
        str: Gate message or empty string if no gate is needed.
    """
    # If not using local planner, no gate
    if planner != 'local':
        return ''
    
    # If no research needed, no gate
    if not has_research:
        return ''
    
    # If gate is explicitly disabled, no gate
    if env.get('AIDEV_TUIOS_PLANNER_GATE') == 'off':
        return ''
    
    # Check if any ask_lumo event with searched=true exists
    for event in events:
        if event.get('kind') == 'ask_lumo' and event.get('searched'):
            return ''
    
    # Check if lumo_waiver event exists
    for event in events:
        if event.get('kind') == 'lumo_waiver':
            return ''
    
    # Need to ask for research
    return 'RESEARCH REQUIRED: Please run ask-lumo about every library, tool or API version the plan touches, or ask-lumo --none-needed "<reason>" when the plan only touches this repository.'


def cache_path(research_dir: str, question: str) -> str:
    """
    Generate cache file path for a question.
    
    Returns:
        str: Path to the cache file.
    """
    # Normalize question: lowercase and collapse whitespace
    normalized = ' '.join(question.lower().split())
    # Get SHA1 hash and take first 12 hex characters
    hash_digest = hashlib.sha1(normalized.encode('utf-8')).hexdigest()
    filename = hash_digest[:12] + '.md'
    return os.path.join(research_dir, filename)


def cache_lookup(research_dir: str, question: str) -> str | None:
    """
    Look up a question in the cache.
    
    Returns:
        Optional[str]: Content of the cached file or None if not found.
    """
    path = cache_path(research_dir, question)
    try:
        with open(path, 'r') as f:
            return f.read()
    except OSError:
        return None


def cache_store(research_dir: str, question: str, reply: str, queries: str) -> str:
    """
    Store a question and reply in the cache.
    
    Returns:
        str: Path to the stored file.
    """
    # Ensure directory exists
    os.makedirs(research_dir, exist_ok=True)
    
    path = cache_path(research_dir, question)
    
    with open(path, 'w') as f:
        f.write(f'QUESTION: {question}\n')
        f.write(f'QUERIES: {queries}\n')
        f.write('\n')
        f.write(reply)
    
    return path