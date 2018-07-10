from izwi.sentencealigner import sentenceAligner
from izwi.sentencealigner import bitext_from_documents
from nltk.translate.api import AlignedSent
from nltk.translate.gale_church import align_blocks
from izwi.wordaligner import bidirectWordAligner
from nltk.translate.phrase_based import phrase_extraction
from nltk.translate.gdfa import grow_diag_final_and
from izwi.documentfilter import documentFilter,paragraph,sentence
from izwi.bitext_filter import sentence_level_bitext_filter
from izwi.postagger import pos_tagger
from izwi.lemmatiser import lemmatiser
import database
import logging
import sys
import re
import timeout

# doc align file > document_level_bitext > paragraph_level_bitext > sentence_level_bitext > word alignment > phrase table

debug = False

def single_alignments_to_sequence_pairs(aligninfo):
    seq_pairs = []
    src_seen = set([])
    tgt_seen = set([])
    cur_src = []
    cur_tgt = []
    for a in aligninfo:
        if (a[0] not in src_seen) and (a[1] not in tgt_seen):
            if cur_src and cur_tgt:
                seq_pairs.append((cur_src,cur_tgt))
            cur_src=[a[0]]
            cur_tgt=[a[1]]
        else:
            if a[0] not in cur_src:
                cur_src.append(a[0])
            if a[1] not in cur_tgt:
                cur_tgt.append(a[1])
        src_seen.add(a[0])
        tgt_seen.add(a[1])
    seq_pairs.append((cur_src,cur_tgt))
    return seq_pairs

# document_level_bitext
class document_level_bitext(object):
    def __init__(self,src_tuple,tgt_tuple):
        logging.debug("Creating document level bitext from document pair")
        myfilter = documentFilter()
        self.src_doc = myfilter.extract_doc(src_tuple[0], None)
        self.src_lang = src_tuple[1]
        self.tgt_doc = myfilter.extract_doc(tgt_tuple[0], None)
        self.tgt_lang = tgt_tuple[1]
        nbparsrc =  self.src_doc.nb_paragraphs()
        if debug:
            print str(nbparsrc) + " PAR IN SRC"
        nbpartgt =  self.tgt_doc.nb_paragraphs()
        if debug:
            print str(nbpartgt) + " PAR IN TGT"

# paragraph_level_bitext
class paragraph_level_bitext(object):
    def __init__(self,doc_level_bitext):
        logging.debug("Creating paragraph level bitext from document pair")
        src_lengths = doc_level_bitext.src_doc.get_paragraph_lengths()
        tgt_lengths = doc_level_bitext.tgt_doc.get_paragraph_lengths()
        par_alignments = single_alignments_to_sequence_pairs(align_blocks(src_lengths, tgt_lengths))
        self.bi_par = []
        for a in par_alignments:
            if debug:
                print "my par align = "+str(a)
            new_src_par = doc_level_bitext.src_doc.paragraphs[a[0][0]]
            #print "current number of sentences in new src par = "+str(len(new_src_par.sentences))
            for i in range(1,len(a[0])):
                new_src_par += doc_level_bitext.src_doc.paragraphs[a[0][i]]
                
            new_tgt_par = doc_level_bitext.tgt_doc.paragraphs[a[1][0]]
            for i in range(1,len(a[1])):
                new_tgt_par += doc_level_bitext.tgt_doc.paragraphs[a[1][i]]
            self.bi_par.append((new_src_par,new_tgt_par))
        logging.info("%d paragraph alignments", len(self.bi_par))

