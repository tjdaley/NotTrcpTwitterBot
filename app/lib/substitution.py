"""
substitution.py - Create phrases from vocabulary.
"""
__author__ = "Thomas J. Daley, J.D."
__version__ = "0.0.1"

import random

class PhraseMaker(object):
    """
    Encapsulates a phrase maker's behavior.
    """
    def __init__(self, vocabulary:dict, substitution_max:int=100):
        """
        Class initializer.

        Args:
            vocabulary (dict): Key is word that will appear in templates. Value is a list of synonyms.
            substitution_max (int): Maximum substitutions the make() method will peform.
                Used to prevent accidental end-less looping. Default = 100.

        Raises:
            ValueError: If substitution_max < 1 or > 1000.
        """
        if substitution_max < 1 or substitution_max > 1000:
            raise ValueError("substitution_max must be betweein 1 and 1000, inclusive.")

        self.vocabulary = vocabulary
        self.substitution_max = substitution_max

    def make(self, template:str, quantity:int)->str:
        """
        Substitute words in a template for randomly selected synonyms from our vocabulary.

        Args:
            template (str): Message with double curly-braces around variables, "{{GREETING}}, Tom."
            quantity (int): Used to determine whether to use plural or singular version of words

        Raises:
            KeyError: If keyword inside curley braces is not found in the vocabulary.
        
        Returns:
            (str): The final phrase.
        """
        result = "" + template

        # Find first opening delimiter
        open_position = result.find("{{")

        # Continue for as long as we have an opening delimiter and we have not reached a substitution max.
        substitution_count = 0
        while open_position != -1:

            # Find closing delimiter
            close_position = result.find("}}")

            # If not found, we have an improperl formatted string. We're done.
            if close_position == -1:
                return result

            # Pick out the key-word. Raise error if not in our vocabulary.
            keyword = result[open_position+2:close_position]
            if keyword not in self.vocabulary:
                raise KeyError("{} not found in vocabulary.".format(keyword))
            
            # Pick a random replacement.
            new_word = random.choice(self.vocabulary[keyword])

            # If the replacement is an array, first element is singular, second element is plural.
            if isinstance(new_word, list):
                if quantity == 1:
                    new_word = new_word[0]
                else:
                    new_word = new_word[1]

            result = "".join([result[0:open_position], new_word, result[close_position+2:]])
            substitution_count += 1
            open_position = result.find("{{")
        
        return result
            