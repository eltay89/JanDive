import json
import logging
import subprocess # nosec B404
import os
import re
import time
import configparser
from llama_cpp import Llama
from tools.search_tool import SearchTool
from tools.calculator_tool import CalculatorTool

# Use a dedicated logger for this module
logger = logging.getLogger(__name__)

# Instantiate tools
calc_tool = CalculatorTool()

def load_config():
    """Load configuration from config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    # Set defaults
    config['search'] = {
        'max_results': '5'
    }
    
    # Read config file if it exists
    if os.path.exists(config_path):
        config.read(config_path)
    
    return config

def has_nvidia_gpu():
    try:
        subprocess.run(['nvidia-smi'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=5) # nosec
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False

def load_llm(model_path, config):
    n_gpu_layers = -1 if has_nvidia_gpu() else 0
    n_ctx = config.getint('llm', 'n_ctx', fallback=8192)
    logger.info(f"Loading LLM with n_gpu_layers={n_gpu_layers} and n_ctx={n_ctx}")

    # Suppress llama.cpp warnings by redirecting stderr
    import sys
    import os
    
    original_stderr = sys.stderr
    sys.stderr = open(os.devnull, 'w')
    
    try:
        llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            n_batch=512,
            verbose=False
        )
    finally:
        # Restore stderr
        sys.stderr.close()
        sys.stderr = original_stderr
        
    return llm

def _get_search_queries(llm, user_query, max_queries=3):
    """Generate targeted search queries using the LLM, with robust fallback."""
    
    prompt = f"""
    Based on the user's query, generate {max_queries} diverse and effective search engine queries.
    The queries should be concise and cover different aspects of the original query.
    Return the queries as a JSON list of strings.

    User Query: "{user_query}"

    JSON Output:
    """

    try:
        response = llm.create_completion(
            prompt,
            max_tokens=150,
            temperature=0.4,
            stop=["\n"],
            echo=False
        )
        
        json_str = response['choices'][0]['text'].strip()
        
        try:
            queries = json.loads(json_str)
            if not isinstance(queries, list):
                queries = [str(queries)]
        except json.JSONDecodeError:
            logger.info(f"Failed to parse LLM output as JSON: '{json_str}'. Falling back to regex.")
            # Fallback: try to extract quoted strings
            queries = re.findall(r'"(.*?)"', json_str)
            if not queries:
                # If no quotes, use the whole line, split by common delimiters
                queries = re.split(r'[,\n;]', json_str)

        # Clean up, add original query, and remove duplicates
        cleaned_queries = [q.strip() for q in queries if q.strip()]
        cleaned_queries.insert(0, user_query)
        return list(dict.fromkeys(cleaned_queries))
        
    except Exception as e:
        logger.error(f"Error generating search queries with LLM: {e}")
        # Fallback to a simple method if LLM fails
        return [user_query]

def _summarize_text(llm, text, max_length=250):
    """Summarize a given text using the LLM."""
    prompt = f"Summarize the following text in under {max_length} words, focusing on the key facts and figures:\n\n{text}"
    
    try:
        response = llm.create_completion(
            prompt,
            max_tokens=max_length + 50, # Give some buffer
            temperature=0.3,
            stop=["\n"],
            echo=False
        )
        return response['choices'][0]['text'].strip()
    except Exception as e:
        logger.error(f"Error summarizing text: {e}")
        # Fallback to simple truncation if summarization fails
        return text[:max_length * 5] + '...'

def run_agent(query, llm=None, temperature=0.6, max_iterations=3, offline=False, status_callback=None, conversation_history=None, detail_level="standard"):
    def update_status(message):
        # Helper function to update status via callback and log it
        if status_callback:
            status_callback(message)
        logger.info(message)

    # Load configuration
    config = load_config()

    if llm is None:
        model_path = os.getenv('JANDIVE_MODEL_PATH', "models/janhq_Jan-v1-4B-Q4_K_M.gguf")
        update_status("loading_llm")
        try:
            llm = load_llm(model_path, config)
        except Exception as e:
            logger.error(f"Failed to load LLM: {e}")
            yield "Error: Failed to load language model.", []
            return

    # If offline or a simple math expression, use calculator directly
    if offline or (not any(c.isalpha() for c in query) and re.match(r'^[0-9+\-*/().\s]+$', query)):
        update_status("Performing calculation...")
        logger.info(f"Using calculator for expression: {query}")
        return str(calc_tool.execute(query)['result']), []

    context = ""
    sources = []
    unique_urls = set()

    search_tool = SearchTool(config=config)
    max_results = config.getint('search', 'max_results')

    update_status("planning")
    search_queries = _get_search_queries(llm, query)
    logger.info(f"Generated search queries: {search_queries}")

    for i, search_query in enumerate(search_queries):
        if i >= max_iterations:
            break
        
        update_status("searching")
        search_results = search_tool.execute(query=search_query, max_results=max_results)

        if not search_results or (isinstance(search_results, list) and search_results and "error" in search_results[0]):
            logger.warning("Search returned no results or an error on iteration %d.", i+1)
            break

        # Filter out results we've already processed
        new_results = [res for res in search_results if res.get('url') not in unique_urls]
        if not new_results:
            logger.info("No new unique search results found. Concluding search phase.")
            break
        
        update_status("processing")
        
        for res in new_results:
            unique_urls.add(res['url'])
            sources.append(res)
            content = res.get('content', res.get('snippet', ''))
            
            # Summarize content if it's too long
            if len(content.split()) > 400:
                content = _summarize_text(llm, content)

            source_index = len(sources)
            context += f"Source {source_index}: {res.get('url', 'N/A')}\nTitle: {res.get('title', 'N/A')}\nContent: {content}\n---"
        
        # Check if context is getting too large
        if len(context.split()) > 3000: # Approx token count
            logger.warning("Context is large, breaking search loop to generate report.")
            break

    if not sources:
        return "Could not find any information matching your query. Please try rephrasing it.", []

    update_status("generating")
    system_prompt = """You are a research assistant. Your sole purpose is to write a comprehensive report based *only* on the provided search results.

