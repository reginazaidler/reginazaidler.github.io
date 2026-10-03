import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

spec = importlib.util.spec_from_file_location('gate', Path(__file__).parents[1] / 'review_staged_changes.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class GateTests(unittest.TestCase):
    def exercise(self, review, key='test', changed=False, network_error=False):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'choices': [{'message': {'content': json.dumps(review)}}]}).encode()
        trees = iter([b'tree', b'changed' if changed else b'tree'])
        def git(*args):
            return next(trees) if args[0] == 'write-tree' else b'diff --git a/index.html b/index.html\n+change'
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'OPENAI_API_KEY': key, 'RUNNER_TEMP': temp}), patch.object(gate, 'git', git), patch.object(gate.subprocess, 'run') as run, patch.object(gate, 'build_context', return_value='staged context'), patch.object(gate.urllib.request, 'urlopen', side_effect=OSError() if network_error else None, return_value=response):
            gate.run_review()
            self.assertIn('checkout-index', run.call_args_list[0].args[0])
            self.assertNotEqual(run.call_args_list[1].kwargs['cwd'], os.getcwd())
            self.assertTrue((Path(temp) / 'website-code-review.json').exists())

    def test_approval(self):
        self.exercise({'approved': True, 'blocking_findings': [], 'summary': 'ok'})

    def test_rejection(self):
        with self.assertRaises(RuntimeError):
            self.exercise({'approved': False, 'blocking_findings': ['bad'], 'summary': 'bad'})

    def test_contradictory_approval(self):
        with self.assertRaises(RuntimeError):
            self.exercise({'approved': True, 'blocking_findings': ['bad'], 'summary': 'bad'})

    def test_missing_key(self):
        with self.assertRaises(RuntimeError):
            self.exercise({}, key='')

    def test_malformed_response(self):
        with self.assertRaises(RuntimeError):
            self.exercise({'approved': 'true'})

    def test_staged_mutation(self):
        with self.assertRaises(RuntimeError):
            self.exercise({'approved': True, 'blocking_findings': [], 'summary': 'ok'}, changed=True)

    def test_api_failure(self):
        with self.assertRaises(OSError):
            self.exercise({}, network_error=True)


if __name__ == '__main__':
    unittest.main()
