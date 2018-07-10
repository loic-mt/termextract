from designpatterns import Visitor
import logging
import re


class exporter(Visitor):
    def __init__(self, language, domain, nbsamples, filehandle, minsourcewords=1, minfreq=0, srcwithtargets=False):
        self.language = language
        self.domain = domain
        self.nbsamples = nbsamples
        self.filehandle = filehandle
        self.minsourcewords = minsourcewords
        self.minfreq = minfreq
        self.srcwithtargets = srcwithtargets
    
    def visit(self, thisDB):
        domaincode = thisDB.get_domain_id(self.domain)
        # get sorted termids for this domain

        if domaincode is not None:
            m = re.match(r"\((\w+)\, (\w+)\)", self.language)
            if (m):
                src = m.group(1)
                tgt = m.group(2)
                logging.info("EXPORTING BILINGUAL TERMS FOR ("+src+", "+tgt+")")

                if self.srcwithtargets:
                    self.export_src_terms_with_targets(src, tgt, domaincode, thisDB)
                else:
                    self.export_bilingual_terms(src, tgt, domaincode, thisDB)
            else:
                self.export_monolingual_terms(self.language, domaincode, thisDB)
                
    def export_src_terms_with_targets(self, src, tgt, domaincode, thisDB):
        termpairs = thisDB.get_term_pairs_for_domain((src, tgt),
                                                             domaincode)
        srcterm_to_term_pair = {}
        for tp in termpairs:
            if int(tp[3])>=self.minfreq:
                if tp[0] not in srcterm_to_term_pair:
                    srcterm_to_term_pair[tp[0]] = []
                srcterm_to_term_pair[tp[0]].append(tuple(tp))
            
        srcterms = thisDB.get_sorted_terms_for_domain(src,
                                                      domaincode,
                                                      self.nbsamples)
        logging.info("nb of terms = %d" % len(srcterms))
        
        for srcterm in srcterms:
            # src term
            if self.language == "zul":
                src_term = unicode(thisDB.get_best_form_from_id(srcterm[0])).encode('utf-8')
            else:
                src_term = unicode(thisDB.get_term_from_id(srcterm[0])).encode('utf-8')

            if len(src_term.split(' '))<self.minsourcewords:
                continue
            
            relevance = str(srcterm[1])
            freq = str(srcterm[2])
            docsfreq = str(srcterm[3])

            # tgt term if found
            src_freq_in_parallel_corpus = thisDB.source_term_in_aligned_corpus(srcterm[0], tgt, domaincode)
            src_freq = str(src_freq_in_parallel_corpus)
            if srcterm[0] not in srcterm_to_term_pair:
                if src_freq_in_parallel_corpus>=self.minfreq:
                    tgt_term = "NO_TARGET_MISSED_ALIGNMENT"
                else:
                    tgt_term = "NO_TARGET_NO_SOURCE_TERM"
                pair_freq = str(0)
            else:
                tps = srcterm_to_term_pair[srcterm[0]]
                
                sorted_targets = sorted(tps, key=lambda element: (element[2], element[3]), reverse=True)
                #print sorted_targets
                best_target = sorted_targets[0]
                if tgt == "zul":
                    tgt_term = unicode(thisDB.get_best_form_from_id(best_target[1])).encode('utf-8')
                else:
                    tgt_term = unicode(thisDB.get_term_from_id(best_target[1])).encode('utf-8')
                pair_freq = str(best_target[3])
                
            # print
            self.filehandle.write(relevance
                                  + "\t"+ src_term
                                  + "\t"+ tgt_term
                                  + "\t" + freq
                                  + "\t" + docsfreq
                                  + "\t" + src_freq
                                  + "\t" + pair_freq
                                  + "\n")

    def export_bilingual_terms(self, src, tgt, domaincode, thisDB):
        termpairs = thisDB.get_term_pairs_for_domain((src, tgt),
                                                             domaincode)
        myterms = []
        for tp in termpairs:
            myterms.append(tuple(tp))
            
        mysterms = sorted(myterms, key=lambda element: (element[2], element[3], element[4]), reverse=True)
            
        src_term_processed = set([])
        for tp in mysterms:
            src_term = unicode(thisDB.get_term_from_id(tp[0]))

            if len(src_term.split(' '))<self.minsourcewords:
                continue
            
            if tgt == "zul":
                tgt_term = unicode(thisDB.get_best_form_from_id(tp[1]))
            else:
                tgt_term = unicode(thisDB.get_term_from_id(tp[1]))
            src_term_relevance = tp[2]
            pair_freq = tp[3]
            if int(pair_freq)>=self.minfreq:
                if src_term not in src_term_processed:
                    output = u"%f\t%s\t%s\t%d\n" % (src_term_relevance, src_term, tgt_term, pair_freq)
                    self.filehandle.write(output.encode('utf-8'))
                    src_term_processed.add(src_term)
                else:
                    output = u"%f\t%s\t%s\t%d\n" % (src_term_relevance, src_term, tgt_term, pair_freq)
                    logging.debug("Minor translation excluded "+output)

    def export_monolingual_terms(self, language, domaincode, thisDB):
        termrels = thisDB.get_sorted_terms_for_domain(self.language,
                                                      domaincode,
                                                      self.nbsamples)
        logging.info("nb of terms = %d" % len(termrels))
        
        for termrel in termrels:
            if self.language == "zul":
                term = unicode(thisDB.get_best_form_from_id(termrel[0]))
            else:
                term = unicode(thisDB.get_term_from_id(termrel[0]))

            if len(term.split(' '))<self.minsourcewords:
                continue
                #term = thisDB.get_term_from_id(termrel[0])
            relevance = termrel[1]
            freq = termrel[2]
            docsfreq = termrel[3]
            output = unicode(term)
            self.filehandle.write(str(relevance)
                                  + "\t"+output.encode('utf-8')
                                  + "\t" + str(freq)
                                  + "\t" + str(docsfreq) + "\n")
