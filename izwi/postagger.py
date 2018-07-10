# Part-of-speech taggers
# NLTK standard for English
# Hunpos models for Northern Sotho

from os.path import join, dirname, pardir

import nltk
from nltk.tag import HunposTagger
from nltk.tag import MarmotTagger
from nltk.tag.stanford import StanfordPOSTagger

import logging
import subprocess

_MODEL_DIR = join(dirname(__file__), pardir, "experiments", "postagmodels")

class pos_tagger:
    def __init__(self, language, stanford=False):
       
        if not language:
            raise ValueError("No language specified for POS tagging")
        else:
             self._language = language
             
        if self._language == "eng" and stanford:
            self.model = StanfordPOSTagger(r'english-bidirectional-distsim.tagger')
            self.tagger = self.model.tag
        elif self._language == "eng":
            try:
                # "new" nltk with slow default behaviour through high-level API
                from nltk.tag import PerceptronTagger
                self.model = PerceptronTagger()
                self.tagger = self.model.tag
            except ImportError:
                self.model = None
                self.tagger = nltk.pos_tag
        elif self._language == "afr":
            self.model = HunposTagger(join(_MODEL_DIR, "pos-tag-model.af"), encoding='utf-8')
            self.tagger = self.model.tag
        elif self._language == "nso":
            self.model = HunposTagger(join(_MODEL_DIR, "simple-pos-tag-model.nso"), encoding='utf-8')
            self.tagger = self.model.tag
        elif self._language == "zul":
            #self.model = MarmotTagger(encoding='utf-8')
            self.model = HunposTagger(join(_MODEL_DIR, "simple-pos-tag-model.zu"), encoding='utf-8')
            self.tagger = self.model.tag
        else:
            raise ValueError('Language "%s" not supported for POS tagging.\nSupply a 3 letter code form ISO-639.' % self._language)
    
    
    def tag(self, sentence):
        #return self.tagger(sentence)
        try:
            return self.tagger(sentence)
        except Exception:
            #self.__init__(self._language)
            return None
            
