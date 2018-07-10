# -*- coding: utf-8 -*-


"""A module for cleaning operations after extraction."""


import re

def is_bullet_char(char):
    return char in u'•●\uf0d8\u0083\uf0b7\uf06e\u2022\u2023'


def is_punctuation(term):
    return not bool(re.search(r'\w', term))

def letters_in_each_token(term):
    return all(bool(re.search(r'\w', token, re.UNICODE)) for token in term.split())

def contains_nonletter(term):
    return bool(len(re.sub(ur"(\w|\s|-|'|’|/)+", '', term, flags=re.UNICODE))>0)

def is_possible_term(term):
    if not letters_in_each_token(term) or is_bullet_char(term[0]) or contains_numbers(term):
        return False
    elif len(term)>1:
        return True
    else:
        return False


def remove_afr_determiners(term):
    newterm = re.sub(ur"^(die|dié|['’]n|ŉ|ŉŉ)\s+", "", term)
    return newterm

def remove_eng_determiners(term):
    newterm = re.sub(r"^(the|a|an|this|that)\s+", "", term)
    return newterm

def contains_numbers(term):
    if re.search(r'\d+',term):
        return True
    else:
        return False

def normalize_numbers(term):
    newterm = re.sub("\d+","<NUMBER>",term)
    return newterm

def normalize(term, language):
    if language == "eng":
        term = remove_eng_determiners(term)
    elif language == "afr":
        term = remove_afr_determiners(term)
    term = normalize_numbers(term)
    return term
