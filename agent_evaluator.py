import datetime
import json
import os
import re
import time
from set_agent import SETStockData, SETAgentTools, LocalFinancialAgent



# Trajectory & Arguments Evaluation Dataset

evaluation_dataset = [
    # TYPE 1: Specific parameter(s), specified ticker, specified year (or current)
    {"prompt": "What is the P/E and P/Bv for SCC in 2024?", "expected_tools": ["trading_comparables"], "expected_args": {"peers": ["SCC"], "year": 2024}},
    {"prompt": "Can you find the Gross profit margin (GPM) and net profit margin (NPM) for PTT in 2023?", "expected_tools": ["profitability_comparables"], "expected_args": {"peers": ["PTT"], "year": 2023}},
    {"prompt": "What is the dividend policy and current dividend yield of SCB for 2025?", "expected_tools": ["dividend_comparables"], "expected_args": {"peers": ["SCB"], "year": 2025}},
    {"prompt": "Give me the Revenue and Net profit of AOT in 2024.", "expected_tools": ["profitability_comparables"], "expected_args": {"peers": ["AOT"], "year": 2024}},
    {"prompt": "Who is the CEO and Chairman of BEM?", "expected_tools": ["get_full_report"], "expected_args": {"symbol": "BEM"}},
    {"prompt": "Show me the D/E ratio and Cash outstanding for CPN in 2023.", "expected_tools": ["balance_sheet_comparables"], "expected_args": {"peers": ["CPN"], "year": 2023}},
    {"prompt": "What is the current foreign shareholding and foreign limit for BDMS?", "expected_tools": ["get_full_report"], "expected_args": {"symbol": "BDMS"}},
    {"prompt": "Tell me the audit company and business description of DUSIT.", "expected_tools": ["get_full_report"], "expected_args": {"symbol": "DUSIT"}},
    {"prompt": "What is the sector/subsector and company website for WHA?", "expected_tools": ["get_full_report"], "expected_args": {"symbol": "WHA"}},
    {"prompt": "Can you get the top 5 shareholders and current market cap of PSH in 2025?", "expected_tools": ["get_full_report"], "expected_args": {"symbol": "PSH"}},

    # TYPE 2: Compare parameter(s), given list of peers OR implied peers, single year
    {"prompt": "Compare the ROE and ROA of SCB, BBL, and KTB for the year 2024.", "expected_tools": ["profitability_comparables"], "expected_args": {"peers": ["SCB", "BBL", "KTB"], "year": 2024}},
    {"prompt": "Compare the profitability of PTTGC against its subsector peers in 2023.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members", "profitability_comparables"], "expected_args": {"symbol": "PTTGC", "year": 2023}},
    {"prompt": "Show me the trading stats comparison for AAV, BA, and THAI for 2025.", "expected_tools": ["trading_comparables"], "expected_args": {"peers": ["AAV", "BA", "THAI"], "year": 2025}},
    {"prompt": "Compare the balance sheet of HMPRO with its competitors in 2024.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members", "balance_sheet_comparables"], "expected_args": {"symbol": "HMPRO", "year": 2024}},
    {"prompt": "Compare the dividend yield of DUSIT, ERW, and MINT for the year 2023.", "expected_tools": ["dividend_comparables"], "expected_args": {"peers": ["DUSIT", "ERW", "MINT"], "year": 2023}},
    {"prompt": "How does the D/E ratio of AMATA compare to its sector peers in 2025?", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members", "balance_sheet_comparables"], "expected_args": {"symbol": "AMATA", "year": 2025}},
    {"prompt": "Compare the EBITDA and Revenue of BH, BCH, and CHG for 2024.", "expected_tools": ["profitability_comparables"], "expected_args": {"peers": ["BH", "BCH", "CHG"], "year": 2024}},
    {"prompt": "Compare the current stock price and P/E of SPALI with its competitors in 2023.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members", "trading_comparables"], "expected_args": {"symbol": "SPALI", "year": 2023}},
    {"prompt": "Compare the net profit margin (NPM) of BTS and BEM in 2024.", "expected_tools": ["profitability_comparables"], "expected_args": {"peers": ["BTS", "BEM"], "year": 2024}},
    {"prompt": "Check the dividend comparables for IVL and its peers in 2025.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members", "dividend_comparables"], "expected_args": {"symbol": "IVL", "year": 2025}},

    # TYPE 3: Compare parameter(s) for a range of years, ONE ticker
    {"prompt": "Show me the Revenue and Net profit for PTT from 2023 to 2025.", "expected_tools": ["profitability_comparables"], "expected_args": {"peers": ["PTT"], "year": [2023, 2024, 2025]}},
    {"prompt": "How has the D/E ratio of CRC changed between 2023 and 2024?", "expected_tools": ["balance_sheet_comparables"], "expected_args": {"peers": ["CRC"], "year": [2023, 2024]}},
    {"prompt": "Compare the dividend yield of TTB for the years 2024 and 2025.", "expected_tools": ["dividend_comparables"], "expected_args": {"peers": ["TTB"], "year": [2024, 2025]}},
    {"prompt": "Track the P/E and P/Bv of GLOBAL over 2023, 2024, and 2025.", "expected_tools": ["trading_comparables"], "expected_args": {"peers": ["GLOBAL"], "year": [2023, 2024, 2025]}},
    {"prompt": "What is the Gross profit margin (GPM) trend for AWC from 2023 to 2024?", "expected_tools": ["profitability_comparables"], "expected_args": {"peers": ["AWC"], "year": [2023, 2024]}},
    {"prompt": "Show me the Cash outstanding of ROJNA in 2023 and 2024.", "expected_tools": ["balance_sheet_comparables"], "expected_args": {"peers": ["ROJNA"], "year": [2023, 2024]}},
    {"prompt": "How did the ROE and ROA of FPT change from 2023 to 2025?", "expected_tools": ["profitability_comparables"], "expected_args": {"peers": ["FPT"], "year": [2023, 2024, 2025]}},
    {"prompt": "Compare the EBITDA of TOP between 2024 and 2025.", "expected_tools": ["profitability_comparables"], "expected_args": {"peers": ["TOP"], "year": [2024, 2025]}},
    {"prompt": "Look at the current market cap and stock price of BAY for 2023 and 2024.", "expected_tools": ["trading_comparables"], "expected_args": {"peers": ["BAY"], "year": [2023, 2024]}},
    {"prompt": "What was the Net profit of LPN in 2023 versus 2024?", "expected_tools": ["profitability_comparables"], "expected_args": {"peers": ["LPN"], "year": [2023, 2024]}},

    # TYPE 4: Compare parameter(s) for a range of years, MULTIPLE peers (given or implied)
    {"prompt": "Compare the profitability of SCC and IVL between 2023 and 2024.", "expected_tools": ["profitability_comparables"], "expected_args": {"peers": ["SCC", "IVL"], "year": [2023, 2024]}},
    {"prompt": "How did the balance sheets of SCB, BBL, and KTB compare from 2024 to 2025?", "expected_tools": ["balance_sheet_comparables"], "expected_args": {"peers": ["SCB", "BBL", "KTB"], "year": [2024, 2025]}},
    {"prompt": "Compare the dividend yield of CENTEL against its peers for 2023 and 2024.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members", "dividend_comparables"], "expected_args": {"symbol": "CENTEL", "year": [2023, 2024]}},
    {"prompt": "Show me the trading stats of QH and SPALI in 2024 and 2025.", "expected_tools": ["trading_comparables"], "expected_args": {"peers": ["QH", "SPALI"], "year": [2024, 2025]}},
    {"prompt": "Compare the Net profit margin (NPM) of PTTGC with its competitors across 2023 to 2025.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members", "profitability_comparables"], "expected_args": {"symbol": "PTTGC", "year": [2023, 2024, 2025]}},
    {"prompt": "Compare the D/E ratio of CPN, CRC, and HMPRO for 2023 and 2024.", "expected_tools": ["balance_sheet_comparables"], "expected_args": {"peers": ["CPN", "CRC", "HMPRO"], "year": [2023, 2024]}},
    {"prompt": "Compare the Gross profit margin (GPM) of BEM and BTS between 2024 and 2025.", "expected_tools": ["profitability_comparables"], "expected_args": {"peers": ["BEM", "BTS"], "year": [2024, 2025]}},
    {"prompt": "How do the trading stats of WHA compare to its subsector peers for 2023 and 2024?", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members", "trading_comparables"], "expected_args": {"symbol": "WHA", "year": [2023, 2024]}},
    {"prompt": "Compare the dividend policy and yield of BDMS, BH, and BCH in 2023 and 2024.", "expected_tools": ["dividend_comparables"], "expected_args": {"peers": ["BDMS", "BH", "BCH"], "year": [2023, 2024]}},
    {"prompt": "Compare the EBITDA of ORI against its peers over 2024 and 2025.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members", "profitability_comparables"], "expected_args": {"symbol": "ORI", "year": [2024, 2025]}},

    # TYPE 5: Find list of peers/competitors for a specified ticker
    {"prompt": "Find a list of peers and competitors for SCC.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members"], "expected_args": {"symbol": "SCC"}},
    {"prompt": "Who are the competitors operating in the same subsector as IRPC?", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members"], "expected_args": {"symbol": "IRPC"}},
    {"prompt": "List the market peers for BAY.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members"], "expected_args": {"symbol": "BAY"}},
    {"prompt": "I want to know the competitor stock tickers for AAV.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members"], "expected_args": {"symbol": "AAV"}},
    {"prompt": "Identify all peers in the same industry subsector as CPN.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members"], "expected_args": {"symbol": "CPN"}},
    {"prompt": "Find the index members that belong to the same sector as CHG.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members"], "expected_args": {"symbol": "CHG"}},
    {"prompt": "Can you list the companies that compete with CENTEL on the SET?", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members"], "expected_args": {"symbol": "CENTEL"}},
    {"prompt": "Get the list of subsector peers for AMATA.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members"], "expected_args": {"symbol": "AMATA"}},
    {"prompt": "Who are the main competitors of S in the stock market?", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members"], "expected_args": {"symbol": "S"}},
    {"prompt": "Show me the peer tickers for THAI.", "expected_tools": ["get_full_report", "get_sector_index_links", "get_index_members"], "expected_args": {"symbol": "THAI"}}
]



