import re
import sys
import operator
import codecs
from itertools import izip

from nltk.tokenize import word_tokenize


def record_vocab(freqmap, line):
    for w in word_tokenize(line):
        if w in freqmap:
            freqmap[w] += 1
        else:
            freqmap[w] = 1

def store_index(indexmap,freqmap):
    freqmap["UNK"] = 0
    sorted_voc = sorted(freqmap.items(), key=operator.itemgetter(1), reverse=True)
    countindex = 1
    for word in sorted_voc:
        #print word[0].encode("utf-8")+" >> "+str(countindex)
        indexmap[word[0]] = countindex
        countindex += 1

def numberized_sentence(line, index):
    return " ".join(str(index[word]) for word in word_tokenize(line))

def write_vocab_file(lang,index,freq):
    vocabfile = lang+".vcb"
    sorted_voc = sorted(index.items(), key=operator.itemgetter(1))
    with open(vocabfile,"w") as vf:
        for w in sorted_voc:
            vf.write("%d\t%s\t%d\n" % (w[1], w[0].encode("utf-8"), freq[w[0]]))

corpusstem = sys.argv[1]
src = sys.argv[2]
tgt = sys.argv[3]

srcfile = corpusstem+"."+src
tgtfile = corpusstem+"."+tgt
alignmentfile = corpusstem+".snt"

srcfreq = {}
tgtfreq = {}
srcfreq["UNK"] = 0
tgtfreq["UNK"] = 0

# record vocabularies
with codecs.open(srcfile, "r", encoding="utf-8") as srcfilehandler, \
     codecs.open(tgtfile, "r", encoding="utf-8") as tgtfilehandler:
    for srcline, tgtline in izip(srcfilehandler, tgtfilehandler):
        srcline = srcline.rstrip()
        tgtline = tgtline.rstrip()
        record_vocab(srcfreq,srcline)
        record_vocab(tgtfreq,tgtline)

srcindex = {}
tgtindex = {}

store_index(srcindex,srcfreq)
store_index(tgtindex,tgtfreq)

# print vocabularies
write_vocab_file(src,srcindex,srcfreq)
write_vocab_file(tgt,tgtindex,tgtfreq)

# print sentences
with codecs.open(srcfile, "r", encoding="utf-8") as srcfilehandler, \
     codecs.open(tgtfile, "r", encoding="utf-8") as tgtfilehandler, \
     open(alignmentfile, "w") as sntfile:
    for srcline, tgtline in izip(srcfilehandler, tgtfilehandler):
        srcline = srcline.rstrip()
        tgtline = tgtline.rstrip()
        sntfile.write("1\n")
        sntfile.write(numberized_sentence(srcline,srcindex)+"\n")
        sntfile.write(numberized_sentence(tgtline,tgtindex)+"\n")
