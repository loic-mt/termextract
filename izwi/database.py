import logging
import sqlite3

import termextractor
import documentfilter
from documentfilter import izwiDocument
import operator

# The maximum number of placeholders that SQLite supports in the IN statement
BATCH_SIZE = 999

prefixes = set([("um","s"), ("umu","s"), ("aba", "p"), ("abe", "p"), ("u", "s"), ("o", "p"), ("imi", "p"), ("i", "s"), ("ama", "p"), ("ame", "p"), ("isi", "s"), ("is", "s"), ("izi", "p"), ("iz", "p"), ("in", "s"), ("izin", "p"), ("izim", "p"), ("ubu", "s"), ("uku", "s")])

#select src_doc.id from document AS src_doc  INNER JOIN document AS tgt_doc INNER JOIN term_in_document AS tid INNER JOIN document_in_domain AS did INNER JOIN document_alignment AS da ON tid.term_code=39656 AND did.document_code=src_doc.id AND did.domain_code=2 AND src_doc.id=da.doc_a AND tgt_doc.id=da.doc_b AND tgt_doc.language='nso' AND src_doc.id=tid.document_code ;

def match_longest_prefix(prefixes, word):
    mlength = 0
    matchingp = None
    for p in prefixes:
        if word.startswith(p[0]) and len(p[0])>mlength:
            matchingp = p
            mlength = len(p)
    return matchingp
    
