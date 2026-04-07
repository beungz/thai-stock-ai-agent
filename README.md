# AIPI 590: Assignment 3: Thai Stock AI Agent
### **Author**: Matana Pornluanprasert

The AI agent is designed to interact with a suite of tools for stock data retrieval, individual Thai stock analysis and comparables, enabling it to answer questions about specified stocks based on current or historical data. The tools allow the agent to perform various financial data retrieval and comparisons, including trading stats, profitability, balance sheet, and dividends. The project includes a Streamlit interface for user interaction and is evaluated on its ability to provide accurate answers to financial and investment queries.<br>


***
# Objective of Agent<br>
To provide a fully autonomous, privacy-first financial assistant capable of bridging the gap between raw web data and natural language. The agent is designed to intelligently plan data retrieval steps, execute local web scraping scripts in real-time, aggregate complex financial metrics, and present the findings to the user in a clear, formatted, and conversational manner without relying on paid APIs.
<br>

***
# Data Source<br>
All data comes from the official Stock Exchange of Thailand. Web scraping is used to collect the data.<br>
https://www.set.or.th/<br>

***
# Structure of Agent Code<br>
The codebase is modularized to separate data extraction, state management, reasoning, and the user interface:
1. **`SETStockData`:** Handles headless browser navigation, dynamic scrolling, and BeautifulSoup parsing to extract raw HTML tables.
2. **`SETPeerComparator`:** Cleans, pivots, and aggregates the raw DataFrames into targeted comparison matrices.
3. **`SETAgentTools`:** A stateful wrapper that sits between the LLM and the scraper. It caches heavy web payloads in RAM and feeds only lightweight metadata to the LLM's context window.
4. **`LocalFinancialAgent`:** The core agent loop. It manages the prompt history, injects the JSON tool registry, parses the LLM's `<action>` tags, and feeds observations back to the model.
5. **`app.py`:** The Streamlit frontend that manages session state, renders the chat interface, and safely handles browser lifecycle events.

***
# Agent Flow<br>
The agent operates on a continuous Reason + Act paradigm:
1. **Understand:** The LLM receives the user prompt alongside the JSON schema of available tools.
2. **Plan & Act:** If data is missing, the LLM outputs an `<action>` block containing the tool name and JSON arguments.
3. **Execute:** The Python framework intercepts the action, executes the corresponding scraper/comparator function, and caches the result.
4. **Observe:** The execution result (the "Observation") is fed back to the LLM.
5. **Synthesize:** The LLM evaluates the observation. If more data is needed, it loops back to step 2. If the data is sufficient, it generates the final Markdown response for the user.

***
# UI Design Considerations<br>
* **Non-Blocking Execution:** Implemented Streamlit `st.status` containers to display the agent's intermediate thought processes and tool executions. This keeps the user informed during multi-second scraping tasks without cluttering the final chat history.
* **Session Persistence:** Both the Chromedriver instance and the agent's memory are tied to Streamlit's `session_state`, ensuring the browser remains warm and ready across multiple chat interactions.
* **Clean Markdown Rendering:** The UI is explicitly prompted to render raw DataFrame outputs as clean Markdown tables, ensuring financial data is highly legible.

***
# Design Choices<br>
* **Custom Framework:** Built entirely from scratch in Python to maintain granular control over the reasoning loop, tool execution, and context window limits.
* **Stateful Caching:** Implemented an in-memory caching system between the agent and the scraper. This prevents redundant web requests, drastically speeds up multi-step queries (like peer comparisons), and minimizes the risk of IP bans.
* **Strict JSON Parsing:** Tool calls are isolated using custom XML tags (`<action>`) and strict JSON schemas, protecting the execution pipeline from LLM conversational hallucinations.

***
# Model Selection<br>
Deployed entirely locally using Ollama to ensure data privacy and zero API costs. To find the optimal balance of reasoning, tool-calling accuracy, and hardware efficiency (fitting comfortably within a 16GB GPU VRAM limit), five state-of-the-art open-weight models were evaluated:<br>

* **`qwen2.5:14b-instruct` (Champion Model):** Selected as the primary agent for its exceptional balance of conversational roleplay (ReAct framework) and strict adherence to complex JSON schemas and XML `<action>` tags.<br>
* **`qwen2.5-coder:14b`:** Evaluated for its elite JSON and coding capabilities, though it proved too literal for the conversational flow required by the ReAct prompting structure.<br>
* **`qwen2.5:7b`:** Tested as a lightweight, high-speed baseline to validate the efficiency and baseline intelligence of the underlying Qwen 2.5 architecture.<br>
* **`gemma2:9b`:** Included as a highly efficient generalist model to test its advanced reasoning capabilities within a compact, sub-10B parameter count.<br>
* **`mistral-nemo:12b`:** A robust benchmark model with a large context window, evaluated to compare standard generalist reasoning against Qwen's specialized tool-calling.<br>

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

***
# Agent Performance Evaluation<br>

The agent's routing logic and parameter extraction were rigorously tested against a 50-question evaluation dataset. The tests span five levels of difficulty, ranging from simple single-tool retrieval to complex, multi-step peer discovery loops.

To optimize performance, the system prompt and JSON function registry were revised to strictly enforce autonomous execution (preventing the agent from pausing to ask the user for permission) and to clarify list/array handling for multi-year queries.

The table below summarizes the **Trajectory Evaluation Score** (whether the agent successfully called the correct sequence of tools with the exact required arguments) before and after these prompt engineering revisions.

| **Model** | **Trajectory Score (Before Revision)** | **Trajectory Score (After Revision)** | **Human Evaluation Result (Correctness)** | 
| :--- | :---: | :---: | :---: |
| **`gemma2:9b`** | 14/50 (28.0%) | 25/50 (50.0%) | 7/50 (14.0%) | 
| **`mistral-nemo:12b`** | 14/50 (28.0%) | 9/50 (18.0%) | 3/50 (6.0%) | 
| **`qwen2.5:7b`** | 26/50 (52.0%) | 42/50 (84.0%) | 24/50 (48.0%) | 
| **`qwen2.5-coder:14b`** | 23/50 (46.0%) | 31/50 (62.0%) | 18/50 (36.0%) | 
| **`qwen2.5:14b-instruct`** | 35/50 (70.0%) | 39/50 (78.0%) | 32/50 (64.0%) |

The `qwen2.5` architecture demonstrated superior obedience to the ReAct `<action>` XML formatting and JSON schemas compared to other generalist models.<br>

**Key Observations from the Manual Evaluation**:
* **Unit Hallucinations (Test 21, 31):** Several models failed because they dropped the "million" designation (e.g., stating `528,531 THB` instead of `528,531 million THB` or inventing abbreviations like `B THB` for billion instead of million). 
* **Premature Stopping (Tests 48-50):** The agents often successfully executed the tools, found the list of peers, but then ended their turn with *"Here is the list. Would you like me to generate a table?"* instead of just outputting the table directly.
* **`qwen2.5:14b-instruct`** maintained its lead as the strongest model, not only in routing tools correctly but also in surfacing the final numbers cleanly to the user.


<br>

***
# Ethics statement<br>
This project is intended for research and educational purposes in large language model and intelligent agent development. All data collection and deployment are conducted with respect for privacy and copyright. Care has been taken to avoid misuse of the model and to ensure responsible use of the technology, particularly in relation to surveillance, personal data, and public safety.<br>
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
tabulate==0.10.0
```

### **How to run the code**:<br>
***

To run the agent with streamlit interface, type the following in the terminal<br>

```
streamlit run app.py
```
Then the interface will be shown in local web browser. User can type in a question and get answer responded by the agent.

***
