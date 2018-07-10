#named entity recognition module


from nltk import ne_chunk_sents


SUPPORTED = [
        'eng',
]


class NERtagger:
    def __init__(self, language):
        self.language = language

    def parse_tree(self, tree):
        tree_entities = []
        if hasattr(tree, 'label') and tree.label:
            #if we use binary=False below (multiclass classifier), then the
            #possibilities (might) include:
            # ORGANIZATION, PERSON, LOCATION, DATE, TIME, MONEY, and GPE
            # (geo-political entity).
            # Full list: http://www.nltk.org/book/ch07.html#tab-ne-types
            if tree.label() == 'PERSON':
                value = u" ".join(x[0] for x in tree.leaves())
                tree_entities.append(' '.join([child[0] for child in tree]))
            else:
                for child in tree:
                    tree_entities.extend(self.parse_tree(child))
        return tree_entities

    def parse(self, pos_tagged_sentences):
        if not self.language in SUPPORTED:
            return set()

        chunked_sentences = ne_chunk_sents(pos_tagged_sentences, binary=False)
        entities = []
        for tree in chunked_sentences:
            entities.extend(self.parse_tree(tree))
        return set(entities)

