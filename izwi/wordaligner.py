from nltk.translate.api import AlignedSent
from  nltk.translate.ibm_model import IBMModel
from  nltk.translate.ibm2 import IBMModel2
from  nltk.translate.ibm3 import IBMModel3
import nltk.translate.gdfa
import sys
import re
import codecs
from collections import defaultdict
import timeout
import logging

IBMModelType = 2
TRAINING_ITERATIONS = 10

# WORD ALIGNER
# will perform word alignment using one of these three methods
# 1) load apply a pre-trained model
# 2) train a model on the new parallel data itself
# 3) both: initialize with 1), then  perform 2)
#
# it will also merge alignment both ways with the standard grow-diag-and-final method
class wordAligner(object):
    def __init__(self,aligned_corpus,iterations):
        self.aligned_corpus = aligned_corpus
        self.iterations = iterations

    def train_model(self):
        if IBMModelType == 2:
            logging.info("TRAINING IBM MODEL2")
            self.model = IBMModel2(self.aligned_corpus,self.iterations)
        elif IBMModelType == 3:
            logging.info("TRAINING IBM MODEL3")
            self.model = IBMModel3(self.aligned_corpus,self.iterations)
        else:
            exit(1)
            
    def define_model_from_tables(self,ttablefile,atablefile,fertilityfile,p0file,dfile,vocab_index):
        proba_table = {}

        logging.info("LOADING IBM2 TTABLE")
        proba_table["translation_table"] = defaultdict(lambda: defaultdict(lambda: IBMModel.MIN_PROB))
        with codecs.open(ttablefile,"r",encoding="utf-8") as ttf:
            for line in ttf:
                line = line.rstrip()
                tok = re.split(" ",line)
                src_word = vocab_index[0][int(tok[0])]
                tgt_word = vocab_index[1][int(tok[1])]
                # if src_word:
                #     logging.debug("LOADING P("+tgt_word+"/"+src_word+")="+tok[2])
                # else:
                #     logging.debug("LOADING P("+tgt_word+"/NULL)="+tok[2])
                proba_table["translation_table"][tgt_word][src_word] = float(tok[2])

        logging.info("LOADING IBM2 ATABLE")
        proba_table["alignment_table"] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: IBMModel.MIN_PROB))))
        with codecs.open(atablefile,"r",encoding="utf-8") as atf:
            for line in atf:
                line = line.rstrip()
                tok = re.split(" ",line)
                proba_table["alignment_table"][int(tok[0])][int(tok[1])][int(tok[2])][int(tok[3])] = float(tok[4])

        if IBMModelType > 2:
            logging.info("LOADING IBM3 FTABLE")
            proba_table["fertility_table"] =  defaultdict(lambda: defaultdict(lambda: IBMModel.MIN_PROB))
            
            with codecs.open(fertilityfile,"r",encoding="utf-8") as atf:
                for line in atf:
                    line = line.rstrip()
                    tok = re.split(" ",line)
                    src_word = vocab_index[0][int(tok[0])]
                    for i in range(1,11):
                        proba_table["fertility_table"][src_word][i] = float(tok[i])
                        # if src_word:
                        #     logging.debug("LOADING F("+src_word+","+str(i)+")="+tok[i])
                        # else:
                        #     logging.debug("LOADING F(NULL,"+str(i)+")="+tok[i])

                        
                        
            logging.info("LOADING IBM3 DTABLE")
            proba_table["distortion_table"] = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: IBMModel.MIN_PROB))))

            with codecs.open(dfile,"r",encoding="utf-8") as atf:
                for line in atf:
                    line = line.rstrip()
                    tok = re.split(" ",line)
                    proba_table["distortion_table"][int(tok[0])][int(tok[1])][int(tok[2])][int(tok[3])] = float(tok[4])

            logging.info("LOADING IBM3 P1")
            with codecs.open(p0file,"r",encoding="utf-8") as atf:
                for line in atf:
                    line = line.rstrip()
                    proba_table["p1"] = 1.0 - float(line)

        if IBMModelType == 2:
            logging.info("LOADING AND TRAINING IBM MODEL2")
            self.model = IBMModel2(self.aligned_corpus,self.iterations,proba_table)
        elif IBMModelType == 3:
            logging.info("LOADING AND TRAINING IBM MODEL3")
            self.model = IBMModel3(self.aligned_corpus,self.iterations,proba_table)
        else:
            exit(1)
            
    @timeout.timeout(5)
    def align(self,sentpair):
        if IBMModelType == 2:
            return self.model.best_model2_alignment(sentpair)
        elif IBMModelType == 3:
            sample, best = self.model.sample(sentpair)
            return best

