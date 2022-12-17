#!/usr/bin/env python

import sys
import getopt
import zipfile
import tempfile
import os
import re
from hashlib import md5

from bs4 import BeautifulSoup, NavigableString, Tag
import copy


DELIMITER = "\n- - - - - - - - - - - - - - - - - - - -\n"

def generate_key(text):
    return '<' + md5(text.encode('utf-8')).hexdigest() + '>'

def process_zip(fn): #XXX unused
    #ebook = zipfile.ZipFile(fn, mode="r")

    tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(fn))
    os.close(tmpfd)

    # hideously unoptimised
    with zipfile.ZipFile(fn, 'r') as zin:
        with zipfile.ZipFile(tmpname, 'w') as zout:
            zout.comment = zin.comment # preserve the comment
            for item in zin.namelist():
                if item.endswith('html'):
                    print(item)
                    #decode issues
                    text = zin.read(item)
                    text = text.decode()
                    print(type(text))
                    preprocessed_text = add_hashes(text)
                    zout.writestr(item, preprocessed_text)
                else:
                    zout.writestr(item, zin.read(item))

    filename = "bi.epub"
    os.rename(tmpname, filename)


def add_hashes(html): #XXX unused
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.body
    for child in [x for x in body.children if not isinstance(x, NavigableString)]:
        txt = "".join(child.findAll(text=True, recursive=True))
        key =  key = generate_key(txt)
        child.append(key)
    return soup.prettify()


def epub_to_txt(fn, char_limit=999999):
    counter = 1
    output_text = ""
    with zipfile.ZipFile(fn, 'r') as zin:
        for item in zin.namelist():
            if item.endswith('html'):
                #decode issues
                text = zin.read(item)
                text = text.decode('utf-8')
                processed_text = process_html(text)
                if len(processed_text) > char_limit:
                    raise Exception("%s has over %d characters" % (fn, char_limit) )
                if len(processed_text) + len(output_text) > char_limit:
                    with open('section%d.txt' % counter, 'w') as f:
                        f.write(output_text)
                        f.close()
                        output_text = processed_text
                        counter += 1
                else:
                    output_text += "\n" + processed_text
        with open('section%d.txt' % counter, 'w') as f:
            f.write(output_text)
            f.close()


def process_html(html):
    output = ""
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.body
    for child in [x for x in body.children if not isinstance(x, NavigableString)]:
        txt = "".join(child.findAll(text=True, recursive=True))
        txt = re.sub('\n', ' ', txt)
        key = generate_key(txt)
        section = txt + "\n" + key
        output += section
        output += DELIMITER
    return output


def bilang_html(html, lookups):
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.body
    counter = 1
    inserts = []
    for child in body.children:
        counter += 1
        if isinstance(child, NavigableString):
            continue
        txt = "".join(child.findAll(text=True, recursive=True))
        txt = re.sub('\n', ' ', txt)
        if not txt:
            continue
        key = generate_key(txt)
        #XXX make italic, add spacing
        copied = soup.new_tag(child.name)
        translated = soup.new_tag("i") #XXX add classes
        #translated = copy.copy(child)
        try:
          translated.string = lookups[key]
        except Exception:
            print("NOT FOUND: %s: %s" % (key, translated.string))
            continue
        copied.append(translated)
        inserts.insert(0, (counter, copied))
    for insert in inserts:
        body.insert(insert[0], insert[1])
        #XXX
        #body.insert(*insert)
    return soup.prettify()


def build_lookup(fn):
    f = open(fn, "r")
    text = f.read()
    f.close()
    lookup = {}
    sections = text.split(DELIMITER)
    for section in sections:
        lines = section.split('\n')
        key =lines[-1]
        content = '\n'.join(lines[:-1])
        lookup[key] = content
    return lookup


def build_bilang(fn, lookup_fn):
    lookups = build_lookup(lookup_fn)
    counter = 1
    with zipfile.ZipFile(fn, 'r') as zin:
        with zipfile.ZipFile('bi.epub', 'w') as zout:
            for item in zin.namelist():
                if not item.endswith('html'):
                    zout.writestr(item, zin.read(item))
                else:
                    text = zin.read(item)
                    text = text.decode()
                    translated_text = bilang_html(text, lookups)
                    zout.writestr(item, translated_text)


if __name__ == "__main__":
    args_list = sys.argv[1:]
    opts = "ht:b"
    long_opts = ["help", "txt=", "bi"]
    args, vals = getopt.getopt(args_list, opts, long_opts)

    help_string = """\
CDB ebbok tools
---------------

Usage:
    {this_file} -h | --help                            Display this message
    {this_file} -t | --txt x.epub                      Generate pre-processed section[n].txt files for translation
    {this_file} -b | --bi source.epub glossay.txt      Generate bilingual bi.epub from source and glossary
"""
    for arg, val in args:
        if arg in ('-t', '--txt'):
            fn = val
            epub_to_txt(fn)
            sys.exit(0)
        if arg in ('-b', '--bi'):
            source = vals[0]
            glossary = vals[1]
            build_bilang(source, glossary)
            sys.exit(0)
    sys.exit(help_string.format(this_file=sys.argv[0]))