# sentence_level_bitext
class sentence_level_bitext(object):
    def __init__(self,par_level_bitext, filterlength=False):
        logging.debug("Creating sent level bitext from document pair")
        self.bi_sent = []
        if par_level_bitext:
            for bp in par_level_bitext.bi_par:
                src_lengths = bp[0].get_sentence_lengths()
                tgt_lengths = bp[1].get_sentence_lengths()
                if debug:
                    print "Align sentences : "+str(src_lengths)+" "+str(tgt_lengths)
                sent_alignments = single_alignments_to_sequence_pairs(align_blocks(src_lengths, tgt_lengths))
                for a in sent_alignments:
                    logging.debug("SENT ALIGN a="+str(a))
                    # TODO: the following test on lenghts of a[0] and a[1] was added
                    # after a crash on aligning ABET eng-zul
                    # possible BUG hiding there
                    if len(a[0]) and len(a[1]):
                        #if True:
                        new_src_sent = bp[0].sentences[a[0][0]]
                        for i in range(1,len(a[0])):
                            new_src_sent += bp[0].sentences[a[0][i]]
                        new_tgt_sent = bp[1].sentences[a[1][0]]
                        for i in range(1,len(a[1])):
                            new_tgt_sent += bp[1].sentences[a[1][i]]
                        if filterlength and (new_src_sent.token_length() > 30 or new_tgt_sent.token_length() > 30):
                            continue
                        self.bi_sent.append((new_src_sent,new_tgt_sent))
            logging.info("%d sentence alignments", len(self.bi_sent))

    def get_bitext(self):
        bitext = []
        for bs in self.bi_sent:
            bitext.append(AlignedSent(bs[0].tokens,bs[1].tokens))
        return bitext

    def get_inverted_bitext(self):
        bitext = []
        for bs in self.bi_sent:
            bitext.append(AlignedSent(bs[1].tokens,bs[0].tokens))
        return bitext

    def __add__(self, other_sbt):
        for bs in other_sbt.bi_sent:
            self.bi_sent.append(bs)
        return self

    def add_sentence_pair(self, sp):
        self.bi_sent.append(sp)
    
    def get_length(self):
        return len(self.bi_sent)

    def dump(self):
        for bs in self.bi_sent:
            print bs[0].text.encode('utf-8')+"\t"+bs[1].text.encode('utf-8')
            #print u' '.join(bs[0].tokens).encode('utf-8')+"\t"+u' '.join(bs[1].tokens).encode('utf-8')

# MAIN ALIGNER
# takes a list of aligned (document,language) pairs
# outputs a list of bilingual terms (or stores them in DB)

