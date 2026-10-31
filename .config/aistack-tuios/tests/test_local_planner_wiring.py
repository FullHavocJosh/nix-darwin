#!/usr/bin/env python3
"""Test that the local planner wiring works correctly."""

import os
import sys
import tempfile

# Add the parent directory to the path so we can import aidev_tuios
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Import the module
import aidev_tuios as a


def check(name, cond):
    if not cond:
        print(f"FAIL: {name}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"PASS: {name}")

def main():
    # Create temporary directories for testing
    with tempfile.TemporaryDirectory() as tmp:
        # Create fake run object
        import types
        run = types.SimpleNamespace(
            project=tmp,
            plan_dir=tmp+'/plan',
            dir=tmp+'/run',
            id='r1',
            data={'panes': {}}
        )
        
        # Create config with pi_plan directory
        cfg = {'pi_plan': tmp+'/pi-plan'}
        
        # Create directories
        os.makedirs(tmp+'/plan', exist_ok=True)
        os.makedirs(tmp+'/run', exist_ok=True)
        os.makedirs(tmp+'/pi-plan', exist_ok=True)
        
        # Test local_planner_body
        body = a.local_planner_body(run, cfg, 'hello', True)
        
        # Check that the body contains expected elements
        check('body contains pi', 'pi ' in body)
        check('body contains planner/', 'planner/' in body)
        check('body contains PI_CODING_AGENT_DIR', 'PI_CODING_AGENT_DIR' in body)
        check('body does not contain claude', 'claude --' not in body)
        
        # Check that models.json was created
        models_file = os.path.join(tmp, 'pi-plan', 'models.json')
        check('models.json exists', os.path.exists(models_file))
        
        # Check that models.json contains 'planner'
        with open(models_file, 'r') as f:
            content = f.read()
            check('models.json contains planner', 'planner' in content)
        
        # Test choose_planner with local planner
        result = a.planner_local.choose_planner({'AIDEV_TUIOS_PLANNER':'local'})
        check('choose_planner returns local', result[0] == 'local')
        check('choose_planner returns forced by AIDEV_TUIOS_PLANNER', result[1] == 'forced by AIDEV_TUIOS_PLANNER')

if __name__ == '__main__':
    main()