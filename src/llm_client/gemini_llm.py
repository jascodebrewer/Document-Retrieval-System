from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.string import StrOutputParser
import logging

# Initialize logger and load environment variables
logger=logging.getLogger(__name__)
load_dotenv()

def get_google_llm(model_id="gemini-2.5-flash"):
    '''
    Initialize Google Gemini LLM client for text generation.
    '''
    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    # Configure Gemini with deterministic responses and retry logic
    llm = ChatGoogleGenerativeAI(
        model=model_id,
        temperature=0,
        max_retries=2, # Retry failed requests up to 2
        google_api_key=api_key
    )
    return llm

def get_prompt_template(prompt_path):
    '''
    Load and parse prompt template from file.
    '''
    # Read prompt template from file
    with open(prompt_path, 'r', encoding='utf-8') as f:
        template=f.read()
    
    # Create LangChain prompt template
    prompt = ChatPromptTemplate.from_template(template=template)
    return prompt

def get_answer(query, llm, prompt, content):
    '''
    Generate answer using RAG pipeline with retrieved context.
    '''
    # Create processing chain: prompt -> LLM -> string output
    chain = prompt | llm | StrOutputParser()
    
    # Invoke chain with user query and retrieved context
    response=chain.invoke({
                    'query':query,
                    'context':content
                        })
    logger.info(f"The response for the query: {query} is: \n\n {response}")
    return response