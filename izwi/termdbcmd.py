# command-line for terminology database processing

import logging
import warnings

import database
import consolidator
import export


defaultParams=[0.3,0.3,0.3]


def get_termdb_argparser():
    import argparse
    parser = argparse.ArgumentParser(
        prog='termdb',
        description="""
        Terminology database management

        Command-line arguments:
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False)

    group = parser.add_argument_group("Options")
    group.add_argument("-h", "--help",
                       action="help",
                       help="izwi termdb manager")
    group.add_argument("--logging",
                       help="type of logging to perform (DEBUG, INFO, WARNING, "
                       "ERROR, CRITICAL). Default: ERROR")
    group.add_argument("-d",
                       "--database",
                       required=True,
                       help="sqlite database file")
    group.add_argument("-c",
                       "--consolidate",
                       action="store_true",
                       required=False,
                       help="updates term relevance scores")
    group.add_argument("-e",
                       "--export",
                       action="store_true",
                       required=False,
                       help="export DB for given domain. "
                       "Format is (tabulated): "
                       "relevance/POS/term string/frequency"
                       " in domain/number of documents matched in domain")
    group.add_argument("-l",
                       "--language",
                       default=None,
                       help="language L1 or language pair (L1, L2)")
    group.add_argument("-D",
                       "--domain",
                       required=False,
                       help="file with domain names")
    group.add_argument("-n",
                       "--nbsamples",
                       type=int,
                       required=False,
                       help="")
    group.add_argument("-m",
                       "--merge",
                       required=False,
                       help="list of database files"
                       " to merge into specified database")
    group.add_argument("-mf",
                       "--minfreq",
                       type=int,
                       required=False,
                       default = 1,
                       help="minimal frequency")
    group.add_argument("-msw",
                       "--minsourcewords",
                       type=int,
                       required=False,
                       default = 1,
                       help="minimum number of words in the source term")
    group.add_argument("-swt",
                       "--source_with_targets",
                       default=False,
                       required=False,
                       action="store_true",
                       help="print source terms with target"
                       " when available")

    return parser


def termdb_main(args):
    if args.logging:
        numeric_level = getattr(logging, args.logging.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % args.logging)
        logging.basicConfig(level=numeric_level)
    else:
        logging.basicConfig(level=logging.ERROR)

    myDB = database.izwiDB(args.database, "")

    if (args.consolidate):
        myconsol = consolidator.consolidator(defaultParams)
        with warnings.catch_warnings():
            warnings.simplefilter("always")
            myDB.accept(myconsol)
    elif (args.export):
        if not (args.domain and args.nbsamples):
            print("specify a file with one domain per line"
                 " and number of terms to be exported")
            exit(1)
        else:
            with open(args.domain, 'r') as domainsfile:
                for line in domainsfile:
                    domain = line.rstrip()
                    filename = domain+"_"+str(args.nbsamples)+"_terms_list.txt"
                    logging.info('Exporting %(num)d most relevant terms for domain "%(d)s',
                            {"num": args.nbsamples, "d": domain})
                    exportfile = open(filename, 'w')
                    myexporter = export.exporter(args.language,
                                                 domain,
                                                 args.nbsamples,
                                                 exportfile,
                                                 args.minsourcewords,
                                                 args.minfreq,
                                                 args.source_with_targets)
                    myDB.accept(myexporter)
                    exportfile.close()
    elif (args.merge):
        with open(args.merge) as f:
            for line in f:
                filepath = line.rstrip()
                logging.info("Importing database file "+filepath)
                importedDB = database.izwiDB(filepath, "")
                importedDB.export_to_other_DB(myDB)
                importedDB.close()
    else:
        print "NB DOMAINS : "+str(myDB.count_domains())
        print "NB DOCUMENTS : "+str(myDB.count_documents())
        print "NB TERMS : "+str(myDB.count_terms())
        print ""
        print "DOMAIN NAMES : "
        print "\n".join(myDB.get_all_domain_names())

    myDB.conclude()
