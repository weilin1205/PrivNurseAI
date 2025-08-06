import json
import re
import logging
import aiohttp
from config import GENERATE_URL, TAGS_URL

logger = logging.getLogger(__name__)

class OllamaService:
    """Service class for interacting with Ollama API"""
    
    def __init__(self):
        self.generate_url = GENERATE_URL
        self.tags_url = TAGS_URL
    
    async def generate_stream(self, model: str, prompt: str):
        """Generate streaming response from Ollama"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }
        
        print(f"DEBUG OLLAMA: Starting streaming generation with model: {model}")
        print(f"DEBUG OLLAMA: URL: {self.generate_url}")
        print(f"DEBUG OLLAMA: Prompt length: {len(prompt)}")
        
        async with aiohttp.ClientSession() as session:
            try:
                print(f"DEBUG OLLAMA: Sending POST request to {self.generate_url}")
                async with session.post(self.generate_url, json=payload) as response:
                    print(f"DEBUG OLLAMA: Response status: {response.status}")
                    print(f"DEBUG OLLAMA: Response headers: {dict(response.headers)}")
                    
                    if response.status != 200:
                        error_msg = f"API request failed with status {response.status}"
                        response_text = await response.text()
                        print(f"DEBUG OLLAMA: Error response body: {response_text}")
                        logger.error(error_msg)
                        yield f'{{"model": "{model}", "created_at": "2024-01-01T00:00:00Z", "response": "Error: {error_msg}", "done": true}}\n'
                        return
                    
                    line_count = 0
                    async for line in response.content:
                        if line:
                            line_count += 1
                            try:
                                # Decode and yield the JSON line
                                json_str = line.decode('utf-8').strip()
                                if json_str:
                                    if line_count <= 3:  # Log first few lines
                                        print(f"DEBUG OLLAMA: Line {line_count}: {json_str[:200]}...")
                                    # Validate JSON format
                                    parsed_json = json.loads(json_str)
                                    yield f"{json_str}\n"
                            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                                print(f"DEBUG OLLAMA: Error processing line {line_count}: {e}")
                                print(f"DEBUG OLLAMA: Problematic line: {line}")
                                logger.error(f"Error processing line: {e}")
                                continue
                    
                    print(f"DEBUG OLLAMA: Processed {line_count} lines total")
                                
            except Exception as e:
                print(f"DEBUG OLLAMA: Exception during streaming: {str(e)}")
                import traceback
                traceback.print_exc()
                logger.exception("Error during streaming generation")
                error_response = {
                    "model": model,
                    "created_at": "2024-01-01T00:00:00Z", 
                    "response": f"Error during generation: {str(e)}",
                    "done": True
                }
                yield f"{json.dumps(error_response)}\n"
    
    async def generate_completion(self, model: str, prompt: str) -> str:
        """Generate a complete (non-streaming) response from Ollama"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        logger.debug(f"Generating completion with model: {model}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.generate_url, json=payload) as response:
                    if response.status != 200:
                        error_msg = f"API request failed with status {response.status}"
                        logger.error(error_msg)
                        return error_msg
                    
                    response_data = await response.json()
                    return response_data.get('response', '')
                    
            except Exception as e:
                logger.exception("Error during completion generation")
                return f"Error during generation: {str(e)}"

async def validation_text(original: str, summary: str, model: str):
    """Validate text using Ollama API"""
    logger.info("="*80)
    logger.info("VALIDATION_TEXT DEBUG - Start")
    logger.info(f"Model: {model}")
    logger.info(f"Original text length: {len(original)}")
    logger.info(f"Summary text length: {len(summary)}")
    
    # Check if summary contains <answer> tags and extract content if present
    answer_pattern = re.search(r'<answer>(.*?)</answer>', summary, re.DOTALL)
    if answer_pattern:
        extracted_summary = answer_pattern.group(1).strip()
        logger.info(f"Found <answer> tags in summary. Extracted content length: {len(extracted_summary)}")
        summary = extracted_summary
    else:
        logger.info("No <answer> tags found in summary")

    prompt = f"#申請會診單：\n{original}\n\n#護理師確認結果：\n{summary}"

    logger.info(f"Generated prompt length: {len(prompt)} characters")
    logger.info(f"Full prompt:\n{'-'*40}\n{prompt}\n{'-'*40}")

    async with aiohttp.ClientSession() as session:
        try:
            logger.info("Sending API request to Ollama...")
            response = await send_api_request(session, prompt, model)
            logger.info(f"API request completed. Response keys: {list(response.keys())}")
        except Exception as e:
            logger.exception("Error during API call")
            return {"error": str(e)}

    if response.get("error"):
        logger.error(f"API returned error: {response['error']}")
        return response

    logger.info(f"Full API response length: {len(response.get('full_response', ''))} characters")
    logger.info(f"Full API response:\n{'-'*40}\n{response.get('full_response', '')}\n{'-'*40}")

    try:
        relevant_text = extract_relevant_text(response["full_response"])
        logger.info(f"Successfully extracted relevant_text: {relevant_text}")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing full response as JSON: {e}")
        logger.error(f"Response that failed to parse: {response.get('full_response', '')[:500]}...")
        return {"error": "Error parsing full response as JSON"}

    if not relevant_text:
        logger.error("No 'relevant_text' field found in the API response")
        logger.error(f"Response structure: {response.get('full_response', '')[:500]}...")
        return {"error": "No 'relevant_text' field in the API response"}

    logger.info("VALIDATION_TEXT DEBUG - End")
    logger.info("="*80)
    return {"relevant_text": relevant_text}

