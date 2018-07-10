from nltk.corpus import stopwords
from nltk import wordpunct_tokenize


# A guideline of maximum length to consider to avoid pathological performance
# on very large documents
MAX_LENGTH = 10000


def language_proba(text):
    words = wordpunct_tokenize(text.lower())
    proba = {}
    matches = 0
    for language in stopwords._fileids:
        proba[language] = len(set(words) & set(stopwords.words(language)))
    return proba

def most_probable_language(text):
    probs = language_proba(text)
    return sorted(probs, key=probs.get, reverse=True)[0]

def majority_vote(LanguageVotes):
    import itertools
    import operator
    SList = sorted((x, i) for i, x in enumerate(LanguageVotes))
    mylanguages = itertools.groupby(SList, key=operator.itemgetter(0))

    def _sortingfunc (g):
        item, iterable = g
        count = 0
        min_index = len(LanguageVotes)
        for myitem, myindex in iterable:
            count += 1
            min_index = min(min_index, myindex)
        return count, -min_index

    return max(mylanguages, key=_sortingfunc)[0]


from nltk.corpus import crubadan
# performance hack: make it only support the given languages, otherwise it is
# unusably slow. It relies on '_' prefixed variables for now.
_supported = set([
    'af',
    'en',
    'nr',
    'nso',
    'ss',
    'st',
    'tn',
    'ts',
    've',
    'xh',
    'zu',
])
_old = crubadan._lang_mapping_data
_new_mapping_data = [row for row in _old if row[0] in _supported]
crubadan._lang_mapping_data = _new_mapping_data


from nltk.classify.textcat import TextCat
_tc = TextCat()
def most_probable_language(text):
    if not text.strip():
        return ""
    return _tc.guess_language(text[:MAX_LENGTH])


if __name__ == '__main__':
    # brief way to test our detection: read plain text files from the given
    # filenames and prints out the detected language
    import sys
    for f in sys.argv[1:]:
        print f, most_probable_language(open(f).read().decode('utf-8'))
