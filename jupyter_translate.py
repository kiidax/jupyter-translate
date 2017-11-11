# -*- coding: utf-8 -*-

# Bing Translator

import os
import codecs
import json
import urllib
import requests
import xml.etree.ElementTree as ET

class BingTranslator:
    '''A class to translate plain texts or HTML texts from one language to another using Bing Translator API.'''

    def __init__(self, key, cache_fname='bing.cache'):
        self.bing_translator_key = key
        self.cache_fname = cache_fname
        self.cache = {}
        self.load_cache()

    def set_bing_translator_key(self, key):
        self.bing_translator_key = key

    def load_cache(self):
        if os.path.exists(self.cache_fname):
            with codecs.open(self.cache_fname, 'r', 'utf-8-sig') as f:
                self.cache = json.load(f)

    def save_cache(self):
        with codecs.open(self.cache_fname, 'w', 'utf-8-sig') as f:
            json.dump(self.cache, f)


    def translate(self, text, content_type='text/html', from_lang='en', to_lang='ja'):
        params = urllib.parse.urlencode({
            'text': text,
            'contentType': content_type,
            'from': from_lang,
            'to': to_lang
        })
        if params in self.cache:
            return self.cache[params]

        headers = {
            'Ocp-Apim-Subscription-Key': self.bing_translator_key,
            'Accept': 'application/json'
            }
        r = requests.get(
            'https://api.microsofttranslator.com/V2/Http.svc/Translate?' + params,
            headers=headers
            )
        try:
            root = ET.fromstring(r.text)
            res = root.text
        finally:
            r.close()

        self.cache[params] = res
        return res

    def translate_array(self, text_list, **config):
        return [
            self.translate(text, **config)
            for text in text_list
            ]

# Markdown

from markdown.inlinepatterns import Pattern
from markdown.util import etree
from markdown.extensions import Extension

class InlineMathPattern(Pattern):
    def handleMatch(self, m):
        el = etree.Element('math')
        el.set('class', 'notranslate')
        el.text = m.group(2)
        return el

class MathExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        inline_math = InlineMathPattern(r'\$([^$]+)\$')
        md.inlinePatterns.add('inlinemath', inline_math, '>emphasis2')

# Unmarkdown

import lxml.html

class Unmarkdown:

    def __init__(self):
        self.reset()

    def reset(self):
        self.list_type = None

    def new_block(self, s):
        if len(s) >= 1 and s[-1] != '\n':
            return s + '\n\n'
        elif len(s) >= 2 and s[-2:] != '\n\n':
            return s + '\n'
        else:
            return s

    def unmarkdown_elem(self, elem):
        s = ''
        if elem.text is not None:
            s += elem.text
        for child in elem:
            if child.tag == 'h1':
                s = self.new_block(s)
                s += '# %s' % (child.text,)
            elif child.tag == 'h2':
                s = self.new_block(s)
                s += '## %s' % (child.text,)
            elif child.tag == 'h3':
                s = self.new_block(s)
                s += '### %s' % (child.text,)
            elif child.tag == 'h4':
                s = self.new_block(s)
                s += '#### %s' % (child.text,)
            elif child.tag == 'p':
                s = self.new_block(s)
                s += self.unmarkdown_elem(child).strip()
            elif child.tag == 'blockquote':
                s = self.new_block(s)
                s += '>' + self.unmarkdown_elem(child).strip()
            elif child.tag == 'ul':
                self.list_type = '- '
                s = self.new_block(s)
                s += self.unmarkdown_elem(child).strip()
            elif child.tag == 'ol':
                self.list_type = 1
                s = self.new_block(s)
                s += self.unmarkdown_elem(child).strip()
            elif child.tag == 'li':
                s = self.new_block(s)
                if type(self.list_type) == str:
                    s += self.list_type + self.unmarkdown_elem(child).strip()
                elif type(self.list_type) == int:
                    s += str(self.list_type) + '. ' + self.unmarkdown_elem(child).strip()
                    self.list_type += 1
            elif child.tag == 'br':
                s = self.new_block(s)
            elif child.tag == 'pre':
                s = self.new_block(s)
                t = self.unmarkdown_elem(child)
                s += '\n'.join(['    %s' % (x,) for x in t.split('\n')])
            elif child.tag == 'strong':
                s += '**%s**' % (child.text,)
            elif child.tag == 'em':
                s += '*%s*' % (child.text,)
            elif child.tag == 'b':
                s += '**%s**' % (child.text,)
            elif child.tag == 'a':
                s += '[%s](%s)' % (child.text, child.attrib.get('href', ''))
            elif child.tag == 'code':
                s += '`%s`' % (child.text,)
            elif child.tag == 'img':
                s += '![%s](%s)' % (child.attrib['alt'], child.attrib['src'])
            elif child.tag == 'math':
                s += '$%s$' % (child.text,)
            else:
                raise Exception('Unsupported element %s' % (child.tag))
            if child.tail is not None:
                s += child.tail
        return s

    def convert(self, html):
        elem = lxml.html.fromstring(html)
        return self.unmarkdown_elem(elem)

# Markdown translator

import markdown