**Instructions:**
1.  **Strictly Adhere to Sources:** Base your entire report on the information given in the 'Source X' snippets. Do not add external knowledge.
2.  **Structure the Report:** Organize your response into:
    *   **Executive Summary:** A brief, high-level summary of the main findings.
    *   **Detailed Findings:** A thorough breakdown of the information, organized by key themes.
    *   **Conclusion:** A summary of the most important points.
3.  **Cite Everything:** For every piece of information you use, you MUST cite the source using the format `[Source X]`. Multiple sources can be cited like `[Source 1, 3]`. The URL is already included in the context; just use the number.
4.  **Synthesize, Don't List:** Do not simply list the sources. Weave the information together into a coherent narrative. If sources conflict, note the discrepancy.
5.  **Format with Markdown:** Use headers, bullet points, and bold text to make the report easy to read.
"""
    if detail_level == "concise":
        system_prompt += "\n\nFORMAT: Maximum 3 bullet points total. Be extremely concise."
    elif detail_level == "detailed":
        system_prompt += "\n\nFORMAT: Include specific statistics and direct quotes where available."
    
    # Prepend conversation history to the user prompt if it exists
    history_context = ""
    if conversation_history:
        history_context = "PREVIOUS CONVERSATION:\n"
        for q, a in conversation_history:
            history_context += f"User asked: {q}\nYou answered: {a}\n---\n"
        history_context += "CURRENT QUERY:\n"

    user_prompt = f"{history_context}Please write a detailed research report on the query: \"{query}\"\n\nUse the following search results as your only source of information:\n---\n{context}\n---"

    update_status("Generating final report...")
    response_stream = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        max_tokens=2048,
        stream=True  # Enable streaming
    )
    
    # Yield each token's content as it's generated
    for chunk in response_stream:
        delta = chunk["choices"][0].get("delta", {})
        content = delta.get("content")
        if content:
            yield content, sources

    # The conversation history will be updated in main.py after the full report is generated
