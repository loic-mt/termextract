# command-line for izwi
import logging

from domain import STUDYMATdomains
import termextractor
import database
from count_buffer import count_buffer
from aligner import izwiAligner
from documentfilter import documentFilter

debug = False


def get_izwi_argparser():
    import argparse
    parser = argparse.ArgumentParser(
        prog='izwi',
        description="""
        Izwi term extractor

        Command-line arguments:
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )

    group = parser.add_argument_group("Options")
    group.add_argument("-h", "--help",
                       action="help",
                       help="izwi term extractor")
    group.add_argument("--logging",
                       help="type of logging to perform (DEBUG, INFO, WARNING, "
                       "ERROR, CRITICAL). Default: ERROR")
    group.add_argument("-i", "--inputfile",
                       help="input file")
    group.add_argument("-I",
                       "--inputfilelist",
                       help="one file path per line")
    group.add_argument("-f",
                       "--fileformat",
                       choices=['docx', 'pdf', 'txt'],
                       help="file format")
    group.add_argument("-c", "--chunkrules",
                       required=False,
                       help="chunk rule file")
    group.add_argument("-s",
                       "--schema",
                       required=False,
                       help="sqlite schema (will create new DB)")
    group.add_argument("-d",
                       "--database",
                       required=False,
                       help="sqlite database file")
    group.add_argument("-b",
                       "--buffersize",
                       type=int,
                       default=10,
                       help="number of documents buffered")
    group.add_argument("-l",
                       "--language",
                       default=None)
    group.add_argument("-x", "--exclude",
                       action="store_true",
                       help="exclude files in other languages")
    group.add_argument("-D",
                       "--code2domains",
                       help="code to domain subject mapping (tabulated file)")
    group.add_argument("-D2",
                       "--code2domains_backoff",
                       help="backoff to first chars in module code")
    group.add_argument("-FD", "--forcedomain",
                       help="tag all documents with this domain")
    group.add_argument("-t",
                       "--truecaser",
                       help="truecasing model")
    group.add_argument("-a",
                       "--align",
                       help="two columns tabulated file with "
                       "('document', language) in each")
    group.add_argument("-dbt",
                       "--dump_bitext",
                       required=False,
                       default=False,
                       action="store_true",
                       help="align documents, dump bitext and quit")
    group.add_argument("-w",
                       "--wordalignmodel",
                       help="""
                       directory path for both IBM2 parameter files,
                        in both directions
                       """)
    group.add_argument("-n",
                       "--normalisemodel",
                       action="store_true",
                       help="""
                       save normalise model (save mappings from DB lemmatised form to surface forms)
                       """)
    return parser


myCB = count_buffer()


def process_one_file(args, term_extractor, filepath, mydomains):

    if args.forcedomain:
        detectedDomain = args.forcedomain
        logging.info("ENFORCING DOMAIN")
        logging.info("DOCUMENT IN DOMAIN : "+detectedDomain)
    elif mydomains:
        detectedDomain = mydomains.find_domain(filepath)
        if (len(detectedDomain)):
            logging.info("DOCUMENT IN DOMAIN : "+detectedDomain)
        else:
            logging.info("DOCUMENT DOMAIN NOT DETECTED")
            return
    else:
        logging.info("USING SINGLE GENERIC DOMAIN")
        detectedDomain = "UNKNOWN"

    myfilter = documentFilter()
    mydoc = myfilter.extract_doc(filepath, args.fileformat)

    logging.info("DETECTED LANGUAGE IS "+mydoc.get_language())
    if args.language:
        if args.exclude and mydoc.get_language() != args.language:
            logging.info("EXCLUDING DOCUMENT IN WRONG LANGUAGE\n")
            return False
        elif mydoc.get_language() != args.language:
            logging.info("LANGUAGE DETECTED DOES NOT MATCH, ENFORCING "+args.language+"\n")
            mydoc.set_language(args.language)
            
    logging.info("%d paragraphs will be processed", mydoc.nb_paragraphs())

    mydoc.accept(term_extractor)
    my_terms_and_forms = term_extractor.get_terms()
    my_sentences = term_extractor.get_sentences()
    term_extractor.reset()

    if debug:
        tokens = mydoc.get_tokens()
    mylexicon = {}
    mystr2term = {}
    mycheck = {}
    for (np, sf) in my_terms_and_forms: 
        key = unicode(np)
        if args.database:
            myCB.add_term_in_doc(np, mydoc, np.trange)
            myCB.add_surface_form(np, sf) 
        if (key in mylexicon):
            mylexicon[key] += 1
        else:
            mystr2term[key] = np
            mylexicon[key] = 1

            if debug:
                myoriginal = " ".join(tokens[np.trange[0]:np.trange[1]])
                logging.debug("CHECK: %s :: %s" % (np.string, myoriginal))

    if (args.database):
        logging.debug("NBDOC in buffer:", myCB.nbdoc)
        
        # store into buffer
        myCB.add_domain(detectedDomain)
        myCB.add_document(mydoc)
        myCB.add_doc_in_domain(mydoc, detectedDomain)
        myCB.add_sentences(mydoc, my_sentences)
        for k in mylexicon:
            myt = mystr2term[k]
            myCB.add_term(myt)
            myCB.update_term_in_domain(myt,
                                       detectedDomain,
                                       mylexicon[k])

        # dump if at least 10 documents processed
        if myCB.nbdoc >= args.buffersize:
            myDB = database.izwiDB(args.database, args.schema)
            myCB.dump_to(myDB)
            myDB.conclude()

    else:
        # print sorted list
        sortedList = sorted(mylexicon.items(),
                            key=lambda x: x[0].lower())
        # use .itemgetter(1) to sort by frequency
        for token in sortedList:
            output = u"%s\t%s" % (token[1], token[0])
            print output.encode('utf-8')


def izwi_main(args):
    if args.logging:
        numeric_level = getattr(logging, args.logging.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % args.logging)
        logging.basicConfig(level=numeric_level)
    else:
        logging.basicConfig(level=logging.ERROR)

    if (args.align):
        # ALIGNMENT AND BILINGUAL TERM MAPPING
        if (not args.wordalignmodel):
            logging.info("ALIGNMENT WITHOUT PRE-TRAINED MODEL")
            myaligner = izwiAligner(args.database,
                                    args.align,
                                    None,
                                    args.dump_bitext,
                                    True)
        else:
            myaligner = izwiAligner(args.database,
                                    args.align,
                                    args.wordalignmodel,
                                    args.dump_bitext,
                                    True)
        myaligner.process()
    else:
        # MONOLINGUAL TERM EXTRACTION
        if (args.truecaser):
            myextractor = termextractor.termExtractor(args.language,
                                                      args.chunkrules,
                                                      args.normalisemodel,
                                                      args.truecaser,
                                                      )
        else:
            myextractor = termextractor.termExtractor(args.language,
                                                      args.chunkrules,
                                                      args.normalisemodel)

        mydomains = None
        if(args.code2domains):
            mydomains = STUDYMATdomains(args.code2domains,
                                        args.code2domains_backoff)
        if (args.inputfile and args.chunkrules):
            process_one_file(args, myextractor, args.inputfile, mydomains)
            logging.info("REPORT ON WHOLE EXTRACTION: "+myextractor.stats())
        elif (args.inputfilelist and args.chunkrules):
            with open(args.inputfilelist) as f:
                for line in f:
                    filepath = line.rstrip()
                    logging.info("Processing file:"+filepath)
                    process_one_file(args, myextractor, filepath, mydomains)
                logging.info("REPORT ON WHOLE EXTRACTION: "+myextractor.stats())
        if (args.database):
            myDB = database.izwiDB(args.database, args.schema)
            myCB.dump_to(myDB)
            myDB.conclude()
