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


def epub_to_txt(fn, char_limit=999999):
    """preprocesse epub to .txt files for translation on deepl.com """
    counter = 1
    output_text = ""
    with zipfile.ZipFile(fn, 'r') as zin:
        for item in zin.namelist():
            if item.endswith('html'):
                text = zin.read(item)
                text = text.decode('utf-8')
                processed_text = process_html(text, 'chapter') #XXX typical gutenberg
                #processed_text = process_html(text)
                if len(processed_text) > char_limit:
                    raise Exception("%s has over %d characters" % (fn, char_limit) )
                if len(processed_text) + len(output_text) > char_limit:
                    with open('section%d.txt' % counter, 'w') as f:
                        sys.stderr.write('section%d.txt done\n' % counter)
                        f.write(output_text)
                        f.close()
                        output_text = processed_text
                        counter += 1
                else:
                    output_text += "\n" + processed_text
        with open('section%d.txt' % counter, 'w') as f:
            sys.stderr.write('section%d.txt done' % counter)
            f.write(output_text)
            f.close()


def process_html(html, container_class=None):
    """convert html into .txt with hashes for each para"""
    output = ""
    soup = BeautifulSoup(html, 'html.parser')
    if not container_class:
        top_containers = (soup.body, )
    else:
        top_containers = soup.find_all("div", {"class": container_class})
    for top_container in [x for x in top_containers if not isinstance(x, NavigableString)]:
        for child in [x for x in top_container.children if not isinstance(x, NavigableString)]:
            txt = "".join(child.findAll(text=True, recursive=True))
            txt = re.sub('\n', ' ', txt)
            key = generate_key(txt)
            section = txt + "\n" + key
            output += section
            output += DELIMITER
    return output


def bilang_html(html, lookups, container_class=None):
    """Add translated para to html"""
    soup = BeautifulSoup(html, 'html.parser')
    if not container_class:
        top_containers = (soup.body, )
    else:
        top_containers = soup.find_all("div", {"class": container_class})
    counter = 1
    inserts = []
    for top_container in [x for x in top_containers if not isinstance(x, NavigableString)]:
        for child in top_container.children:
            counter += 1
            if isinstance(child, NavigableString):
                continue
            txt = "".join(child.findAll(text=True, recursive=True))
            txt = re.sub('\n', ' ', txt)
            if not txt:
                continue
            key = generate_key(txt)
            copied = soup.new_tag(child.name)
            translated = soup.new_tag("i")
            try:
                translated.string = lookups[key]
            except Exception:
                sys.stderr.write("NOT FOUND: %s: %s" % (key, translated.string))
                continue
            copied.append(translated)
            inserts.insert(0, (counter, copied))
        for insert in inserts:
            top_container.insert(*insert)
    return soup.prettify()


def build_lookup(fn):
    """read .txt glossay into dict"""
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
    """generate bilingual bi.epub from source and glossary"""
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
                    #translated_text = bilang_html(text, lookups)
                    translated_text = bilang_html(text, lookups, 'chapter') #XXX typical gutenberg
                    zout.writestr(item, translated_text)
        sys.stderr.write('bi.epub done')
        zout.close()
    zin.close()


if __name__ == "__main__":
    args_list = sys.argv[1:]
    opts = "ht:b" #XXX add a, analyze, display top div class
    long_opts = ["help", "txt=", "bi"]
    args, vals = getopt.getopt(args_list, opts, long_opts)

    help_string = """\
CDB ebbok tools
---------------

Usage:
    {this_file} -h | --help                            Display this message
    {this_file} -t | --txt x.epub                      Generate pre-processed section[n].txt files for translation to glossary.txt
    {this_file} -b | --bi source.epub glossary.txt     Generate bilingual bi.epub from source and glossary
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