class bidirectWordAligner(object):
    def __init__(self, sbitext, src, tgt, models_dir_path):
        self.dir_path = models_dir_path
        self.wamodel = self.load_model(sbitext.get_bitext(), src, tgt)
        self.reverse_wamodel = self.load_model(sbitext.get_inverted_bitext(), tgt, src)

    def load_model(self, bitext, src, tgt):
        model = wordAligner(bitext, TRAINING_ITERATIONS)
        # src and tgt get inverted between the word aligner convention and the bitext, model convention in NLTK
        lp = tgt+"-"+src
        if self.dir_path:
            if IBMModelType == "IBMModel2":
                ttablefile = self.dir_path + "/" + lp + ".IBM2.t.count"
                atablefile = self.dir_path + "/" + lp + ".IBM2.a.count"
            else:
                ttablefile = self.dir_path + "." + lp + ".t3"
                atablefile = self.dir_path + "." + lp + ".a3"
            fertilityfile = self.dir_path + "." + lp + ".n3"
            p1file = self.dir_path + "." + lp + ".p0_3"
            distortionfile = self.dir_path + "." + lp + ".d3"

            # src and tgt get inverted between the word aligner convention and the bitext, model convention in NLTK
            vocab_index = self.load_vocabs(tgt, src)
            
            model.define_model_from_tables(ttablefile, atablefile, fertilityfile, p1file, distortionfile, vocab_index)
        else:
            model.train_model()
        return model
    def load_vocabs(self, src, tgt):
        return (self.load_vocab(src), self.load_vocab(tgt))

    def load_vocab(self, language):
        vocab = {}
        vocab_file = self.dir_path + "." + language + ".vcb"
        logging.info("LOADING VOCABULARY FOR LANGUAGE="+language)
        #nmax = 0
        with codecs.open(vocab_file,"r",encoding="utf-8") as vf:
            for line in vf:
                line = line.rstrip()
                toks = line.split('\t')
                n = int(toks[0])
                #if n>nmax:
                #    nmax = n
                vocab[n] = toks[1]
            # NULL word index is 0
            vocab[0] = None
        return vocab
    
# takes a single file (tab-separated parallel sentences) as input from stdin
if __name__ == '__main__':
    bitext = []
    with sys.stdin as f:
        for line in f:
            line = line.rstrip()
            paral = re.split('\t',line)
            srcwords = re.split(' ',paral[0])
            tgtwords = re.split(' ',paral[1])
            bitext.append(AlignedSent(srcwords,tgtwords))

    if len(sys.argv) > 1:
        mywa = wordAligner(bitext,5)
        ttablefile = sys.argv[1]
        atablefile = sys.argv[2]
        mywa.define_model_from_tables(ttablefile,atablefile)
    else:
        mywa = wordAligner(bitext,5)
        mywa.train_model()

    for sentpair in mywa.aligned_corpus:
        aligninfo = mywa.align(sentpair)
        #print str(sentpair.words)+"\t"+str(sentpair.mots)+"\t"+str(sentpair.alignment)
        print str(aligninfo.src_sentence)+"\t"+str(aligninfo.trg_sentence)+"\t"+str(aligninfo.alignment)
