import logging
import re
import sys


class STUDYMATdomains:
    def __init__(self, codemappingfile,backoffcodemappingfile):
        # tabulated file, first column = code, second colu;n = subject
        self.code2subj = {}
        if (codemappingfile):
            with open (codemappingfile, "r") as myfile:
                for line in myfile:
                    line = line.rstrip()
                    chunks = re.split('\t',line)
                    self.code2subj[chunks[0]]=chunks[1]
        self.bo_code2subj = {}
        if (backoffcodemappingfile):
            with open (backoffcodemappingfile, "r") as myfile:
                for line in myfile:
                    line = line.rstrip()
                    chunks = re.split('\t',line)
                    self.bo_code2subj[chunks[0]]=chunks[1]

    def find_3lcode(self, filepath):
        matchedObj = re.match( r'^.*/([A-Z]{2}.*?)/.*', filepath, re.M)
        if matchedObj:
            return matchedObj.group(1)[0:3]
        else:
            return ""

    def code_to_subject(self, code, lettercode):
        if code in self.code2subj:
            return self.code2subj[code]
        elif lettercode in self.bo_code2subj:
            return self.bo_code2subj[lettercode]
        else:
            return ""

    def find_module_code(self, txtfilepath):
        matchedObj = re.match( r'.*zzz\_sg\_001\_\_unisa\-studymaterial\_\_(.{7}).*', txtfilepath, re.M)
        
        if matchedObj:
            return matchedObj.group(1)
        else:
            matchedObj = re.match( r'.*aals\_\_unisa\-study\-material\_\_(.{7}).*', txtfilepath, re.M) 
            if matchedObj:
                return matchedObj.group(1)
            else:
                logging.info("no module code found for:"+txtfilepath)
                return ""

    def find_domain(self, filepath):
        modulecode = self.find_module_code(filepath)
        logging.info("module code ="+modulecode)
        matchedlettercode = re.match( r'^([A-Z]+).*', modulecode, re.M)
        if matchedlettercode:
            lettercode = matchedlettercode.group(1)
            logging.debug("letter code ="+lettercode)
        else:
            lettercode = ""
        if (modulecode != ""):
            return self.code_to_subject(modulecode,lettercode)
        else:
            return ""
