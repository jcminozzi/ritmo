"""Classificador de intenções: Naive Bayes multinomial, implementado para estudo."""
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
import unicodedata

STOPWORDS = set('a o as os de da do das dos e em um uma para por com que qual quais foi foram me mostre quero saber voce eu'.split())
STOPWORDS.update('janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro'.split())


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower())
                   if unicodedata.category(c) != 'Mn')


def features(text):
    words = [w for w in re.findall(r'[a-z]{2,}', normalize(text)) if w not in STOPWORDS]
    return words + [a+'_'+b for a,b in zip(words, words[1:])]


class IntentModel:
    def __init__(self, data):
        self.data = data

    @classmethod
    def train(cls, examples):
        documents = Counter()
        counts = defaultdict(Counter)
        vocabulary = set()
        for example in examples:
            label = example['intent']
            tokens = features(example['question'])
            documents[label] += 1
            counts[label].update(tokens)
            vocabulary.update(tokens)
        if len(documents) < 2 or not vocabulary:
            raise ValueError('Treino precisa de exemplos de pelo menos duas intenções.')
        total = sum(documents.values())
        classes = {}
        for label in sorted(documents):
            denominator = sum(counts[label].values()) + len(vocabulary)
            classes[label] = {
                'log_prior': math.log(documents[label]/total),
                'log_likelihood': {word:math.log((counts[label][word]+1)/denominator)
                                   for word in sorted(vocabulary)}
            }
        return cls({'algorithm':'multinomial-naive-bayes', 'alpha':1,
                    'training_examples':total, 'vocabulary':sorted(vocabulary), 'classes':classes})

    def predict(self, question):
        tokens = [w for w in features(question) if w in self.data['vocabulary']]
        if not tokens:
            return {'intent':'unclear', 'raw_intent':None, 'margin':0}
        scores = []
        for label, parameters in self.data['classes'].items():
            score = parameters['log_prior'] + sum(parameters['log_likelihood'][w] for w in tokens)
            scores.append((score, label))
        scores.sort(reverse=True)
        margin = scores[0][0]-scores[1][0]
        # A margin is a heuristic for abstention, not a calibrated probability.
        return {'intent':scores[0][1] if margin >= 0.6 else 'unclear',
                'raw_intent':scores[0][1], 'margin':round(margin, 4)}

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding='utf-8')))
