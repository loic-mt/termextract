# a count buffer keeps *in memory* counts of domains, documents and terms seen in the corpus
# until they can be dumped into the database

import logging
from collections import defaultdict
from izwi.database import izwiDB
from izwi.termextractor import term


class count_buffer:
    def __init__(self):
        self.reset()

    def reset(self):
        self.nbdoc = 0
        self.domains = set()
        self.documents = set()
        self.terms = set()
        self.doc_in_domain = defaultdict(str)
        self.term_in_doc = defaultdict(lambda: defaultdict())
        self.term_in_domain = defaultdict(lambda: defaultdict())
        self.surface_form = defaultdict(lambda: defaultdict())
        self.sentences = defaultdict(list)
                
    def nbdoc(self):
        return self.nbdoc

    def add_domain(self, dom):
        logging.debug("added domain in buffer: "+str(dom))
        self.domains.add(dom)

    def add_document(self, doc):
        logging.debug("added document in buffer: "+str(doc))
        self.documents.add(doc)
        self.nbdoc += 1

    def add_term(self, term):
        logging.debug("added term in buffer: "+unicode(term))
        self.terms.add(term)
        
    def add_surface_form(self, term, form):
        key = unicode(term)
        if key not in self.surface_form:
            self.surface_form[key] = {}
        if form not in self.surface_form[key]:
            self.surface_form[key][form] = 1
        else:
            self.surface_form[key][form] += 1

    def add_doc_in_domain(self, doc,dom):
        self.doc_in_domain[str(doc)] = dom

    def add_term_in_doc(self, term, doc, trange):
        key = unicode(term)
        if key not in self.term_in_doc:
            self.term_in_doc[key] = {}

        if str(doc) not in self.term_in_doc[key]:
            self.term_in_doc[key][str(doc)] = []
        logging.debug("added term: "+key+" in document: "+str(doc))
        self.term_in_doc[key][str(doc)].append(trange)

    def update_term_in_domain(self,term,dom,freq):
        if unicode(term) not in self.term_in_domain:
            domains = defaultdict()
            self.term_in_domain[unicode(term)] = domains
        else:
            domains = self.term_in_domain[unicode(term)]

        if dom not in domains:
            domains[dom] = (freq, 1)
        else:
            domains[dom] = (domains[dom][0]+freq, domains[dom][1]+1)

    def add_sentences(self, doc, sentences):
        self.sentences[str(doc)] = sentences

    def dump_to(self, this_db):
        domain_to_id = {}
        document_to_id = {}
        term_to_id = {}
        for dom in self.domains:
            logging.debug("adding domain to DB: "+str(dom))
            domid = this_db.add_domain(dom)
            domain_to_id[dom] = domid
        for doc in self.documents:
            logging.debug("adding document to DB: "+str(doc))
            docid = this_db.add_document(doc)
            document_to_id[str(doc)] = docid
            #print "mapped "+str(doc)
        for term in self.terms:
            logging.debug("adding term to DB: "+unicode(term))
            tid = this_db.add_term(term)
            term_to_id[unicode(term)] = tid
        for uterm in self.surface_form.keys():
            termid = term_to_id[uterm]
            for form in self.surface_form[uterm].keys():
                count = self.surface_form[uterm][form]
                this_db.update_term_surface_form(termid, form, count)
        for docstr in self.doc_in_domain.keys():
            docid = document_to_id[docstr]
            domainid = domain_to_id[self.doc_in_domain[docstr]]
            logging.debug("adding doc: "+str(docid)+" in domain: "+str(domainid))
            this_db.add_doc_in_domain(docid, domainid)

        for uterm in self.term_in_doc.keys():
            termid = term_to_id[uterm]
            for docstr in self.term_in_doc[uterm].keys():
                docid = document_to_id[docstr]
                occurences = self.term_in_doc[uterm][docstr]
                logging.debug("adding term: "+str(termid)+" in document: "+str(docid)+" occurences:"+str(occurences))
                this_db.add_terms_in_doc(termid, docid, occurences)

        for uterm in self.term_in_domain.keys():
            for domstr in self.term_in_domain[uterm].keys():
                termid = term_to_id[uterm]
                domain_id = domain_to_id[domstr]
                f = self.term_in_domain[uterm][domstr]
                logging.debug("updating term: "+str(termid)+" in domain: "+str(domainid)+" frequencies:"+str(f))
                this_db.update_term_in_domain(termid, domain_id, f[0], f[1])

        for doc, sentences in self.sentences.viewitems():
            this_db.add_sentences(document_to_id[doc], sentences)
        self.reset()