class izwiAligner(object):
    def __init__(self, thisDB, docalign_file, wa_model_filestem, dump_bitext=False, verbose=False):
        self.db = database.izwiDB(thisDB, None)
        self.document_alignments = []
        self.load_document_alignments(docalign_file)
        self.wa_model_filestem = wa_model_filestem
        self.dump_bitext = dump_bitext
        self.verbose = verbose

    def load_document_alignments(self, filename):
        with open(filename,'r') as f:
            for line in f:
                line = line.rstrip()
                chunks = re.split("\t",line)
                msrc = re.match(r"\(\'(.*)\',(\w+)\)", chunks[0])
                srctuple = (msrc.group(1),msrc.group(2))
                mtgt = re.match(r"\(\'(.*)\',(\w+)\)", chunks[1])
                tgttuple = (mtgt.group(1),mtgt.group(2))
                align_tuple = (srctuple,tgttuple)
                self.document_alignments.append(align_tuple)

    def apply_offset(self,phrase,offset):
        new_phrase = (phrase[0]+offset,phrase[1]-1+offset)
        return new_phrase

    @timeout.timeout(5)
    def extract_phrase_table(self,bisent,alignment):
        PT = []
        srctext = bisent[0].tokenized_sentence()
        trgtext = bisent[1].tokenized_sentence()
        # print "EPT:SRC:"+srctext.encode('utf-8')
        # print "EPT:TGT:"+trgtext.encode('utf-8')
        # print "EPT:INPUT_ALIGNMENT:"+str(alignment)
        phrase_pairs = phrase_extraction(srctext, trgtext, alignment)
        # if True:
        #     print str(len(phrase_pairs))+" pairs to add for this sentence"

        #print "PHRASE PAIRS: "+str(phrase_pairs)
        for p in phrase_pairs:
            PT.append((self.apply_offset(p[0],bisent[0].offset),self.apply_offset(p[1],bisent[1].offset)))
        return PT


    @timeout.timeout(5)        
    def gdfa_wrapper(self, srclen, tgtlen, e2f_str, f2e_str):
        return grow_diag_final_and(srclen, tgtlen, e2f_str, f2e_str)

    def get_sent_bitext(self, docpair, filter_length=False, this_filter=None):
        logging.debug("DOCUMENT LEVEL ALIGNMENT")
        doc_bitext = document_level_bitext(docpair[0],docpair[1])
        logging.debug("PARAGRAPH LEVEL ALIGNMENT")
        par_bitext = paragraph_level_bitext(doc_bitext)
        logging.debug("SENTENCE LEVEL ALIGNMENT")
        sent_bitext = sentence_level_bitext(par_bitext, filter_length)
        if this_filter:
            logging.info("APPLYING BITEXT FILTER")
            this_filter.apply(sent_bitext)
        return sent_bitext
        
    def get_phrase_table(self, mybwa, sent_bitext, src, tgt):
        # align each document at sentence, then word level
        # clearly not optimal since word alignment would benefit from training on all the new data
        # but that's a beginning
        
        if debug:
            for b in sent_bitext.bi_sent:
                print str(b[0].offset)+"\t"+str(b[1].offset)
        
        # from there, we can take the symmetrized alignments instead of a unidirectionnal one
        PT = []
        logging.debug("PHRASE LEVEL ALIGNMENT")
        sentence_count = 0

        bitext = sent_bitext.get_bitext()
        for bisent, sentpair in zip(sent_bitext.bi_sent, bitext):

            #print "SENTPAIR ="+str(sentpair)

            try:
                aligninfo = mybwa.wamodel.align(sentpair)
            except Exception as e:
                logging.warning("FAILED WORD ALIGNMENT: "+str(e)+" FOR SENTENCE PAIR"+str(sentpair))
                continue
            inv_sentpair = AlignedSent(sentpair.mots,sentpair.words)    
            try:
                raligninfo = mybwa.reverse_wamodel.align(inv_sentpair)
            except Exception as e:
                logging.warning("FAILED REVERSE WORD ALIGNMENT: "+str(e)+" FOR SENTENCE PAIR"+str(inv_sentpair))
                continue

            #print "aligninfo::"+str(aligninfo.src_sentence)+"\t"+str(aligninfo.trg_sentence)+"\t"+str(aligninfo.alignment)
            #print "raligninfo::"+str(raligninfo.src_sentence)+"\t"+str(raligninfo.trg_sentence)+"\t"+str(raligninfo.alignment)
            
            f2e = ["%d-%d" % x for x in enumerate(aligninfo.alignment)]
            e2f = ["%d-%d" % x for x in enumerate(raligninfo.alignment)]

            srclen = len(aligninfo.src_sentence)
            tgtlen = len(aligninfo.trg_sentence)
            f2e_str = ' '.join(f2e)
            e2f_str = ' '.join(e2f)

            logging.debug("SRC LEN : "+str(srclen))
            logging.debug("TGT LEN : "+str(tgtlen))
            logging.debug("WORD ALIGNMENT E2F : "+e2f_str)
            logging.debug("WORD ALIGNMENT F2E : "+f2e_str)
            
            try:
                # conventions are inverted
                gdfa = self.gdfa_wrapper(tgtlen, srclen, f2e_str, e2f_str)
                logging.debug("BISENT ="+bisent[0].text.encode('utf-8')+" --> "+bisent[1].text.encode('utf-8')+" ::: GDFA: srclen="+str(srclen)+", tgtlen="+str(tgtlen)+", RESULT = "+str(gdfa))
            except timeout.TimeoutError:
                logging.warning("TIMEOUT in GDFA")
                logging.debug("GDFA ARGUMENTS WERE: srclen="+str(srclen)+", tgtlen="+str(tgtlen)+" E2F="+e2f_str+" F2E="+f2e_str)
                continue
            alignment_without_null_word = set([])
            for i, j in gdfa:
                if i>0 and j>0:
                    alignment_without_null_word.add((i - 1, j - 1))
            try:
                PT.extend(self.extract_phrase_table(bisent, alignment_without_null_word))
            except timeout.TimeoutError:
                logging.warning("TIMEOUT in extract phrase table")
                continue
            sentence_count += 1
            
        # store in a dictionary of dictionaries...of set
        logging.debug("STORING TOKEN RANGE MAPPINGS")
        dictPT = {}
        for pp in PT:
            if pp[0] not in dictPT:
                dictPT[pp[0]] = set([])
            dictPT[pp[0]].add(pp[1])
        return dictPT

    def find_term_pairs(self, docpair, dictPT):
        src_doc_id = self.db.get_docid(docpair[0])
        tgt_doc_id = self.db.get_docid(docpair[1])

        docalign_id = self.db.add_document_alignment((src_doc_id, tgt_doc_id))
        # for each term in src document
        src_term_range = self.db.get_terms_in_document(docpair[0])
        tgt_term_range = self.db.get_terms_in_document(docpair[1])
        logging.debug(str(len(src_term_range))+" TERMS IN SRC DOCUMENT")
        logging.debug(str(len(tgt_term_range))+" TERMS IN TGT DOCUMENT")
        
        target_range_to_term = {}
        for tf in tgt_term_range:
            target_range_to_term[tf[1]] = tf[0]
        termpairfreq = {}
        for tf in src_term_range:
            if tf[1] in dictPT:
                target_ranges = dictPT[tf[1]]
                for tr in target_ranges:
                    if tr in target_range_to_term:
                        pair_tuple = (tf[0], target_range_to_term[tr])
                        if pair_tuple in termpairfreq:
                            termpairfreq[pair_tuple] += 1
                        else:
                            logging.debug("FOUND NEW TERM PAIR: "+str(pair_tuple))
                            termpairfreq[pair_tuple] = 1
        logging.info("STORING TERM PAIRS IN DB")
        for pair_tuple in termpairfreq:
            self.db.update_term_alignment_in_document_alignment(docalign_id, pair_tuple, termpairfreq[pair_tuple])
            if self.verbose:
                src_term = self.db.get_term_from_id(pair_tuple[0])
                tgt_term = self.db.get_term_from_id(pair_tuple[1])
                freq = termpairfreq[pair_tuple]
                output = u"%d\t%s\t%s" % (freq, src_term, tgt_term)
                logging.debug("TERM PAIR:\t"+output.encode('utf-8'))

    def process(self):
        docpair = self.document_alignments[0]
        src = docpair[0][1]
        tgt = docpair[1][1]

        logging.info("BUILDING CUMULATED BITEXT")
        logging.info("ADDING BI SENTENCES FROM DOCUMENT PAIR"+str(docpair))
        
        sbt_filter = sentence_level_bitext_filter(src, tgt, False, False)
        cumulated_sbt = self.get_sent_bitext(docpair, False, sbt_filter)
        individual_sbt = [cumulated_sbt]
        for i in range(1, len(self.document_alignments)):
            docpair = self.document_alignments[i]
            logging.info("ADDING BI SENTENCES FROM DOCUMENT PAIR"+str(docpair))
            # get phrase table
            sbt = self.get_sent_bitext(docpair, False, sbt_filter)
            cumulated_sbt += sbt
            individual_sbt.append(sbt)

        logging.debug("LENGTH OF CUMULATED BITEXT="+str(cumulated_sbt.get_length()))
        
        if self.dump_bitext:
            cumulated_sbt.dump()
            exit(1)
            
        # load models in both directions
        logging.debug("WORD LEVEL ALIGNMENT")
        mybwa = bidirectWordAligner(cumulated_sbt,
                                    src,
                                    tgt,
                                    self.wa_model_filestem)
        
        for docpair, sbt in zip(self.document_alignments, individual_sbt):
            logging.info("EXTRACTING PHRASE PAIRS IN DOC PAIR "+str(docpair))
            dictPT = self.get_phrase_table(mybwa, sbt, src, tgt)
            logging.info("FINDING TERM PAIRS IN DOC PAIR "+str(docpair))
            self.find_term_pairs(docpair, dictPT)
        self.db.conclude()

if __name__ == '__main__':
    # Basic test/demo. This assumes the files are already processed with the
    # results in tests.db, and it is run from the top-level directory of the
    # project (the directory containing "experiments".
    aligner = izwiAligner('experiments/management_principles/data/en-af-aligned',
                          'experiments/wordalignmodels/en-af')
    from izwi.wordaligner import wordAligner

    for (doc1, lang1), (doc2, lang2) in aligner.document_alignments:
        bitext = bitext_from_documents('test2.db', doc1, lang1, doc2, lang2)
        word_aligner = wordAligner(bitext, 5)
        # translation probabilities, alignment probabilities:
        ttablefile = aligner.wa_model_filestem + ".t.count"
        atablefile = aligner.wa_model_filestem + ".a.count"
        word_aligner.define_model_from_tables(ttablefile,atablefile)
        for sentpair in word_aligner.aligned_corpus:
            aligninfo = word_aligner.align(sentpair)
            # ... do something with aligninfo ...