class MarkdownTranslator:
    
    def __init__(self, bing_translator):
        self._bing_translator = bing_translator
        self._markdown = markdown.Markdown(extensions=[MathExtension()])
        self._unmarkdown = Unmarkdown()

    def translate(self, text, **config):
        html = self.markdown(text)
        html = self._bing_translator.translate(text, content_type='text/html', **config)
        text = self.unmarkdown(html)
        return text

    def is_html(self, text):
        if '<' in text and '</' in text:
            ol = len([1 for x in text if x == '<'])
            if ol >= 3:
                cl = len([1 for x in text if x == '>'])
                if cl >= 3:
                    if ol - cl <= 2 or cl - ol <= 2:
                        return True
        return False

    def translate_array(self, text_list, **config):
        do_unmarkdown = [not self.is_html(text) for text in text_list]
        html_list = [self.markdown(text) for text in text_list]
        html_list = self._bing_translator.translate_array(html_list, content_type='text/html', **config)
        if False:
            text_list = [self.unmarkdown(html) for html in html_list]
        else:
            for i in range(len(html_list)):
                try:
                    if do_unmarkdown[i]:
                        text_list[i] = self.unmarkdown(html_list[i])
                    else:
                        text_list[i] = html_list[i]
                except Exception as ex:
                    print(text_list[i])
                    raise ex
        return text_list

    def markdown(self, text):
        self._markdown.reset()
        return self._markdown.convert(text)

    def unmarkdown(self, text):
        self._unmarkdown.reset()
        return self._unmarkdown.convert(text)

# Jupyter notebook translator

import json
import codecs
import re

class NotebookTranslator:

    def __init__(self, bing_translator):
        self.markdown_translator = MarkdownTranslator(bing_translator)

    def translate_file(self, infname, outfname=None, **config):
        if infname.endswith('.ipynb'):
            self.translate_file_notebook(infname, outfname, **config)
        elif infname.endswith('.md'):
            self.translate_file_markdown(infname, outfname, **config)

    def translate_file_notebook(self, infname, outfname=None, replace=False, from_lang='en', to_lang='ja', **config):
        if outfname is None:
            outfname = re.sub(r'\.ipynb', '_%s.ipynb' % (to_lang,), infname)
            if infname == outfname:
                raise Exception()
        with codecs.open(infname, 'r', 'utf-8-sig') as f:
            doc = json.load(f)
        self.translate_document(doc, replace=replace, from_lang=from_lang, to_lang=to_lang, **config)
        with codecs.open(outfname, 'w', 'utf-8') as f:
            json.dump(doc, f)

    def translate_file_markdown(self, infname, outfname=None, from_lang='en', to_lang='ja', **config):
        if outfname is None:
            outfname = re.sub(r'\.md', '_%s.md' % (to_lang,), infname)
            if infname == outfname:
                raise Exception()
        with codecs.open(infname, 'r', 'utf-8-sig') as f:
            text = f.read()
        text = self.markdown_translator.translate(text, **config)
        with codecs.open(outfname, 'w', 'utf-8') as f:
            f.write(text)

    def cell_to_markdown(self, cell):
        source = cell['source']
        if type(source) == str:
            return source
        elif type(source) == list:
            return ''.join(source)
        else:
            raise RuntimeException('Unexpected')

    def translate_document(self, doc, replace=False, **config):
        text_list = [self.cell_to_markdown(cell) for cell in doc['cells'] if cell['cell_type'] == 'markdown']
        text_list = self.markdown_translator.translate_array(text_list, **config)
        cells = []
        i = 0
        for cell in doc['cells']:
            if cell['cell_type'] == 'markdown':
                if not replace:
                    cells.append(cell)
                cell = json.loads(json.dumps(cell))
                cell['metadata']['original_source'] = cell['source']
                cell['source'] = text_list[i]
                cells.append(cell)
                i += 1
            else:
                cells.append(cell)
        doc['cells'] = cells

# Test

def test_translate():
    with open('bing.key', 'r') as f:
        key = f.read().strip()
    bt = BingTranslator(key)
    bt.load_cache()
    t = bt.translate(u'Hello!')
    print(t)
    bt.save_cache()

def test_markdown():
    t = u'''Hello $s + 1$.'''
    md = markdown.Markdown(extensions=[MathExtension()])
    html = md.convert(t)
    md.reset()
    print(html)

def test_markdown_translate():
    bt = BingTranslator(key)
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

def test():
    #test_translate()
    #test_markdown()
    test_markdown_translate()

# Main

import argparse

if __name__ == '__main__':
    import sys
    import glob

    parser = argparse.ArgumentParser(description='Translate Jupyter notebook using Bing Translator API.')
    parser.add_argument('-k', '--key', nargs='?', help='Bing Translator API secret key.', type=str)
    parser.add_argument('--key-file', nargs='?', help='Use Bing Translator API secret key from file.', type=str, default='bing.key')
    parser.add_argument('--from', nargs='?', dest='from_lang', help='Language to translate from.', type=str, default='en')
    parser.add_argument('--to', nargs='?', dest='to_lang', help='Language to translate to.', type=str, default='ja')
    parser.add_argument('inputs', nargs='+', help="Input files.")
    args = parser.parse_args()

    if args.key is not None:
        key = args.key
    elif args.key_file is not None:
        with open(args.key_file, 'r') as f:
            key = f.read().strip()
    fnames = args.inputs
    from_lang = args.from_lang
    to_lang = args.to_lang

    if False:
        test()
    else:
        bt = BingTranslator(key)
        bt.load_cache()
        nt = NotebookTranslator(bt)
        if len(fnames) == 1 and os.path.isdir(fnames[0]):
            print('Directory mode. Translating files under directory...')
            for fname in glob.glob(os.path.join(fnames[0], '*.ipynb')):
                if not fname.endswith('_%s.ipynb' % (to_lang,)):
                    print('Translating %s...' % (fname,))
                    nt.translate_file(fname)
                    bt.save_cache()
        else:
            for arg in sys.argv[1:]:
                for fname in glob.glob(arg):
                    print('Translating %s...' % (fname,))
                    nt.translate_file(fname)
                    bt.save_cache()