class izwiDB:
    def __init__(self, thisdbfile, thisschemafile):
        self.con = sqlite3.connect(thisdbfile, timeout=30000.0)
        self.cur = self.con.cursor()

        if (thisschemafile):
            schema = ""
            with open(thisschemafile, "r") as myfile:
                schema = myfile.read()
            self.con.executescript(schema)

    def accept(self, visitor):
        visitor.visit(self)

    def get_domain_id(self, thisdomain):
        sqlnamelst = (thisdomain, )
        self.cur.execute('SELECT rowid FROM domain WHERE name=?', sqlnamelst)
        res = self.cur.fetchone()
        if res is not None:
            did = res[0]
        else:
            did = None
        return did

    def add_domain(self, thisdomain):
        did = self.get_domain_id(thisdomain)
        if (did is None):
            sqlstr = "INSERT INTO domain VALUES (NULL, ?)"
            self.cur.execute(sqlstr, (thisdomain,))
            did = self.cur.lastrowid
        self.domainid = did
        return self.domainid

    def add_document(self, thisdoc):
        sqlstr = "INSERT INTO document VALUES (NULL, ?, ?)"
        self.cur.execute(sqlstr,
                         (thisdoc.get_language(), thisdoc.get_filename()))
        return self.cur.lastrowid

    def get_docid(self, file_lang_tuple):
        logging.debug("GETTING DOC ID FOR "+str(file_lang_tuple))
        sqlstr = "SELECT rowid FROM document WHERE filename=? AND language=?"
        self.cur.execute(sqlstr, file_lang_tuple)
        res = self.cur.fetchone()
        logging.debug("RES = "+str(res))
        if res is not None:
            docid = res[0]
        else:
            docid = None
        return docid

    def add_document_to_current_domain(self, thisfilename):
        self.docid = self.add_document(thisfilename)
        # add document-domain matching
        self.add_doc_in_domain(self.docid, self.domainid)
        return self.docid

    def get_termid(self, term):
        sqlstr = "SELECT rowid FROM term WHERE language=? AND pos=? AND string=?"
        self.cur.execute(sqlstr,
                         (term.get_language(),
                          term.get_pos(),
                          term.get_string()))
        res = self.cur.fetchone()
        if res is not None:
            termid = res[0]
        else:
            termid = None
        return termid

    def add_term(self, term):
        # add term
        termid = self.get_termid(term)
        if termid is None:
            sqlstr = "INSERT INTO term VALUES (NULL, ?, ?, ?)"
            self.cur.execute(sqlstr,
                             (term.get_language(),
                              term.get_pos(),
                              term.get_string()))
            termid = self.cur.lastrowid
        return termid

    def update_term_surface_form(self, termid, surface_form, count):
        sqlstr = "SELECT rowid, frequency FROM surface_form WHERE term_code=? AND form=?"
        self.cur.execute(sqlstr, (termid, surface_form))
        res = self.cur.fetchone()
        if res is None:  # term not yet found in domain
            sqlstr = "INSERT INTO surface_form VALUES (?, ?, ?)"
            self.cur.execute(sqlstr, (termid, surface_form, count))
        else:  # term already in domain, update both frequency and docfrequency
            rowid, frequency = res
            frequency += count

            sqlstr = """UPDATE surface_form
                        SET frequency=?
                        WHERE term_code=? AND form=?"""
            self.cur.execute(sqlstr, (frequency, termid, surface_form))

    def add_term_in_doc(self, termid, docid, trange):
        # add a term-document occurence
        sqlstr = "INSERT INTO term_in_document VALUES (?, ?, ?, ?)"
        self.cur.execute(sqlstr, (termid, docid, trange[0], trange[1]))

    def add_terms_in_doc(self, termid, docid, occurences):
        # add multiple term-document occurences
        sqlstr = "INSERT INTO term_in_document VALUES (?, ?, ?, ?)"
        values = [(termid,
                   docid,
                   trange[0],
                   trange[1])
                  for trange in occurences]
        self.cur.executemany(sqlstr, values)

    def add_doc_in_domain(self, docid, domid):
        # add document-domain matching
        sqlstr = "INSERT INTO document_in_domain VALUES (?, ?, 0.0)"
        self.cur.execute(sqlstr, (docid, domid))

    def update_term_in_domain(self, termid, domid, freq, docfreq):
        sqlstr = "SELECT rowid, frequency, docsfrequency FROM term_in_domain WHERE term_code=? AND domain_code=?"
        self.cur.execute(sqlstr, (termid, domid))
        res = self.cur.fetchone()
        if res is None:  # term not yet found in domain
            sqlstr = "INSERT INTO term_in_domain VALUES (?, ?, ?, ?, ?)"
            self.cur.execute(sqlstr, (termid, domid, freq, docfreq, 0.0))
        else:  # term already in domain, update both frequency and docfrequency
            rowid, curfreq, curdocsfreq = res
            curfreq += freq
            curdocsfreq += docfreq

            sqlstr = """UPDATE term_in_domain
                        SET frequency=?, docsfrequency=?
                        WHERE term_code=? AND domain_code=?"""
            self.cur.execute(sqlstr, (curfreq, curdocsfreq, termid, domid))

    def count_domains(self):
        sqlstr = "SELECT Count() FROM domain"
        self.cur.execute(sqlstr)
        res = self.cur.fetchone()[0]
        return res

    def count_documents(self):
        sqlstr = "SELECT Count() FROM document"
        self.cur.execute(sqlstr)
        res = self.cur.fetchone()[0]
        return res

    def count_terms(self):
        sqlstr = "SELECT Count() FROM term"
        self.cur.execute(sqlstr)
        res = self.cur.fetchone()[0]
        return res

    def get_all_domain_names(self):
        sqlstr = "SELECT name FROM domain"
        self.cur.execute(sqlstr)
        res = [str(i[0]) for i in self.cur.fetchall()]
        return res

    def count_docs_in_all_domains(self):
        sqlstr = "SELECT domain_code, Count() FROM document_in_domain GROUP BY domain_code;"
        self.cur.execute(sqlstr)
        res = self.cur.fetchall()
        return res

    def get_all_terms(self):
        sqlstr = "SELECT rowid FROM term"
        self.cur.execute(sqlstr)
        res = [int(i[0]) for i in self.cur.fetchall()]
        return res

    def get_terms_in_document(self, file_lang_tuple):
        # returns a list of (termid, start_token, end_token)
        sqlstr = "SELECT term_code, start_token, end_token FROM term_in_document WHERE document_code=?"
        docid = self.get_docid(file_lang_tuple)
        self.cur.execute(sqlstr, (docid,))
        res = [(int(i[0]), (int(i[1]), int(i[2])))
               for i in self.cur.fetchall()]
        return res

    # for now, hard-coded for Zulu
    def get_best_form_from_id(self, termcode):
        # get all surface forms in a dictionary
        sqlstr = "SELECT form, frequency FROM surface_form WHERE term_code=?"
        self.cur.execute(sqlstr, (termcode,))
        res = self.cur.fetchall()
        form_to_freq = {}
        singular_to_freq = {}
        plural_to_freq = {}
        for x in res:
            form_to_freq[x[0]] = int(x[1])
            mp = match_longest_prefix(prefixes, x[0])
            if mp:
                if mp[1] == "s":
                    singular_to_freq[x[0]] = int(x[1])
                elif mp[1] == "p":
                    plural_to_freq[x[0]] = int(x[1])

        if len(singular_to_freq):
            # then take the most frequent form
            sorted_list = sorted(singular_to_freq.items(), key=operator.itemgetter(1), reverse=True)
        elif len(plural_to_freq):
            # then take the most frequent form
            sorted_list = sorted(plural_to_freq.items(), key=operator.itemgetter(1), reverse=True)
        else:
            sorted_list = sorted(form_to_freq.items(), key=operator.itemgetter(1), reverse=True)
        form = sorted_list[0]
        return form[0]

    def get_term_from_id(self, termcode): 
        sqlstr = "SELECT language, pos, string FROM term WHERE id=?"
        self.cur.execute(sqlstr, (termcode,))
        res = self.cur.fetchone()
        myterm = termextractor.term(res[0], res[1], res[2], None)
        return myterm
    
    def get_domains_for_term(self, termcode):
        sqlstr = "SELECT domain_code FROM term_in_domain WHERE term_code=?"
        self.cur.execute(sqlstr, (termcode,))
        res = [int(i[0]) for i in self.cur.fetchall()]
        return res

    def get_sorted_terms_for_domain(self, language, domaincode, nmax):
        logging.debug("looking for terms in language "
                      + language + ", domain = " + str(domaincode) + " nmax="+str(nmax))
        sqlstr = "SELECT tid.term_code, tid.relevance, tid.frequency, tid.docsfrequency FROM term_in_domain AS tid INNER JOIN term AS t ON tid.term_code = t.id WHERE t.language=? AND tid.domain_code=? ORDER BY tid.relevance DESC LIMIT ?"
        logging.debug("SQL request: " + sqlstr) 
        self.cur.execute(sqlstr, (language, domaincode, nmax,))
        res = self.cur.fetchall()
        return res

    def get_docids_in_domain(self, language, domaincode):
        sqlstr = """
        SELECT document_code
        FROM document_in_domain
        INNER JOIN document ON document_code = document.id
        GROUP BY document_code
        HAVING document.language=? AND domain_code=?
        """
        self.cur.execute(sqlstr, (language, domaincode))
        res = self.cur.fetchall()
        return res
    
    def get_document_alignments(self, languagepair, domaincode):
        sqlstr = "SELECT doc_al.id FROM document_alignment AS doc_al JOIN document AS srcdoc ON doc_a = srcdoc.id JOIN document AS tgtdoc ON doc_b = tgtdoc.id JOIN document_in_domain AS srcdocindom ON doc_a = srcdocindom.document_code WHERE srcdoc.language=? AND tgtdoc.language=? AND srcdocindom.domain_code=?"
        
        self.cur.execute(sqlstr, (languagepair[0],
                                  languagepair[1],
                                  domaincode,))
        res = self.cur.fetchall()
        return res

    def get_term_pairs_for_doc_alignment(self, domaincode, dacode):
        sqlstr = "SELECT ta.term_a_code, ta.term_b_code, tid.relevance, ta.frequency, tgttid.frequency FROM term_alignment AS ta INNER JOIN  term_in_domain AS tid INNER JOIN term_in_domain AS tgttid ON ta.term_a_code=tid. term_code AND tid.domain_code=? AND tgttid.term_code=ta.term_b_code AND tgttid.domain_code=tid.domain_code WHERE  ta.document_alignment_code=? ORDER BY tid.relevance DESC, ta.frequency DESC"
        self.cur.execute(sqlstr, (domaincode, dacode,))
        res = self.cur.fetchall()
        return res

    def get_term_pairs_for_domain(self, languagepair, domaincode):
        # list of ids
        logging.debug("LOOKING FOR DOCUMENT ALIGNMENTS")
        documentalignments = self.get_document_alignments(languagepair,
                                                          domaincode)
        term_pair = {}
        for da in documentalignments:
            logging.debug("document alignment "+str(da))
            term_pairs_for_da = self.get_term_pairs_for_doc_alignment(domaincode, da[0])
            for t in term_pairs_for_da:
                key = tuple(t[0:2])
                if key not in term_pair:
                    logging.debug("new term pair: "+str(key))
                    term_pair[key] = list(t[2:5])
                else:
                    logging.debug("seen term pair: "+str(key))
                    term_pair[key][1] += t[3]
                    term_pair[key][2] += t[4]

        cumul = []
        for t in term_pair:
            myt = (t[0], t[1], term_pair[t][0], term_pair[t][1], term_pair[t][2])
            cumul.append(myt)

        return cumul
    
    def get_freq_docsfreq_for_term_in_domain(self, termcode, domaincode):
        sqlstr = """SELECT frequency, docsfrequency
                    FROM term_in_domain
                    WHERE term_code=? AND domain_code=?"""
        self.cur.execute(sqlstr, (termcode, domaincode))
        res = self.cur.fetchone()
        return res

    def update_relevance_for_term_in_domain(self, relevance, termid, domainid):
        sqlstr = """UPDATE term_in_domain
                    SET relevance=?
                    WHERE term_code=? AND domain_code=?"""
        self.cur.execute(sqlstr, (relevance, termid, domainid))

    def add_document_alignment(self, doc_id_tuple):
        logging.debug("ADDING DOCUMENT ALIGNMENT IN THE DATABASE: "+str(doc_id_tuple))
        doca_id, docb_id = doc_id_tuple
        sqlstr = "INSERT INTO document_alignment VALUES (NULL, ?, ?)"
        self.cur.execute(sqlstr, (doca_id, docb_id))
        return self.cur.lastrowid

    def update_term_alignment_in_document_alignment(self,
                                                    docalignid,
                                                    term_id_tuple,
                                                    frequency):
        terma_id, termb_id = term_id_tuple
        sqlstr = """SELECT frequency
                    FROM term_alignment
                    WHERE document_alignment_code=?
                    AND term_a_code=? AND term_b_code=?"""
        self.cur.execute(sqlstr, (docalignid, terma_id, termb_id))
        res = self.cur.fetchone()
        if res is None:  # new term alignment
            sqlstr = "INSERT INTO term_alignment VALUES (?, ?, ?, ?)"
            self.cur.execute(sqlstr,
                             (docalignid, terma_id, termb_id, frequency))
        else:  # increment frequency of existing term alignment
            new_frequency = res[0] + frequency
            sqlstr = """UPDATE term_alignment
                        SET frequency=?
                        WHERE document_alignment_code=?
                        AND term_a_code=? AND term_b_code=?"""
            self.cur.execute(sqlstr,
                             (new_frequency, docalignid, terma_id, termb_id))

    def add_sentences(self, docid, sentences):
        """lengths is a list of tuples (paragraph_number, sentence)"""
        docid = int(docid)
        sqlstr = "INSERT INTO SENTENCE VALUES (NULL, %d, ?, ?)" % docid
        self.cur.executemany(sqlstr, sentences)

    def get_sentence_lengths(self, docid, para):
        """Return all (id, sentence length) of a paragraph in the document"""
        sqlstr = """SELECT rowid, LENGTH(text) FROM SENTENCE
                    WHERE DOCUMENT_CODE = ? AND PARAGRAPH_NUMBER = ?
                    ORDER BY ID"""
        self.cur.execute(sqlstr, (docid, para))
        return self.cur.fetchall()

    def get_all_paragraph_lengths(self, docid):
        """Return (par_num, char_length) for all paragraphs in the document"""
        docid = int(docid)
        sqlstr = """SELECT paragraph_number, sum(length(text)) FROM SENTENCE
                    WHERE DOCUMENT_CODE = ?
                    GROUP BY PARAGRAPH_NUMBER
                    ORDER BY PARAGRAPH_NUMBER"""
        self.cur.execute(sqlstr, (docid,))
        return self.cur.fetchall()

    def get_sentence_pairs(self, pairs):
        """Return a list of sentence pairs with the given IDs."""
        ids = set()
        for pair in pairs:
            ids.update(pair)
        # in this day and age, we have to construct a parameter list, no more
        # than 1000 placeholders at a time (sqlite limit)
        sentence_dict = {}
        all_ids = list(ids)
        for start in range(0, len(all_ids), BATCH_SIZE):
            sublist = all_ids[start:start+BATCH_SIZE]
            question_marks = "?"*len(sublist)
            question_marks = ",".join(question_marks)
            sqlstr = """SELECT rowid, text
                        FROM sentence
                        WHERE rowid in (%s)""" % question_marks
            self.cur.execute(sqlstr, sublist)
            sentence_dict.update(self.cur.fetchall())

        return [(sentence_dict[s],
                 sentence_dict[t])
                for (s, t) in pairs]

    def commit(self):
        self.con.commit()

    def close(self):
        self.con.close()

    def conclude(self):
        self.commit()
        self.close()

    def export_to_other_DB(self, other_db):
        self.exported_domain_id = {}
        self.exported_document_id = {}
        self.exported_term_id = {}
        
        # export each table
        logging.info("Importing domains into target DB")
        self.export_domains(other_db)
        logging.info("Importing documents into target DB")
        self.export_documents(other_db)
        logging.info("Importing terms into target DB")
        self.export_terms(other_db)
        logging.info("Importing document to domain into target DB")
        self.export_document_in_domain(other_db)
        logging.info("Importing term to document into target DB")
        self.export_term_in_document(other_db)
        logging.info("Importing term to domain into target DB")
        self.export_term_in_domain(other_db)
        logging.info("All tables were imported")

    def export_domains(self, other_db):
        # get all domains in this db
        sqlstr = "SELECT id, name FROM domain"
        self.cur.execute(sqlstr)
        allres = self.cur.fetchall()
        for res in allres:
            newid = other_db.add_domain(res[1])
            self.exported_domain_id[res[0]] = newid

    def export_documents(self, other_db):
        # get all documents in this db
        sqlstr = "SELECT id, filename, language FROM document"
        self.cur.execute(sqlstr)
        allres = self.cur.fetchall()
        for res in allres:
            mydoc = izwiDocument(res[1])
            mydoc.set_language(res[2])
            newid = other_db.add_document(mydoc)
            self.exported_document_id[res[0]] = newid

    def export_terms(self, other_db):
        # get all terms in this db
        sqlstr = "SELECT id, language, pos, string FROM term"
        self.cur.execute(sqlstr)
        allres = self.cur.fetchall()
        for res in allres:
            thisterm = termextractor.term(res[1], res[2], res[3], (0, 0))
            newid = other_db.add_term(thisterm)
            self.exported_term_id[res[0]] = newid

    def export_document_in_domain(self, other_db):
        sqlstr = "SELECT document_code, domain_code FROM document_in_domain"
        self.cur.execute(sqlstr)
        allres = self.cur.fetchall()
        for res in allres:
            newdocid = self.exported_document_id[res[0]]
            newdomainid = self.exported_domain_id[res[1]]
            other_db.add_doc_in_domain(newdocid, newdomainid)

    def export_term_in_document(self, other_db):
        sqlstr = """SELECT term_code, document_code, start_token, end_token
                    FROM term_in_document"""
        self.cur.execute(sqlstr)
        allres = self.cur.fetchall()
        for res in allres:
            newtermid = self.exported_term_id[res[0]]
            newdocid = self.exported_document_id[res[1]]
            other_db.add_term_in_doc(newtermid, newdocid, res[2:4])

    def export_term_in_domain(self, other_db):
        sqlstr = "SELECT term_code, domain_code, frequency, docsfrequency FROM term_in_domain"
        self.cur.execute(sqlstr)
        allres = self.cur.fetchall()
        for res in allres:
            newtermid = self.exported_term_id[res[0]]
            newdomainid = self.exported_domain_id[res[1]]
            other_db.update_term_in_domain(newtermid,
                                           newdomainid,
                                           res[2],
                                           res[3])
            
    def source_term_in_aligned_corpus(self, term_id, tgt_lang, domain_code):
        sqlstr = "SELECT src_doc.id from document AS src_doc  INNER JOIN document AS tgt_doc INNER JOIN term_in_document AS tid INNER JOIN document_in_domain AS did INNER JOIN document_alignment AS da ON tid.term_code=? AND did.document_code=src_doc.id AND did.domain_code=? AND src_doc.id=da.doc_a AND tgt_doc.id=da.doc_b AND tgt_doc.language=? AND src_doc.id=tid.document_code"

        self.cur.execute(sqlstr, (term_id,
                                  domain_code,
                                  tgt_lang))
        res = self.cur.fetchall()
        return len(res)