def evaluate_trajectory_and_args(agent_messages, test_case):
    """Evaluates both the trajectory (tools called) and the arguments passed to those tools against the expected values in the test case. Returns True if both trajectory and arguments match expectations, otherwise False."""
    tools_called = []
    collected_args = {}
    
    # Extract tools called and their arguments from the agent's messages
    for m in agent_messages:
        if '<action>' in str(m.get('content', '')):
            action_match = re.search(r"<action>(.*?)</action>", m['content'], re.DOTALL)

            if action_match:
                raw_str = action_match.group(1).strip()
                raw_str = re.sub(r"```$", "", raw_str).strip()
                try:
                    action_data = json.loads(raw_str)
                    tools_called.append(action_data.get('name', 'Unknown'))
                    
                    args = action_data.get('arguments', {})
                    for k, v in args.items():
                        if k in collected_args:
                            # Convert existing to list if it's not already a list
                            if not isinstance(collected_args[k], list):
                                collected_args[k] = [collected_args[k]]
                            
                            # Append the new value(s) safely
                            if isinstance(v, list):
                                collected_args[k].extend(v)
                            else:
                                collected_args[k].append(v)
                        else:
                            collected_args[k] = v
                except json.JSONDecodeError:
                    print(f"[Eval Warning] Failed to parse Agent tool output: {raw_str}")

    # Check Trajectory (Tools)
    expected_tools = test_case["expected_tools"]
    traj_success = all(tool in tools_called for tool in expected_tools)

    # Check Arguments strictly
    expected_args = test_case.get("expected_args", {})
    args_success = True
    failed_args_reason = ""
    
    for key, expected_val in expected_args.items():
        actual_val = collected_args.get(key)
        
        # Scenario A: The expected value is a list (e.g., years [2023, 2024] or peers ["PTT", "IRPC"])
        if isinstance(expected_val, list):
            if not isinstance(actual_val, list):
                # If there's only 1 item, it might not be a list in `actual_val` yet
                actual_val = [actual_val] if actual_val is not None else []
                
            if not set(expected_val).issubset(set(actual_val)):
                args_success = False
                failed_args_reason += f"Arg '{key}' mismatch. Expected {expected_val}, Got {actual_val}. "
        
        # Scenario B: The expected value is a single string or int (e.g., symbol "SCC")
        else:
            # If the LLM called it multiple times, actual_val is now a list. Just check if it's in the list.
            if isinstance(actual_val, list):
                if expected_val not in actual_val:
                    args_success = False
                    failed_args_reason += f"Arg '{key}' mismatch. Expected {expected_val}, Got {actual_val}. "
            else:
                if expected_val != actual_val:
                    args_success = False
                    failed_args_reason += f"Arg '{key}' mismatch. Expected {expected_val}, Got {actual_val}. "

    # Final Output Formatting
    if traj_success and args_success:
        print(f"PASS | Tools: {tools_called} | Args: {collected_args}")
        return True
    else:
        print(f"FAIL")
        if not traj_success:
            print(f"   -> Trajectory Mismatch: Expected {expected_tools}, Got {tools_called}")
        if not args_success:
            print(f"   -> Argument Mismatch: {failed_args_reason}")
        return False



