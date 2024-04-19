from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI


def create_summarize_chain():
    # Prompt
    prompt_text = """You are an assistant tasked with summarizing tables and text. \ 
    Give a concise summary of the table or text. Table or text chunk: {element} """
    prompt = ChatPromptTemplate.from_template(prompt_text)

    # Summary chain
    model = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
    return {"element": lambda x: x} | prompt | model | StrOutputParser()


