import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sync_indexes as sync
import seo_audit as audit
import generate_article as generator

MAIN = 'insurance-service-index-2025.html'
OLD = 'insurance-service-index-2025-disability-insurance.html'
BASE = sync.SITE_BASE + '/'


class IndexSyncTests(unittest.TestCase):
    def test_redirect_cleanup_and_repeat_runs(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp)
            (root / MAIN).write_text('<title>Main</title><link rel="canonical" href="' + BASE + MAIN + '">')
            (root / OLD).write_text('<META CONTENT="0; URL=' + BASE + MAIN + '" HTTP-EQUIV="Refresh">')
            (root / 'before.html').write_text('<title>Before</title>')
            (root / 'after.html').write_text('<title>After</title>')
            sitemap = root / 'sitemap.xml'
            sitemap.write_text('<urlset>' + ''.join('<url><loc>' + BASE + p + '</loc></url>' for p in ['before.html', OLD, 'after.html']) + '</urlset>')
            llms = root / 'llms.txt'
            llms.write_text('- Old: ' + BASE + OLD + '\n- Before: ' + BASE + 'before.html\n')
            pages = sync.collect_pages(root)
            initial = (sitemap.read_bytes(), llms.read_bytes())
            sync.sync_sitemap(sitemap, pages, root, '2026-10-23', True)
            sync.sync_llms(llms, [sync.page_url(p, root) for p in pages], root, True)
            self.assertEqual(initial, (sitemap.read_bytes(), llms.read_bytes()))
            for i in range(3):
                sync.sync_sitemap(sitemap, pages, root, '2026-10-23', False)
                sync.sync_llms(llms, [sync.page_url(p, root) for p in pages], root, False)
                audit.sync_sitemap(sitemap, pages, root, '2026-10-23')
                audit.sync_llms_txt(llms, [BASE + OLD, BASE + MAIN], root)
                generator.update_sitemap(sitemap, OLD[:-5], '2026-10-23')
                generator.update_llms_txt(llms, OLD[:-5], 'Old')
                urls = [e.text for e in ET.parse(sitemap).findall('.//loc')]
                self.assertEqual(set(urls), {BASE + MAIN, BASE + 'before.html', BASE + 'after.html'})
                self.assertEqual(len(urls), 3)
                self.assertIn(BASE + MAIN, llms.read_text())
                self.assertNotIn(BASE + OLD, llms.read_text())
                current = (sitemap.read_bytes(), llms.read_bytes())
                if i:
                    self.assertEqual(previous, current)
                previous = current
            alias = audit.audit_page(root / OLD, root)
            self.assertTrue(alias.noindex)
            self.assertEqual(alias.url, BASE + OLD)

    def test_audit_repairs_indexes_without_sync_first(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(tmp)
            (root / MAIN).write_text('<title>Main</title>')
            (root / OLD).write_text('<meta http-equiv="refresh" content="0; url=' + BASE + MAIN + '">')
            sitemap = root / 'sitemap.xml'
            sitemap.write_text('<urlset><url><loc>' + BASE + OLD + '</loc></url></urlset>')
            llms = root / 'llms.txt'
            llms.write_text('- Old: ' + BASE + OLD + '\n')
            added = audit.sync_sitemap(sitemap, list(root.glob('*.html')), root, '2026-10-23')
            audit.sync_llms_txt(llms, added, root)
            self.assertEqual([e.text for e in ET.parse(sitemap).findall('.//loc')], [BASE + MAIN])
            self.assertIn(BASE + MAIN, llms.read_text())
            self.assertNotIn(BASE + OLD, llms.read_text())
            # Cleanup must also work when no new sitemap URLs were added.
            llms.write_text('- Old: ' + BASE + OLD + '\n')
            audit.sync_llms_txt(llms, [], root)
            self.assertNotIn(BASE + OLD, llms.read_text())

    def test_repository_article_metadata(self):
        root = Path(__file__).resolve().parents[2]
        self.assertFalse(sync.has_redirect(root / MAIN))
        self.assertTrue(sync.has_redirect(root / OLD))
        self.assertNotIn(BASE + MAIN, sync.EXCLUDED_URLS)
        urls = {e.text for e in ET.parse(root / 'sitemap.xml').findall('.//{*}loc')}
        self.assertIn(BASE + MAIN, urls)
        self.assertNotIn(BASE + OLD, urls)

    def test_refresh_without_url_is_not_redirect(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'reload.html'
            p.write_text('<meta http-equiv="refresh" content="60">')
            self.assertFalse(sync.has_redirect(p))


if __name__ == '__main__':
    unittest.main()
