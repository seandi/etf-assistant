from typing import Dict, List, Tuple
from app.backend.config import DB_DIALECT

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI

TEMPLATE = """
Given the {dialect} query reported below, your task is to extract all values being used as filtering condition by a LIKE, IN or = operator within a WHERE clasues.
You should return a json object with a single key 'filters' containing the list of filters found matching the given condition.
In particular, each element in the list must contain:
- a field 'column' with the column on which the filtering condition is being applied 
- a field 'value' with the value being used as filtering condition in the LIKE, IN or = operator
For the IN operator you should treat each element as its own individual filter.

Query:
{query}

"""


class QueryFilter(BaseModel):
    column: str
    value: str


class QueryFilters(BaseModel):
    filters: List[QueryFilter]


class FilterExtractionChain:
    def __init__(self) -> None:
        self.chain = PromptTemplate.from_template(
            TEMPLATE
        ) | ChatOpenAI().with_structured_output(QueryFilters, method="json_mode")

    def run(self, query, callbacks: Dict | None = None) -> QueryFilters:
        return self.chain.invoke(
            {"query": query, "dialect": DB_DIALECT},
            config={"callbacks": callbacks},
        )
