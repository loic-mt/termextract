import logging
from math import log
from math import pow

import database
from designpatterns import Visitor


class consolidator(Visitor):
    def __init__(self,params):
        self.params = params

    def visit(self, thisDB):
        self.db = thisDB
        # count number of domains
        self.nbDomainsTotal = self.db.count_domains()
        self.nb_domain_docs = dict(self.db.count_docs_in_all_domains())
        logging.info("Total number of domains is %d" % self.nbDomainsTotal)
        # add score to all terms
        self.add_scores_to_all_terms()

    def add_scores_to_all_terms(self):
        termids = self.db.get_all_terms()
        #for termid in termids[:2000]:
        for termid in termids:
            logging.debug("Adding score to term %d" % termid)
            self.add_scores_to_term(termid)

    def add_scores_to_term(self, termid):
        # all domains in which this term appears
        termDomains = self.db.get_domains_for_term(termid)
        # count those domains
        nbTermDomains = len(termDomains)
        logging.debug("Term %d in %d domains" % (termid, nbTermDomains))
        for domainid in termDomains:
            self.add_score_to_term_in_domain(termid, domainid, nbTermDomains)

    def add_score_to_term_in_domain(self, termid, domainid, nbTermDomains):
        # number of documents in given domain
        nbDomainDocs = self.nb_domain_docs[domainid]
        # frequency of this term in this domain
        freqs = self.db.get_freq_docsfreq_for_term_in_domain(termid, domainid)
        termDomainFreq = freqs[0]
        nbTermDocs = freqs[1]
         # compute score
        relevance = self.score_term(termDomainFreq,nbTermDocs,nbDomainDocs,nbTermDomains)
        #if nbTermDomains == self.nbDomainsTotal:
        #    logging.warn("TERM "+str(termid)+" IN ALL DOMAINS")
        #logging.debug("SCORE = "+str(relevance))
        # update score for term in this domain
        #logging.debug("UPDATING SCORE FOR TERM "+str(termid)+" IN DOMAIN "+str(domainid))
        self.db.update_relevance_for_term_in_domain(relevance, termid, domainid)

    def score_term(self, termDomainFreq,nbTermDocs,nbDomainDocs,nbTermDomains):
        #logging.debug("COMPUTING SCORE WITH "+str(termDomainFreq)+" , "+str(nbTermDocs)+" , "+str(nbDomainDocs)+" , "+str(nbTermDomains))
        if (nbDomainDocs == 0):
            logging.error("0 DOCS IN DOMAIN")
            logging.error("COMPUTING SCORE WITH "+str(termDomainFreq)+" , "+str(nbTermDocs)+" , "+str(nbDomainDocs)+" , "+str(nbTermDomains))
            exit(1)
        if (nbTermDocs == 0):
            logging.error("0 DOCS IN TERM : ERROR")
            logging.error("COMPUTING SCORE WITH "+str(termDomainFreq)+" , "+str(nbTermDocs)+" , "+str(nbDomainDocs)+" , "+str(nbTermDomains))
            exit(1)
        if (termDomainFreq == 0):
            logging.error("0 OCCURENCE OF TERM : ERROR")
            logging.error("COMPUTING SCORE WITH "+str(termDomainFreq)+" , "+str(nbTermDocs)+" , "+str(nbDomainDocs)+" , "+str(nbTermDomains))
            exit(1)
        sc = pow(float(termDomainFreq),0.5)*pow(float(nbTermDocs)/float(nbDomainDocs),0.25)*(1.0+5*(log(float(self.nbDomainsTotal))-log(float(nbTermDomains))))
        if (sc == 0.0):
            logging.error("SCORE IS NILL : ERROR")
            logging.error("COMPUTING SCORE WITH "+str(termDomainFreq)+" , "+str(nbTermDocs)+" , "+str(nbDomainDocs)+" , "+str(nbTermDomains))
            exit(1)

        return sc
        #sc = self.params[0]*log(termDomainFreq)
        #+ self.params[1]*(log(nbTermDocs)-log(nbDomainDocs))
        #+ self.params[2]*(log(self.nbDomainsTotal)-log(nbTermDomains))
        #return sc

    def tf_idf(self, termDomainFreq,nbTermDocs,nbDomainDocs,nbTermDomains):
        sc = termDomainFreq*(log(self.nbDomainsTotal)-log(nbTermDomains))
        return sc
