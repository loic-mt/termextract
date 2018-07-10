import logging
from izwi.postagger import pos_tagger
from izwi.lemmatiser import lemmatiser
from izwi.timeout import timeout, TimeoutError

# sentence level bitext filter
class sentence_level_bitext_filter(object):
    def __init__(self, src, tgt, lemmatise=False, lowercase=False):
        self.lemmatise = lemmatise
        if self.lemmatise:
            self.src_postagger = pos_tagger(src)
            self.tgt_postagger = pos_tagger(tgt)
            self.src_lemmatiser = lemmatiser(src)
            self.tgt_lemmatiser = lemmatiser(tgt)
        else:
            self.src_postagger = None
            self.tgt_postagger = None
            self.src_lemmatiser = None
            self.tgt_lemmatiser = None
        self.lowercase = lowercase

    @timeout(5)
    def __filter_sent_pair__(self, bs):
        if self.lemmatise:
            src_len = len(bs[0].tokens)
            tgt_len = len(bs[1].tokens)
            src_sent_tagged = self.src_postagger.tag(bs[0].tokens)
            tgt_sent_tagged = self.tgt_postagger.tag(bs[1].tokens)
            #print str(tgt_sent_tagged)
            if src_sent_tagged == None or tgt_sent_tagged == None or len(src_sent_tagged)!=src_len or len(tgt_sent_tagged)!=tgt_len:
                src_sent_lemmatised =  bs[0].tokens
                tgt_sent_lemmatised = bs[1].tokens
                logging.warning("POS TAGGING FAILED IN sentence_level_bitext_filter")
            else:
                src_sent_lemmatised =  self.src_lemmatiser.word_by_word_lemma_list(src_sent_tagged)
                tgt_sent_lemmatised =  self.tgt_lemmatiser.word_by_word_lemma_list(tgt_sent_tagged)
                if src_sent_lemmatised == None or tgt_sent_lemmatised == None or len(src_sent_lemmatised)!=src_len or len(tgt_sent_lemmatised)!=tgt_len:
                    src_sent_lemmatised =  bs[0].tokens
                    tgt_sent_lemmatised = bs[1].tokens
                    logging.warning("LEMMATISATION FAILED IN sentence_level_bitext_filter")
        else:
            src_sent_lemmatised =  bs[0].tokens
            tgt_sent_lemmatised =  bs[1].tokens
        #print str(tgt_sent_lemmatised)
        if self.lowercase:
            src_sent = [w.lower() for w in src_sent_lemmatised]
            tgt_sent = [w.lower() for w in tgt_sent_lemmatised]
        else:
            src_sent = src_sent_lemmatised
            tgt_sent = tgt_sent_lemmatised
        bs[0].tokens = src_sent
        bs[1].tokens = tgt_sent
        return bs
        
    def apply(self, sbt):
        newbt = []
        for bs in sbt.bi_sent:
            try:
                newbs = self.__filter_sent_pair__(bs)
                newbt.append(newbs)
            except TimeoutError:
                logging.warning("TIMEOUT IN __filter_sent_pair__")
                continue
        sbt.bi_sent = newbt


             
             
             

