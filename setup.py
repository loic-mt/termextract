#!/usr/bin/env python

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup

import sys
import re
main_py = open('izwi/__init__.py').read()
metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", main_py))

requires = [
        'nltk',
    'pdfminer',
    'python-docx',
    'numpy',
    'regex',
]


setup(name='Izwi',
      version=metadata['version'],
      author=metadata['author'],
      author_email='dugasl@unisa.ac.za',
      description='Izwi term extractor',
      packages=['izwi'],
      classifiers=[
          'Development Status :: 0 - Beta',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Scientific/Engineering',
      ],
      license="BSD",
      scripts=['scripts/izwi','scripts/termdb','scripts/truecaser', 'scripts/bitext_filter'],
      install_requires=requires,
      )

if ('install' in sys.argv) or ('develop' in sys.argv):
    import nltk
    print "Downloading stuff from NLTK"
    nltk.download('stopwords')
    nltk.download('punkt')
    nltk.download('maxent_treebank_pos_tagger')
    nltk.download('maxent_ne_chunker')
    nltk.download('words')
    nltk.download('crubadan') # for language identification
