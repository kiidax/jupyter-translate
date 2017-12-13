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
            'Accept': 'application/xml'
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

    def translate_array_safe(self, text_list, **config):
        req = []
        res = []
        c = 0
        for text in text_list:
            if c + len(text) > 10240:
                if len(req) == 0:
                    raise Exception('The text to translate is too long. %d characters.' % len(text))
                res.extend(self.translate_array(req, **config))
                req = []
                c = 0
            req.append(text)
            c += len(text)
        if len(req) > 0:
            res.extend(self.translate_array(req, **config))
        return res

    def translate_array(self, text_list, **config):
        url = 'https://api.microsofttranslator.com/V2/Http.svc/TranslateArray'
        headers = {
            'Ocp-Apim-Subscription-Key': self.bing_translator_key,
            'Content-Type': 'application/xml'
            }
        root = ET.Element('TranslateArrayRequest')
        self._add_translate_request(root, text_list, **config)
        data = ET.tostring(root)
        r = requests.post(url, headers=headers, data=data)
        try:
            r.raise_for_status()
            root = ET.fromstring(r.text)
        finally:
            r.close()
        nsmap = {
            's': 'http://schemas.datacontract.org/2004/07/Microsoft.MT.Web.Service.V2'
            }

        res = [
            elem.text
            for elem in root.findall('.//s:TranslateArrayResponse/s:TranslatedText', namespaces=nsmap)
            ]

        return res

    def add_translation(
        self, original_text, translated_text, user, content_type='text/html', from_lang='en', to_lang='ja',
        category=None, rating=None):

        params = {
            'originalText': original_text,
            'translatedText': translated_text,
            'contentType': content_type,
            'category': category,
            'rating': rating,
            'user': user,
            'from': from_lang,
            'to': to_lang
        }
        keys = [k for k, v in params.items() if v is None]
        for k in keys:
            del params[k]

        params = urllib.parse.urlencode(params)

        headers = {
            'Ocp-Apim-Subscription-Key': self.bing_translator_key,
            'Accept': 'application/xml'
            }
        r = requests.get(
            'https://api.microsofttranslator.com/V2/Http.svc/AddTranslation?' + params,
            headers=headers
            )
        try:
            #root = ET.fromstring(r.text)
            #res = root.text
            print(r.text)
            res = r.text
            print(r.status_code)
        finally:
            r.close()

        return res

    def get_translations_array(self, text_list, from_lang='en', to_lang='ja', category=None, content_type='text/html', **config):
        url = 'https://api.microsofttranslator.com/V2/Http.svc/GetTranslationsArray'
        headers = {
            'Ocp-Apim-Subscription-Key': self.bing_translator_key,
            'Content-Type': 'application/xml'
            }
        root = ET.Element('GetTranslationsArrayRequest')
        self._add_translate_request(root, text_list, from_lang, to_lang, category, content_type, max_translations=3)
        data = ET.tostring(root)
        r = requests.post(url, headers=headers, data=data)
        try:
            root = ET.fromstring(r.text)
        finally:
            r.close()
        nsmap = {
            's': 'http://schemas.datacontract.org/2004/07/Microsoft.MT.Web.Service.V2'
            }

        # TODO
        res = [
            elem.text
            for elem in root.findall('.//s:TranslateArrayResponse/s:TranslatedText', namespaces=nsmap)
            ]

        return res

    def _add_translate_request(self, root, text_list, from_lang, to_lang, category=None, content_type=None, max_translations=None):
        ET.SubElement(root, 'AppId')
        child = ET.SubElement(root, 'From')
        child.text = from_lang
        options_elem = ET.SubElement(root, 'Options')
        if category is not None:
            category_elem = ET.SubElement(options_elem, '{http://schemas.datacontract.org/2004/07/Microsoft.MT.Web.Service.V2}Category')
            category_elem.text = category
        if content_type is not None:
            content_type_elem = ET.SubElement(options_elem, '{http://schemas.datacontract.org/2004/07/Microsoft.MT.Web.Service.V2}ContentType')
            content_type_elem.text = content_type
        texts_elem = ET.SubElement(root, 'Texts')
        for text in text_list:
            string_elem = ET.SubElement(texts_elem, '{http://schemas.microsoft.com/2003/10/Serialization/Arrays}string')
            string_elem.text = text
        to_elem = ET.SubElement(root, 'To')
        to_elem.text = to_lang
        if max_translations is not None:
            max_trans_elem = ET.SubElement(root, 'MaxTranslations')
            max_trans_elem.text = str(max_translations)

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

    def unmarkdown_elem(self, elem, s):
        if elem.tag == 'h1':
            s = self.new_block(s)
            s += '# %s' % (elem.text,)
        elif elem.tag == 'h2':
            s = self.new_block(s)
            s += '## %s' % (elem.text,)
        elif elem.tag == 'h3':
            s = self.new_block(s)
            s += '### %s' % (elem.text,)
        elif elem.tag == 'h4':
            s = self.new_block(s)
            s += '#### %s' % (elem.text,)
        elif elem.tag == 'p' or elem.tag == 'div':
            s = self.new_block(s)
            s += self.unmarkdown_elem_list(elem).strip()
        elif elem.tag == 'blockquote':
            s = self.new_block(s)
            s += '>' + self.unmarkdown_elem_list(elem).strip()
        elif elem.tag == 'ul':
            self.list_type = '- '
            s = self.new_block(s)
            s += self.unmarkdown_elem_list(elem).strip()
        elif elem.tag == 'ol':
            self.list_type = 1
            s = self.new_block(s)
            s += self.unmarkdown_elem_list(elem).strip()
        elif elem.tag == 'li':
            s = self.new_block(s)
            if type(self.list_type) == str:
                s += self.list_type + self.unmarkdown_elem_list(elem).strip()
            elif type(self.list_type) == int:
                s += str(self.list_type) + '. ' + self.unmarkdown_elem_list(elem).strip()
                self.list_type += 1
        elif elem.tag == 'br':
            s = self.new_block(s)
        elif elem.tag == 'pre':
            s = self.new_block(s)
            t = self.unmarkdown_elem_list(elem)
            s += '\n'.join(['    %s' % (x,) for x in t.split('\n')])
        elif elem.tag == 'strong':
            s += '**%s**' % (elem.text,)
        elif elem.tag == 'em':
            s += '*%s*' % (elem.text,)
        elif elem.tag == 'b':
            s += '**%s**' % (elem.text,)
        elif elem.tag == 'a':
            s += '[%s](%s)' % (elem.text, elem.attrib.get('href', ''))
        elif elem.tag == 'code':
            s += '`%s`' % (elem.text,)
        elif elem.tag == 'img':
            s += '![%s](%s)' % (elem.attrib['alt'], elem.attrib['src'])
        elif elem.tag == 'math':
            s += '$%s$' % (elem.text,)
        else:
            raise Exception('Unsupported element %s' % (elem.tag))
        return s

    def unmarkdown_elem_list(self, elem):
        s = ''
        if elem.text is not None:
            s += elem.text
        for child in elem:
            s = self.unmarkdown_elem(child, s)
            if child.tail is not None:
                s += child.tail
        return s

    def convert(self, html):
        elem = lxml.html.fromstring(html)
        s = ''
        return self.unmarkdown_elem(elem, s)

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
        html_list = self._bing_translator.translate_array_safe(html_list, content_type='text/html', **config)
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
        self.translation_prefix = '_unchecked_'

    def translate_file(self, infname, outfname=None, output_dir=None, **config):
        if infname.endswith('.ipynb'):
            self.translate_file_notebook(infname, outfname, output_dir, **config)
        elif infname.endswith('.md'):
            self.translate_file_markdown(infname, outfname, output_dir, **config)

    def _make_outfname(self, infname, outfname, output_dir, to_lang, ext):
        if outfname is None:
            outfname = re.sub(r'\.%s' % (ext,), '_%s.%s' % (to_lang, ext), infname)
            if infname == outfname:
                raise Exception()
            if output_dir is not None:
                outfname = os.path.join(output_dir, os.path.basename(outfname))
        return outfname

    def translate_file_notebook(self, infname, outfname=None, output_dir=None, to_lang='ja', allow_update=False, allow_overwrite=False, **config):
        outfname = self._make_outfname(infname, outfname, output_dir, to_lang, 'ipynb')
        translation_dict = None
        if os.path.exists(outfname):
            if allow_update:
                translation_dict = self.get_translations_from_file(outfname)
            elif not allow_overwrite:
                raise Exception("Cannot overwrite file `%s'" % outfname)
        with codecs.open(infname, 'r', 'utf-8-sig') as f:
            doc = json.load(f)
        self.translate_document(doc, to_lang=to_lang, translation_dict=translation_dict, **config)
        with codecs.open(outfname, 'w', 'utf-8') as f:
            json.dump(doc, f)

    def translate_file_markdown(self, infname, outfname=None, output_dir=None, to_lang='ja', **config):
        outfname = self.make_outfname(infname, outfname, output_dir, to_lang, 'md')
        with codecs.open(infname, 'r', 'utf-8-sig') as f:
            text = f.read()
        text = self.markdown_translator.translate(text, to_lang=to_lang, **config)
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

    def cell_to_original_markdown(self, cell):
        metadata = cell.get('metadata')
        if metadata is None:
            return None
        source = metadata.get('original_source')
        if source is None:
            return None
        if type(source) == str:
            return source
        elif type(source) == list:
            return ''.join(source)
        else:
            raise RuntimeException('Unexpected')

    def translate_document(self, doc, replace=False, translation_dict=None, **config):
        if translation_dict is None:
            translation_dict = {}
        translation_list = [
            self.cell_to_markdown(cell)
            for cell in doc['cells']
            if cell['cell_type'] == 'markdown'
            ]
        translation_list = [
            (text, translation_dict.get(text))
            for text in translation_list
            ]
        untranslated_text = [
            text
            for text, translated_text in translation_list 
            if translated_text is None
            ]
        translated_text_list = self.markdown_translator.translate_array(untranslated_text, **config)
        j = 0
        for i in range(len(translation_list)):
            text, translated_text = translation_list[i]
            if translated_text is None:
                translation_list[i] = (text, self.translation_prefix + '\n\n' + translated_text_list[j])
                j += 1
        cells = []
        i = 0
        for cell in doc['cells']:
            if cell['cell_type'] == 'markdown':
                if not replace:
                    cells.append(cell)
                cell = json.loads(json.dumps(cell))
                cell['metadata']['original_source'] = cell['source']
                cell['source'] = translation_list[i][1]
                cells.append(cell)
                i += 1
            else:
                cells.append(cell)
        doc['cells'] = cells

    def get_translations_from_file(self, fname):
        with codecs.open(fname, 'r', 'utf-8-sig') as f:
            doc = json.load(f)
        return self.get_translations_from_doc(doc)

    def get_translations_from_doc(self, doc):
        translation_list = [
            (self.cell_to_original_markdown(cell), self.cell_to_markdown(cell))
            for cell in doc['cells']
            if cell['cell_type'] == 'markdown'
            ]
        return {
           k: v
           for k, v in translation_list
           if k is not None and not v.startswith(self.translation_prefix)
           }

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

