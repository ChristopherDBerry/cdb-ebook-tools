#!/usr/bin/env python

import sys
import deepl
import zipfile
import tempfile
import os

#auth_key = "1a55a5f2-6f20-365f-e620-f0b06520a344:fx" #chrisdanielberry
#auth_key = "e91c5aea-81e4-b020-7c3c-dcc6638af3ad:fx" #chrisdberry
auth_key = "8a576ca1-0910-f6e2-718e-c51497d0db6a"  #chrisdberry premium

def process_zip(fn, lang, engine):
    #ebook = zipfile.ZipFile(fn, mode="r")

    tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(fn))
    os.close(tmpfd)

    # hideously unoptimised
    with zipfile.ZipFile(fn, 'r') as zin:
        with zipfile.ZipFile(tmpname, 'w') as zout:
            zout.comment = zin.comment # preserve the comment
            for item in zin.namelist():
                if item.startswith('OEBPS/') and item.endswith('.xhtml'):
                    print(item)
                    #decode issues
                    text = zin.read(item)
                    text = text.decode()
                    print(type(text))
                    translated_text = translate(text, lang, engine)
                    zout.writestr(item, translated_text)
                else:
                    zout.writestr(item, zin.read(item))

    filename = "translated_ebook.epub"
    os.rename(tmpname, filename)

def translate(text, lang, engine):
    if engine == "dev":
        return dev(text, lang)
    if engine == "deepl":
        return engine_deepl(text, lang)

def dev(text, target_lang="EN-US"):
    return text

def engine_deepl(source, target_lang="EN-US"):
    translator = deepl.Translator(auth_key)
    result = translator.translate_text(source,
        target_lang=target_lang ,
        split_sentences="nonewlines",
        preserve_formatting=True,
        tag_handling="xml")
    return result.text

if __name__ == "__main__":
    fn = sys.argv[1]
    print(fn)
    process_zip(fn, "EN-US", "deepl")
