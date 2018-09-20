from jupyter_translate import *
import unittest
import markdown


class TestJupyterTranslate(unittest.TestCase):

    def setUp(self):
        with open('bing.key', 'r') as f:
            self.key = f.read().strip()

    def test_translate(self):
        bt = BingTranslator(self.key)
        bt.load_cache()
        t = bt.translate(u'Hello!')
        print(t)
        bt.save_cache()

    def test_markdown(self):
        t = u'''Hello $s + 1$.'''
        md = markdown.Markdown(extensions=[MathExtension()])
        html = md.convert(t)
        md.reset()
        print(html)
        self.assertRegex(html, r".*Hello.*<math.*>.*s \+ 1.*</math>.*")

    def test_markdown_translate(self):
        bt = BingTranslator(self.key)
        bt.load_cache()
        mt = MarkdownTranslator(bt)
        t = u'''
- Hello $s + 1$.
- THis is a pen.

1. Go to school.
2. Happy holiday.
'''
        t = mt.translate(t, from_lang="en", to_lang='ja')
        print(t)
        bt.save_cache()

    def test_array(self):
        bt = BingTranslator(self.key)
        category = None
        res = bt.get_translations_array(['Hello!', 'This is a world.', 'I have a pen.', 'I use deep learning.'],
                                category=category)
        for x in res:
            print(x)

    def test_add(self):
        bt = BingTranslator(self.key)
        category = None
        res = bt.add_translation('I use deep learning.', u'私は深層学習を使います。',
                                category=category)
        #for x in res:
        #    print(x)


if __name__ == '__main__':
    unittest.main()