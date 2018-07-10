# truecaser module

import codecs
import languagedetection
import logging
import operator
import nltk
import pickle

class truecaser:
    def __init__(self):
        self.initial_dictionary = {}
        self.final_dictionary = {}
        self.file_extension = "txt"
        self.language = ""

    def train(self,this_directory,file_extension,language):
        self.file_extension = file_extension
        self.language=language
        self.add_directory(this_directory)
        self.compute_final_dictionary()

    def add_directory(self,this_directory):
        import glob
        for file in glob.glob(this_directory+"/*."+self.file_extension):
            self.add_file(file)

    def add_file(self,this_file):
        with codecs.open(this_file,'r',encoding='utf8') as f:
            lines = f.readlines()
        detected_lang = languagedetection.most_probable_language('\n'.join(lines)[0:1000])
        if (detected_lang == self.language) or (self.language == "any"):
            for line in lines:
                tokens = nltk.word_tokenize(line)
                for t in tokens:
                    self.add_token(t)
        else:
            logging.warning("excluded file %s: wrong language: %s (not %s)",
                            this_file, detected_lang, self.language)

    def add_token(self,token):
        #TODO: in case the token is not
        mykey=token.lower()
        if mykey in self.initial_dictionary:
            if token in self.initial_dictionary[mykey]:
                self.initial_dictionary[mykey][token]+=1
            else:
                self.initial_dictionary[mykey][token]=1
        else:
            self.initial_dictionary[mykey]={}
            self.initial_dictionary[mykey][token]=1

    def compute_final_dictionary(self):
        for k in self.initial_dictionary:
            best_casing= max(self.initial_dictionary[k].iteritems(), key=operator.itemgetter(1))[0]
            self.final_dictionary[k]=best_casing

    def truecase_alltokens(self,input):
        for i in range(0,len(input)): # string case
            input[i] = self.truecase_token(input[i])
        return input

    def truecase_token(self,token):
        mykey=token.lower()
        if mykey in self.final_dictionary:
            return self.final_dictionary[mykey]
        else:
            return token

    def save_model(self,this_file):
        pickle.dump(self.final_dictionary, open(this_file, "wb" ) )

    def load_model(self,this_file):
        self.final_dictionary = pickle.load( open(this_file, "rb"))
