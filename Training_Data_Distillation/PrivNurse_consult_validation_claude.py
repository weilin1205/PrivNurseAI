import anthropic
import json
import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

client = anthropic.Anthropic(
    api_key="YOUR_API_KEY",
)

print_lock = Lock()

def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)
        # 強制刷新輸出
        print('', flush=True, end='')

def process_row(index, row):
    start_time = time.time()
    safe_print(f"Starting #{index + 1}")
    original = row['original']
    summary = row['summary']
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        temperature=0,
        system="Extract the exact phrases or sentences from the [original] text that correspond to the information summarized in the [summary]. Present these extracted phrases as an array of strings in JSON format, with the key 'relevant_text'. Do not output anything other than the JSON array.",
        messages=[
            {
                "role": "user",
                "content": f"[original] \n{original}\n\n[summary] \n{summary}"
            }
        ]
    )
    text_content = message.content[0].text
    try:
        parsed_content = json.loads(text_content)
        result = json.dumps(parsed_content, ensure_ascii=False)
    except json.JSONDecodeError:
        safe_print(f"Error: Invalid JSON output from Claude for input: {original[:50]}...")
        result = None
    
    end_time = time.time()
    safe_print(f"Finished #{index + 1} in {end_time - start_time:.2f} seconds")
    return result

# Input and output file paths
input_file = '會診紀錄-1.csv'
output_file = 'output_test.csv'

# Read all rows from input CSV
with open(input_file, 'r', encoding='utf-8-sig') as infile:
    reader = csv.DictReader(infile)
    rows = list(reader)[:10]  # Only process the first 10 rows

# Process rows concurrently
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(process_row, i, row) for i, row in enumerate(rows)]
    
    # Write results to output CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        fieldnames = reader.fieldnames + ['claude_output']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for i, (row, future) in enumerate(zip(rows, futures)):
            claude_output = future.result()
            if claude_output:
                row['claude_output'] = claude_output
            else:
                safe_print(f"Invalid JSON output for row #{i + 1}, skipping this row.")
                row['claude_output'] = ''
            writer.writerow(row)

safe_print(f"Processing complete. Results saved to {output_file}")