def test_array():
    with open('bing.key', 'r') as f:
        key = f.read().strip()
    bt = BingTranslator(key)
    category = None
    res = bt.get_translations_array(['Hello!', 'This is a world.', 'I have a pen.', 'I use deep learning.'],
                             category=category)
    for x in res:
        print(x)

def test_add():
    with open('bing.key', 'r') as f:
        key = f.read().strip()
    bt = BingTranslator(key)
    category = None
    res = bt.add_translation('I use deep learning.', u'私は深層学習を使います。',
                             category=category)
    #for x in res:
    #    print(x)

def test():
    #test_translate()
    #test_markdown()
    #test_markdown_translate()
    test_add()
    test_array()

# Main

def main():

    import argparse
    import sys
    import glob

    parser = argparse.ArgumentParser(description='Translate Jupyter notebook using Bing Translator API.')
    parser.add_argument('--key', '-k', nargs='?', help='Bing Translator API secret key.', type=str)
    parser.add_argument('--key-file', nargs='?', help='Use Bing Translator API secret key from file.', type=str, default='bing.key')
    parser.add_argument('--from', nargs='?', dest='from_lang', help='Language to translate from.', type=str, default='en')
    parser.add_argument('--to', nargs='?', dest='to_lang', help='Language to translate to.', type=str, default='ja')
    parser.add_argument('--output-directory', '-d', nargs='?', dest='output_dir', help='Output directory', type=str, default=None)
    parser.add_argument('--preserve', '-p', dest='preserve', help='Preserve original texts.', default=False, action='store_true')
    parser.add_argument('--force', '-f', dest='allow_overwrite', help='Allow overwrite old files.', default=False, action='store_true')
    parser.add_argument('--update', '-u', dest='allow_update', help='Allow update files.', default=False, action='store_true')
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
    output_dir = args.output_dir
    preserve = args.preserve
    allow_update = args.allow_update
    allow_overwrite = args.allow_overwrite

    bt = BingTranslator(key)
    bt.load_cache()
    nt = NotebookTranslator(bt)
    if len(fnames) == 1 and os.path.isdir(fnames[0]):
        print(to_lang)
        print('Directory mode. Translating files under directory...')
        for fname in glob.glob(os.path.join(fnames[0], '*.ipynb')):
            if not fname.endswith('_%s.ipynb' % (to_lang,)):
                print('Translating %s...' % (fname,))
                nt.translate_file(
                    fname, from_lang=from_lang, to_lang=to_lang,
                    category='generalnn', allow_update=allow_update,
                    allow_overwrite=allow_overwrite,
                    output_dir=output_dir, replace=not preserve)
                bt.save_cache()
    else:
        for arg in fnames:
            found=False
            for fname in glob.glob(arg):
                print('Translating %s...' % (fname,))
                nt.translate_file(
                    fname, from_lang=from_lang, to_lang=to_lang,
                    category='generalnn', allow_update=allow_update,
                    allow_overwrite=allow_overwrite,
                    output_dir=output_dir, replace=not preserve)
                bt.save_cache()
                found=True
            if not found:
                raise Exception('Input file `%s\' not found.' % arg)

if __name__ == '__main__':
    import sys
    #sys.argv = r'a b c'.split()
    #sys.argv = r'a -p -d ..\CNTKja\Tutorials ..\CNTK\Tutorials'.split()
    #sys.argv = r'a -p -d ..\CNTKja\Tutorials ..\CNTK\Tutorials\CNTK_101_LogisticRegression.ipynb'.split()
    main()
    #test()
