import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generate_article as generator

WORKFLOW = (Path(__file__).resolve().parents[2] / '.github/workflows/insurance-trends-agent.yml').read_text()
PUBLISH = WORKFLOW.split('      - name: Review, commit and push new files\n', 1)[1].split('        run: |\n', 1)[1].split('\n      - name:', 1)[0]
PUBLISH = '\n'.join(line[10:] for line in PUBLISH.splitlines())
SLUG = 'clal-insurance-unclaimed-unredeemed-checks'


class NotificationTests(unittest.TestCase):
    def test_generation_outputs_only_after_completed_creation(self):
        meta = dict(slug=SLUG, chosen_trend='test', reason='test', h1='test', keyword='test', meta_description='test')
        for mode in ('SKIP', 'UPDATE', 'selection', 'dry', 'CREATE', 'index_failure'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'reports').mkdir()
                stale = root / 'reports/last-generated-article.json'
                stale.write_text(json.dumps({'slug': 'old-article'}))
                output = root / 'output'
                args = types.SimpleNamespace(json_path='unused', output_dir=tmp, max_trends=15, selection_only=mode == 'selection', dry_run=mode == 'dry', orchestrator_decision='reports/orchestrator-decision.json')
                orchestrator = types.SimpleNamespace(decide=lambda *a: {'action': mode if mode in ('SKIP', 'UPDATE') else 'CREATE', 'reason': 'test'})
                def indexes(**kwargs):
                    if mode == 'index_failure':
                        raise RuntimeError('index failure')
                with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}), patch.dict(sys.modules, {'seo_orchestrator': orchestrator}), patch.object(generator, 'parse_args', return_value=args), patch.object(generator, 'load_report', return_value={}), patch.object(generator, 'pick_best_trend', return_value=meta), patch.object(generator, 'write_article', return_value={}), patch.object(generator, 'build_html', return_value='<html>test</html>'), patch.object(generator, 'update_all_indexes', side_effect=indexes), contextlib.redirect_stdout(io.StringIO()):
                    if mode == 'index_failure':
                        with self.assertRaises(RuntimeError):
                            generator.main()
                    else:
                        self.assertEqual(generator.main(), 0)
                self.assertEqual(output.read_text() if output.exists() else '', f'article_slug={SLUG}\n' if mode == 'CREATE' else '')
                if mode in ('SKIP', 'UPDATE', 'selection', 'dry'):
                    self.assertEqual(json.loads(stale.read_text())['slug'], 'old-article')

    def test_publish_requires_new_html_and_successful_push(self):
        for mode in ('stale_SKIP', 'stale_without_generation', 'existing', 'missing', 'new', 'push_failure', 'review_failure'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / 'repo'
                root.mkdir()
                def git(*args):
                    return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True)
                git('init', '-b', 'main')
                git('config', 'user.name', 'Test')
                git('config', 'user.email', 'test@example.com')
                (root / 'reports').mkdir()
                (root / 'data/trends-agent').mkdir(parents=True)
                (root / 'scripts').mkdir()
                (root / 'scripts/review_staged_changes.py').write_text('raise SystemExit(1)' if mode == 'review_failure' else '')
                for name in ('sitemap.xml', 'llms.txt', 'articles.html'):
                    (root / name).write_text('initial')
                (root / 'reports/last-generated-article.json').write_text(json.dumps({'slug': SLUG}))
                html = root / f'{SLUG}.html'
                if mode in ('stale_SKIP', 'stale_without_generation', 'existing'):
                    html.write_text('old article')
                git('add', '.')
                git('commit', '-m', 'initial')
                remote = Path(tmp) / 'remote.git'
                subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
                git('remote', 'add', 'origin', str(remote))
                git('push', '-u', 'origin', 'main')
                if mode == 'push_failure':
                    git('remote', 'set-url', 'origin', str(Path(tmp) / 'missing.git'))
                (root / 'reports/orchestrator-decision.json').write_text(json.dumps({'action': 'SKIP' if mode == 'stale_SKIP' else 'CREATE'}))
                if mode in ('new', 'push_failure', 'review_failure', 'existing'):
                    html.write_text('new content')
                output = Path(tmp) / 'output'
                env = dict(os.environ, GENERATED_SLUG='' if mode.startswith('stale') else SLUG, GITHUB_OUTPUT=str(output))
                result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', PUBLISH], cwd=root, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, mode not in ('push_failure', 'review_failure'), result.stderr)
                self.assertEqual(output.read_text() if output.exists() else '', f'article_slug={SLUG}\n' if mode == 'new' else '')
                if mode not in ('push_failure', 'review_failure'):
                    report = subprocess.check_output(['git', '--git-dir', str(remote), 'show', 'main:reports/orchestrator-decision.json'], text=True)
                    self.assertIn('SKIP' if mode == 'stale_SKIP' else 'CREATE', report)
                if mode == 'new':
                    self.assertIn(SLUG, git('log', '-1', '--format=%s').stdout)

    def test_email_uses_successful_publish_output(self):
        email = WORKFLOW.split('      - name: Send email summary\n', 1)[1].split('      - name:', 1)[0]
        self.assertIn("if: success() && steps.publish.outputs.article_slug != ''", email)
        self.assertNotIn('env.ARTICLE_SLUG', email)
        self.assertIn('GENERATED_SLUG: ${{ steps.generate_article.outputs.article_slug }}', WORKFLOW)


if __name__ == '__main__':
    unittest.main()
