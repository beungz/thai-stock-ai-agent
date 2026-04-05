# AIPI 590: Assignment 3: Thailand's Stock AI Agent
### **Author**: Matana Pornluanprasert

The AI agent is designed to interact with a suite of tools for share data retrieval, individual Thai stock analysis and comparables, enabling it to answer questions about specified stocks based on current or historical data. The tools allows the agent to perform various financial analyses and comparisons, including trading stats, profitability, balance sheet, and dividends. The project includes a Streamlit interface for user interaction and is evaluated on its ability to provide accurate and insightful answers to financial queries.<br>


***
# Objective of Agent<br>
To provide a fully autonomous, privacy-first financial assistant capable of bridging the gap between raw web data and natural language. The agent is designed to intelligently plan data retrieval steps, execute local web scraping scripts in real-time, aggregate complex financial metrics, and present the findings to the user in a clear, formatted, and conversational manner without relying on paid APIs.
<br>

***
# Data Source<br>
All data comes from the official Stock Exchage of Thailand. Web scraping is used to collect the data.<br>
https://www.set.or.th/<br>

***
# Structure of Agent Code<br>
The codebase is modularized to separate data extraction, state management, reasoning, and the user interface:
1. **`SETStockData`:** Handles headless browser navigation, dynamic scrolling, and BeautifulSoup parsing to extract raw HTML tables.
2. **`SETPeerComparator`:** Cleans, pivots, and aggregates the raw DataFrames into targeted comparison matrices.
3. **`SETAgentTools`:** A stateful wrapper that sits between the LLM and the scraper. It caches heavy web payloads in RAM and feeds only lightweight metadata to the LLM's context window.
4. **`LocalFinancialAgent`:** The core agent loop. It manages the prompt history, injects the JSON tool registry, parses the LLM's `<action>` tags, and feeds observations back to the model.
5. **`app.py`:** The Streamlit frontend that manages session state, renders the chat interface, and safely handles browser lifecycle events.
<br>

***
# Agent Flow<br>
The agent operates on a continuous Reason + Act paradigm:
1. **Understand:** The LLM receives the user prompt alongside the JSON schema of available tools.
2. **Plan & Act:** If data is missing, the LLM outputs an `<action>` block containing the tool name and JSON arguments.
3. **Execute:** The Python framework intercepts the action, executes the corresponding scraper/comparator function, and caches the result.
4. **Observe:** The execution result (the "Observation") is fed back to the LLM.
5. **Synthesize:** The LLM evaluates the observation. If more data is needed, it loops back to step 2. If the data is sufficient, it generates the final Markdown response for the user.
<br>

***
# UI Design Considerations<br>
* **Non-Blocking Execution:** Implemented Streamlit `st.status` containers to display the agent's intermediate thought processes and tool executions. This keeps the user informed during multi-second scraping tasks without cluttering the final chat history.
* **Session Persistence:** Both the Chromedriver instance and the agent's memory are tied to Streamlit's `session_state`, ensuring the browser remains warm and ready across multiple chat interactions.
* **Clean Markdown Rendering:** The UI is explicitly prompted to render raw DataFrame outputs as clean Markdown tables, ensuring financial data is highly legible.
<br>

***
# Design Choices<br>
* **Custom Framework:** Built entirely from scratch in Python to maintain granular control over the reasoning loop, tool execution, and context window limits.
* **Stateful Caching:** Implemented an in-memory caching system between the agent and the scraper. This prevents redundant web requests, drastically speeds up multi-step queries (like peer comparisons), and minimizes the risk of IP bans.
* **Strict JSON Parsing:** Tool calls are isolated using custom XML tags (`<action>`) and strict JSON schemas, protecting the execution pipeline from LLM conversational hallucinations.
<br>

***
# Model Selection<br>

[To update]<br>

Deployed entirely locally using Ollama to ensure data privacy, and zero API costs<br>
* **Agent Model:** `qwen2.5:7b` (or equivalent 7B/8B models like Llama 3.1). Selected for its state-of-the-art tool-calling capabilities and adherence to JSON schemas, while fitting comfortably within consumer GPU VRAM limits (8GB).<br>

* **Evaluator Model (Judge):** `qwen2.5:32b`. Used strictly for the automated evaluation pipeline. Selected for its superior, near-GPT-4 reasoning capabilities and strict JSON output formatting.<br>
<br>

***
# Tools<br>

The agent determines when and how to use the following tools based on a dynamic JSON registry:
* `get_full_report`: Fetches comprehensive financial tables and metadata for a specific stock ticker.
* `get_sector_index_links`: Retrieves the master map of all SET sectors and subsectors.
* `get_index_members`: Extracts a list of competitor stock tickers from a specific subsector URL.
* `trading_comparables`: Generates a Markdown table comparing Price, Market Cap, P/E, P/BV, and Beta.
* `profitability_comparables`: Compares Total Revenues, EBITDA, Net Profit, ROE, ROA, and Margins.
* `balance_sheet_comparables`: Compares Cash, Assets, Liabilities, Equity, and D/E ratios.
* `dividend_comparables`: Analyzes Dividend Yield, Payout Ratios, and extracts official Dividend Policies.
<br>

***
# Agent Performance Evaluation<br>

[To update]<br>

The agent is continuously tested using a custom, two-tiered automated evaluation pipeline:
1. **Trajectory (Routing) Evaluation:** Verifies the agent's logic. It tests whether the agent parsed the prompt correctly and selected the exact required sequence of tools (e.g., executing peer discovery tools before calling comparison tables).
2. **Output (Generation) Evaluation:** Utilizes an **LLM-as-a-Judge** framework. The 32B evaluator model cross-references the agent's final answer against the raw, live-scraped ground truth data to grade it on Factuality (zero hallucinations), Completeness, and Format Adherence (e.g., proper Markdown tables).
<br>

***
# Ethics statement<br>
This project is intended for research and educational purposes in large language model and intelligent agent development. All data collection and deployment are conducted with respect for privacy and copyright. Care has been taken to avoid misuse of the model and to ensure responsible use of the technology, particularly in relation to surveilance, personal data, and public safety.<br>
<br>


***
# Requirements and How to run the code

### **Requirements**:<br>
```
pandas==2.3.0
lxml==6.0.0
html5lib==1.1
beautifulsoup4==4.13.4
selenium==4.41.0
undetected-chromedriver==3.5.5
ollama==0.6.1
streamlit==1.45.1
```
<br>

### **How to run the code**:<br>
***

To run the agent with streamlit interface:<br>

```
streamlit run app.py
```

<br>


***
