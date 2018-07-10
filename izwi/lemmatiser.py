# Lemmatisers
# Wordnet based lemmatiser for English

from nltk.stem.wordnet import WordNetLemmatizer
from nltk.stem import RegexpStemmer


class word_lemmatiser:
    def __init__(self, language):
        self.language = language
        if self.language == "eng":
            self.model = WordNetLemmatizer()
        elif self.language == "nso":
            self.model = RegexpStemmer('ng$', min=4)
        else:
            self.model = None
            
    def lemma(self, x):
        if self.language == "eng":
            return self.model.lemmatize(x[0])
        elif self.language == "nso":
            return self.model.stem(x[0].lower())
        elif self.language == "zul":
            return x[2]
        else:
            return x[0]

    def identity(self, word):
        return word

class lemmatiser:
    def __init__(self, language):
        self.language = language
        self.word_lemmatiser = word_lemmatiser(self.language)
    
    def word_lemma(self, word):
        return self.word_lemmatiser.lemma(word)

    def phrase_lemma(self, phrase, headword_index):
        lemmas = [x[0] for x in phrase]
        lemmas[headword_index] = self.word_lemmatiser.lemma(phrase[headword_index])
        value = u" ".join(lemmas)
        return value

    def word_by_word_lemma(self, phrase):
        lemmas = [self.word_lemmatiser.lemma(x) for x in phrase]
        value = u" ".join(lemmas)
        return value

    def word_by_word_lemma_list(self, phrase):
        lemmas = [self.word_lemmatiser.lemma(x) for x in phrase]
        return lemmas
        