async def send_api_request(session, prompt, model):
    """Send request to Ollama API"""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    logger.info(f"SEND_API_REQUEST DEBUG:")
    logger.info(f"  URL: {GENERATE_URL}")
    logger.info(f"  Model: {model}")
    logger.info(f"  Prompt length: {len(prompt)} characters")
    logger.info(f"  Stream: False")

    try:
        logger.info(f"Sending POST request to Ollama...")
        async with session.post(GENERATE_URL, json=payload) as response:
            logger.info(f"Response status: {response.status}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if response.status != 200:
                error_body = await response.text()
                logger.error(f"API request failed with status {response.status}")
                logger.error(f"Error response body: {error_body}")
                return {"error": f"API request failed with status {response.status}. Body: {error_body}"}

            full_response = await accumulate_response(response)
            logger.info(f"Successfully received response")
            logger.info(f"Response preview: {full_response[:500]}..." if len(full_response) > 500 else f"Full response: {full_response}")
            return {"full_response": full_response}
    except Exception as e:
        logger.exception("Error during API request")
        return {"error": str(e)}

async def accumulate_response(response):
    """Accumulate streaming response"""
    full_response = ""
    line_count = 0
    logger.info("ACCUMULATE_RESPONSE DEBUG: Starting to read response...")
    
    async for line in response.content:
        if line:
            line_count += 1
            try:
                data = json.loads(line)
                logger.info(f"  Line {line_count}: {json.dumps(data)[:200]}...")
                if 'response' in data:
                    full_response += data['response']
                    logger.info(f"  Accumulated response length: {len(full_response)}")
            except json.JSONDecodeError as e:
                logger.error(f"  Failed to parse line {line_count}: {e}")
                logger.error(f"  Raw line: {line}")
    
    logger.info(f"ACCUMULATE_RESPONSE DEBUG: Finished. Total lines: {line_count}, Total response length: {len(full_response)}")
    return full_response

def extract_relevant_text(full_response):
    """Extract relevant text from response"""
    logger.info("EXTRACT_RELEVANT_TEXT DEBUG:")
    logger.info(f"  Input length: {len(full_response)} characters")
    logger.info(f"  Input preview: {full_response[:200]}...")
    
    try:
        # First attempt: try to parse as-is
        parsed_response = json.loads(full_response)
        logger.info(f"  Successfully parsed JSON on first attempt")
        logger.info(f"  Parsed keys: {list(parsed_response.keys())}")
        logger.info(f"  Full parsed response: {json.dumps(parsed_response, ensure_ascii=False, indent=2)}")
        
        relevant_text = parsed_response.get('relevant_text')
        if relevant_text:
            logger.info(f"  Found relevant_text: {relevant_text}")
        else:
            logger.warning(f"  No relevant_text field in parsed response")
            
        return relevant_text
    except json.JSONDecodeError as e:
        logger.warning(f"  Initial JSON decode failed: {e}")
        logger.info(f"  Attempting to fix common escape issues...")
        
        # Second attempt: try to fix common escape issues
        try:
            # Replace problematic escape sequences
            # Common medical/prescription symbols that might be escaped
            fixed_response = full_response
            replacements = [
                ('\\#', '#'),      # Prescription number sign
                ('\\*', '*'),      # Asterisk
                ('\\&', '&'),      # Ampersand
                ('\\%', '%'),      # Percent
                ('\\@', '@'),      # At sign
                ('\\_', '_'),      # Underscore
                ('\\~', '~'),      # Tilde
                ('\\$', '$'),      # Dollar sign
            ]
            
            for old, new in replacements:
                if old in fixed_response:
                    fixed_response = fixed_response.replace(old, new)
                    logger.info(f"  Replaced {old} with {new}")
            
            parsed_response = json.loads(fixed_response)
            logger.info(f"  Successfully parsed JSON after fixing escapes")
            logger.info(f"  Parsed keys: {list(parsed_response.keys())}")
            logger.info(f"  Full parsed response: {json.dumps(parsed_response, ensure_ascii=False, indent=2)}")
            
            relevant_text = parsed_response.get('relevant_text')
            if relevant_text:
                logger.info(f"  Found relevant_text: {relevant_text}")
            else:
                logger.warning(f"  No relevant_text field in parsed response")
                
            return relevant_text
        except json.JSONDecodeError as e2:
            logger.error(f"  JSON decode error even after escape fixes: {e2}")
            logger.error(f"  Original response: {full_response[:500]}...")
            logger.error(f"  Fixed response: {fixed_response[:500]}...")
            # Try one more time with raw string literal interpretation
            try:
                logger.info(f"  Final attempt: treating as raw string and using ast.literal_eval")
                import ast
                # Convert the JSON-like string to a Python dict using ast
                # First make it a valid Python literal
                python_str = fixed_response.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                parsed_response = ast.literal_eval(python_str)
                relevant_text = parsed_response.get('relevant_text')
                if relevant_text:
                    logger.info(f"  Found relevant_text using ast.literal_eval: {relevant_text}")
                    return relevant_text
            except Exception as e3:
                logger.error(f"  ast.literal_eval also failed: {e3}")
            raise e2