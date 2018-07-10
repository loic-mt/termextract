# command-line for truecaser training and testing
# takes folder with txt files as input, returns a truecasing model
# model can then be tested on same or new data


import truecaser
import nltk

import codecs
import logging
import sys


def get_truecaser_argparser():
    import argparse
    parser = argparse.ArgumentParser(
        prog='truecaser',
        description="""
        Train and test truecaser

        Command-line arguments:
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False)

    group = parser.add_argument_group("Options")
    group.add_argument("-h", "--help", action="help", help="train and test truecaser")
    group.add_argument("-d", "--directory", required=False, help="train on corpus in this directory (.txt files)")
    group.add_argument("-m", "--model", required=True, help="truecasing model to create or to load")
    group.add_argument("-t", "--test", required=False, help="run model on this text file")
    group.add_argument("-l", "--language", required=False, default="any")
    return parser


def truecaser_main(args):
    if (args.directory and not(args.test)):
        mytruecaser = truecaser.truecaser()
        mytruecaser.train(args.directory,"txt",args.language)
        mytruecaser.save_model(args.model)
    elif (not(args.directory) and args.test):
        mytruecaser = truecaser.truecaser()
        mytruecaser.load_model(args.model)
        with codecs.open(args.test,'r',encoding='utf8') as f:
            for line in f:
                tokens = nltk.word_tokenize(line)
                tokens = mytruecaser.truecase_alltokens(tokens)
                sys.stdout.write(u" ".join(tokens)+"\n")
    else:
        logging.error("com'on, it's either training or testing")