def save_manual_evaluation_report(results, agent_model, filename=None):
    """Generates a clean, highly readable Markdown file for manual human review."""

    # Create a folder to store the reports if it doesn't exist
    report_dir = "agent_result_report"
    os.makedirs(report_dir, exist_ok=True)

    # Auto-generate a smart filename (Model Name + Timestamp) so you don't overwrite old tests
    if filename is None:
        safe_model_name = agent_model.replace(':', '_').replace('-', '_')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eval_{safe_model_name}_{timestamp}.md"
    filepath = os.path.join(report_dir, filename)

    # Write the file into the folder
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# Manual Agent Evaluation Report\n")
        f.write(f"**Agent Model:** `{agent_model}`\n")
        f.write(f"**Total Tests:** {len(results)}\n\n")
        f.write("---\n\n")
        
        # Write each test result in a structured format
        for res in results:
            f.write(f"## Test {res['test_num']}\n")
            f.write(f"**Prompt:** *\"{res['prompt']}\"*\n\n")
            f.write(f"**Expected Tools:** `{', '.join(res['expected_tools'])}`  \n")
            f.write(f"**Trajectory Success:** {'Pass' if res['traj_success'] else 'Fail'}  \n")
            f.write(f"**Time Taken:** {res['latency']:.2f}s\n\n")
            
            f.write("### Agent's Final Answer:\n")
            
            answer_lines = res['final_answer'].split('\n')
            for line in answer_lines:
                f.write(f"> {line}\n")
            
            f.write("\n---\n\n")
            
    print(f"\nManual evaluation report successfully saved to: {os.path.abspath(filepath)}")



