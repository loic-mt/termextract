#from izwi import database
from nltk.translate.gale_church import align_blocks
#from izwi.aligner import single_alignments_to_sequence_pairs

import logging
import sys
import re

from nltk.translate.api import AlignedSent

# SENTENCE ALIGNER
# the  nltk.align.gale_church implementation is based on text length only
# default values of priors can and should be changed
# for instance, it might be that the sentence legnth ratio of en/zu will differ from the ratio for en/fr
class sentenceAligner(object):
    def __init__(self):
        pass

    def align(self):
        logging.debug("ALIGNING")

    def getSentencePairs(self):
        return []

def bitext_from_documents(db, doc1, lang1, doc2, lang2):
    myDB = database.izwiDB(db, "")
    doc1id = myDB.get_docid(doc1, lang1)
    doc2id = myDB.get_docid(doc2, lang2)
    p_lengths1 = myDB.get_all_paragraph_lengths(doc1id)
    p_lengths2 = myDB.get_all_paragraph_lengths(doc2id)
    bitext = []
    for para1, para2 in align_blocks([x[1] for x in p_lengths1],
                                     [x[1] for x in p_lengths2]):
        # convert from index in the list above to the ID in the DB:
        para1 = p_lengths1[para1][0]
        para2 = p_lengths2[para2][0]
        s_lengths1 = myDB.get_sentence_lengths(doc1id, para1)
        s_lengths2 = myDB.get_sentence_lengths(doc2id, para2)
        for s1, s2 in align_blocks([x[1] for x in s_lengths1],
                                   [x[1] for x in s_lengths2]):
            s1 = s_lengths1[s1][0]
            s2 = s_lengths2[s2][0]
            bitext.append((s1, s2))

    return [AlignedSent(s.split(), t.split()) for (s,t) in myDB.get_sentence_pairs(bitext)]

def count_sentence_lengths(file,lengths):
    with open(file,'r') as f:
        for line in f:
            line = line.rstrip()
            line = re.sub(" ","",line)
            lengths.append(len(line))


# takes two one-segment-per-line files as input
if __name__ == '__main__':
    srclengths = []
    tgtlengths = []
    count_sentence_lengths(sys.argv[1],srclengths)
    count_sentence_lengths(sys.argv[2],tgtlengths)
    sent_alignments = align_blocks(srclengths,tgtlengths)
    for sp in sent_alignments:
        print sp
