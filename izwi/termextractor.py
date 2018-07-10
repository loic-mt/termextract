import logging
import re

import nltk
from nltk.tokenize.treebank import TreebankWordTokenizer

from designpatterns import Visitor
from izwi import cleaner
from izwi import ner
from izwi.postagger import pos_tagger
import truecaser
from lemmatiser import lemmatiser

debug = False


class term:
    def __init__(self, thislang, thispos, thisvalue, thisrange, thisheadword = ""):
        self.language = thislang
        self.pos = thispos
        self.string = thisvalue
        self.head = thisheadword
        self.trange = thisrange

    def __str__(self):
        return self.pos+"\t"+self.string

    def __unicode__(self):
        return u"%s\t%s\t%s" % (self.pos, self.string, self.head)

    def get_language(self):
        return self.language
    def get_pos(self):
        return self.pos
    def get_string(self):
        return self.string
    def get_t_range(self):
        return self.trange


def _get_username(email_address):
    return email_address[:email_address.find('@')]


# based on http://emailregex.com/
email_re = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")


class termExtractor(Visitor):
    def __init__(self, language, chunkrulefile,normalisemodel = None,truecaserfile = None):
        self.language = language
        self.pos_tagger = pos_tagger(language)
        with open (chunkrulefile, "r") as myfile:
            self.grammar = myfile.read()
        if (truecaserfile == None):
            self.truecaser = None
        else:
            self.truecaser = truecaser.truecaser()
            self.truecaser.load_model(truecaserfile)
        if normalisemodel:
            self.normalisemodel = True
        else:
            self.normalisemodel = False
        self.myner = ner.NERtagger(language)
        self.lemmatiser = lemmatiser(language)
        self.nbsentences = 0
        self.nbtokens = 0
        self.tokentypes = set([])
        self.reset()

    def reset(self):
        self.terms = []
        self.emails = []
        self.persons = set()
        self._sentences = []

    def stats(self):
        report = "NB SENTENCES="+str(self.nbsentences)+", NB TOKENS="+str(self.nbtokens)+", NB TOKEN TYPES="+str(len(self.tokentypes))
        return report

    def visit(self, thisDocument):
        logging.debug("TERM EXTRACTION STARTS...")
        # grammar to parse the sentence in order to find the NP
        cp = nltk.RegexpParser(self.grammar)
        # grammar to parse the NP in order to find the head word (hacky)

        # For each paragraph
        for par_number, par in enumerate(thisDocument.get_paragraphs()):
            # For each sentence
            for s in par.sentences:
                self.nbsentences += 1
                self.nbtokens += len(s.tokens)
                for t in s.tokens:
                    self.tokentypes.add(t)
                s_tokenized = s.tokenized_sentence().lower()
                #print "TOKENIZED: "+s_tokenized.encode("utf-8")+" WHILE TOKENS = "+str(s.tokens)
                #print "CHAR INDICES = "+str(s.char_indices)
                # lbound keeps track of the leftmost part of the string where
                # we might still want to look for the term in s_tokenized
                lbound = 0
                self.emails.extend(email_re.findall(s.text))
                self._sentences.append((par_number, s.text))
                if (self.truecaser):
                    # first truecase, then apply POS tagger
                    truecasedsentence = self.truecaser.truecase_alltokens(s.tokens)
                    tagged_sentence = self.pos_tagger.tag(truecasedsentence)
                    if not tagged_sentence:
                        logging.debug("POS TAGGER FAILED ON SENTENCE"+str(truecasedsentence))
                        continue
                    else:
                        logging.debug("POS TAGGER SUCCEEDED:"+str(tagged_sentence))
                    self.persons.update(self.myner.parse([tagged_sentence]))
                    sentence = tagged_sentence
                else:
                    # first tag, and do NER before lowercasing everything
                    tagged_sentence = self.pos_tagger.tag(s.tokens)
                    if not tagged_sentence:
                        logging.debug("POS TAGGER FAILED ON SENTENCE"+str(s.tokens))
                        continue
                    else:
                        logging.debug("POS TAGGER SUCCEEDED:"+str(tagged_sentence))

                    self.persons.update(x.lower() for x in self.myner.parse([tagged_sentence]))
                    sentence = [(w[0].lower(), w[1]) for w in tagged_sentence]

                result = cp.parse(sentence)
                logging.debug("CHUNK PARSING OF SENTENCE "+str(sentence)+" = "+str(result)+" TOK SENT="+s_tokenized.encode("utf-8"))

                for subtree in result.subtrees():

                    # We only keep NP phrases for now
                    if subtree.label() != 'NP':
                        continue

                    # Build surface form and find index of headword
                    headword = "?"
                    surface_words = []
                    index = 0
                    head_index = -1
                    for psubtree in subtree:
                        word = u" ".join(x[0] for x in psubtree.leaves())
                        surface_words.append(word)
                        if psubtree.label() == 'HEAD':
                            head_index = index
                        index += 1    
                      
                    surface_value = u" ".join(surface_words)
                    term_length = len(surface_value.split())
                    
                    # Looking for the token range.
                    # We only start looking from lbound, so that we handle
                    # duplicates correctly. We lowercase aggresively so that we
                    # are guaranteed to find it regardless of whether we have
                    # truecasing or not.
                    term_start = s_tokenized.find(surface_value.lower(), lbound)

                    if term_start == -1:
                        logging.debug("TERM "+surface_value.lower().encode("utf-8")+" START NOT FOUND IN "+s_tokenized.encode("utf-8"))
                        continue
                    else:
                        lbound = term_start + len(surface_value)
                        logging.debug("TERM "+surface_value.lower().encode("utf-8")+" START FOUND, ="+str(term_start)+", LBOUND ="+str(lbound))
                        
                    tok_range = s.offset_at_char_range(term_start, lbound + 1)
                    if not tok_range:
                        logging.debug("TERM "+surface_value+" TOK RANGE NOT FOUND")
                        continue
                    logging.debug("TERM OF LENGTH "+str(term_length)+": "+surface_value+" TOK RANGE="+str(tok_range))
                   
                    # Lemmatise term
                    lemmatised_words = []
                    local_offset = tok_range[0] - s.offset
                    logging.debug("LOCAL RANGE "+str(local_offset)+" - "+str(local_offset+term_length))
                    tagged_phrase = tagged_sentence[local_offset:(local_offset+term_length)]
                    logging.debug("TAGGED PHRASE: "+str(tagged_phrase))

                    if self.language == "eng":
                        value = self.lemmatiser.phrase_lemma(tagged_phrase, head_index)
                    else:
                        value = surface_value
                        #value = self.lemmatiser.word_by_word_lemma(tagged_phrase)

                    # Misc. rule-based filter
                    if value != surface_value:
                        logging.debug("LTERM "+surface_value+" LEMMATISED AS "+value)
                    if not cleaner.is_possible_term(value):
                        logging.debug("TERM "+value+" CLEANED OUT")
                        continue

                    # Normalization
                    value = cleaner.normalize(value, self.language)

                    # Store in list of extracted terms
                    newterm = term(self.language, "NP", value, tok_range, headword)
                    if debug:
                        print "ADDED TERM: %s (%d,%d)" % (
                            unicode(newterm).encode('utf-8'),
                            tok_range[0],
                            tok_range[1],
                        )
                    self.terms.append((newterm, surface_value))

    def get_terms(self):
        usernames = set(_get_username(x) for x in self.emails)
        entities = usernames.union(self.persons)
        return filter(lambda x: x[0].get_string() not in entities, self.terms)

    def get_sentences(self):
        return self._sentences