def run_trajectory_evaluation(agent_model="qwen2.5-coder:14b"):
    """Runs the trajectory and arguments evaluation for the specified agent model on the predefined dataset. Generates a Markdown report for manual review and prints a summary in the terminal."""
    
    # Terminal Header
    print("\n" + "="*60)
    print(f"STARTING TRAJECTORY & ARGUMENTS EVALUATION")
    print(f"Agent Model: {agent_model}")
    print("="*60)
    
    passed_trajectory = 0
    manual_eval_data = []  # List to store data for the markdown report
    
    print("Booting up Chrome Scraper...")
    scraper = SETStockData(version=146)
    live_tools = SETAgentTools(scraper)
    
    try:
        # Loop through the 50-question dataset
        for i, test in enumerate(evaluation_dataset):
            test_num = i + 1
            print(f"\n" + "-"*50)
            print(f"Test {test_num}: {test['prompt']}")
            print("-" * 50)
            
            # Initialize fresh agent memory for each test
            agent = LocalFinancialAgent(model_name=agent_model, tool_manager=live_tools)
            
            start_time = time.time()
            # Run the agent (allow up to 10 steps)
            agent.run(test["prompt"], max_steps=10) 
            latency = time.time() - start_time
            print(f"Time taken: {latency:.2f}s")
            
            # Extract assistant messages for evaluation
            assistant_messages = [m for m in agent.messages if m.get("role") == "assistant"]
            traj_success = evaluate_trajectory_and_args(assistant_messages, test)
            
            if traj_success:
                passed_trajectory += 1
                
            # Extract the final answer (last assistant message that is not an action)
            final_answers = [
                m['content'] 
                for m in assistant_messages 
                if '<action>' not in str(m.get('content', ''))
            ]
            final_answer = final_answers[-1].strip() if final_answers else "*[No final answer generated. The agent likely ran out of steps or got stuck in a loop.]*"
            
            # Store it
            manual_eval_data.append({
                "test_num": test_num,
                "prompt": test["prompt"],
                "expected_tools": test["expected_tools"],
                "traj_success": traj_success,
                "latency": latency,
                "final_answer": final_answer
            })
            
            # Sleep slightly to prevent hammering the SET servers
            time.sleep(2)

    finally:
        print("\nClosing Chrome Scraper...")
        scraper.close()

    # Generate the Markdown Report
    save_manual_evaluation_report(manual_eval_data, agent_model)

    # Final Terminal Report
    print("\n" + "="*50)
    print("FINAL TRAJECTORY EVALUATION REPORT")
    print("="*50)
    print(f"Trajectory & Args Score: {passed_trajectory}/{len(evaluation_dataset)} ({(passed_trajectory/len(evaluation_dataset))*100:.1f}%)")
