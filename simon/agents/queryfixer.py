"""
queryfixer.py
Performs the act of answering a question by querying
"""
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.output_parsers import CommaSeparatedListOutputParser
from langchain.prompts import StringPromptTemplate
from langchain.schema import BaseOutputParser
import re

from ..models import *


TEMPLATE = """
System:
The knowledge base contains information about specific terms and general information. For instance, "my coworker Bob", "Bob's preferences for socks", "eigenvalues", and "last year's tax return" are all valid information in the knowledge base. "last year's tax return" is a valid entry in the knowledgebase while "an excel sheet for last year's tax return" is not.

You will be provided a partial slice of the human's notes and thoughts; your job is to identify what the human is actually trying to do, and convert that to a more genreal question or statement that uses only keywords that could be found in the knowledge base.

Here are few examples of successful conversions:
- "What's an eigenvalue?" => "Eigenvalues"
- "Tell me about Zorbabs" => "Zorbabs"
- "I'm traveling to Singapore next week! What should I do?" => "Singapore"
- "Who should I visit in Bangkok?" => "people I know in Bangkok"

Provide your output in this format:

```output
your full, new question/statement here
```

Begin!

Human:
Here are some supporting information:
{entities}
Here is the question to answer:
{input}

AI:
"""

class QueryPromptFormatter(StringPromptTemplate):
    def format(self, **kwargs):
        entities = "\n".join([
            f"{key}: {value}"
            for key,value in kwargs.pop("entities").items()])
        return TEMPLATE.format(input=kwargs["input"],
                               entities=entities)

class QueryOutputParser(BaseOutputParser):
    def parse(self, str):
        str = str.strip("```output").strip("`").strip("'").strip('"').strip()

        return str

class QueryFixer(object):
    def __init__(self, context, verbose=False):
        """Context-Aware follow-up assistant

        Parameters
        ----------
        context : AgentContext
            The context to operate the RIO under
        verbose : bool
            Whether the chain should be verbose
        """
        
        prompt = QueryPromptFormatter(input_variables=["entities", "input"],
                                      output_parser=QueryOutputParser())
        self.__chain = LLMChain(llm=context.llm, prompt=prompt, verbose=verbose)

    def __call__(self, question, entities={}):
        return self.__chain.predict_and_parse(input=question,
                                              entities=entities)