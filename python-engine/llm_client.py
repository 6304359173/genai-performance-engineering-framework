import os
from dotenv import load_dotenv
from openai import OpenAI

# Load variables from .env
load_dotenv()

# Read API key
api_key = os.getenv("OPENAI_API_KEY")

# Check API key
if not api_key or api_key == "YOUR_API_KEY_HERE":
    print("ERROR: OpenAI API key is not configured.")
    print("Please update the .env file.")
    exit()

# Create OpenAI client
client = OpenAI(api_key=api_key)

# Read RCA prompt
with open("E:\\ai-perf-framework\\ai-engine\\rca_prompt.txt",
          "r", encoding="utf-8") as file:
    prompt = file.read()

# Send prompt to LLM
response = client.responses.create(
    model="gpt-5.6",
    input=prompt
)

# Get AI response
ai_report = response.output_text

# Save AI-generated report
output_file = "E:\\ai-perf-framework\\reports\\ai_llm_rca_report.md"

with open(output_file, "w", encoding="utf-8") as file:
    file.write(ai_report)

print("====================================")
print(" AI LLM RCA Engine")
print("====================================")
print()
print("AI RCA report generated successfully.")
print()
print(f"Report: {output_file}")