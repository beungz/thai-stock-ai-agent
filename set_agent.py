import pandas as pd
import undetected_chromedriver as uc
import io
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import json
import ollama
import streamlit as st



def extract_set_metadata(html_content):
    """This function takes the raw HTML content of a SET stock factsheet page and extracts key metadata about the company."""
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {}

    # Full Company Name
    name_h1 = soup.find('h1', class_='company-name')
    data['company_fullname'] = name_h1.get_text(strip=True) if name_h1 else None

    # Business Type Description
    biz_div = soup.find('div', class_='business-desc')
    data['business_description'] = biz_div.get_text(strip=True) if biz_div else None

    # Label-Value Pairs for Company Profile & Shareholder sections
    items = soup.find_all('div', class_='item-list-details')
    for item in items:
        label = item.find('label')
        value_tag = item.find(['span', 'div', 'a'])
        if label and value_tag:
            key = label.get_text(strip=True).replace(':', '').lower().replace(' ', '_')
            val = value_tag.get_text(" ", strip=True)
            if key in data:
                data[f"prev_{key}"] = val
            else:
                data[key] = val

    # Auditor Information
    auditor_div = soup.find('div', class_='auditor')
    if auditor_div:
        auditor_names_div = auditor_div.find('div', class_='cell-2')
        if auditor_names_div:
            data['auditor_names'] = [s.get_text(strip=True) for s in auditor_names_div.find_all('span')]
        
        report_cells = auditor_div.find_all('div', class_='cell-x')
        for cell in report_cells:
            lbl = cell.find('label')
            val = cell.find('span')
            if lbl and val:
                key = lbl.get_text(strip=True).lower().replace(' ', '_').replace('/', '')
                data[key] = val.get_text(strip=True)

    # Sector / Subsector Index Memberships
    company_info_div = soup.find('div', class_=lambda c: c and 'company-info' in c)
    if company_info_div:
        spans = company_info_div.find_all('span', class_='mb-1')
        if len(spans) > 0:
            # Clean up the excessive spacing/newlines in the sector text
            raw_sector = spans[0].get_text(strip=True)
            data['sector_subsector'] = re.sub(r'\s+', ' ', raw_sector)
        if len(spans) > 1:
            data['index_memberships'] = spans[1].get_text(strip=True)

    # SET ESG Ratings
    esg_label = soup.find(lambda tag: tag.name == "span" and "SET ESG Ratings" in tag.text)
    if esg_label:
        rating_text = esg_label.next_sibling
        if rating_text and isinstance(rating_text, str) and rating_text.strip():
            data['set_esg_ratings'] = rating_text.strip()
        else:
            parent_text = esg_label.parent.get_text(separator=" ", strip=True)
            data['set_esg_ratings'] = parent_text.replace(esg_label.get_text(strip=True), '').strip()

    # CAC Anti-Corruption Certification
    cac_label = soup.find(lambda tag: tag.name == "span" and "CAC Anti-Corruption" in tag.text)
    if cac_label:
        next_div = cac_label.find_next_sibling('div')
        if next_div:
            data['cac_certification'] = next_div.get_text(strip=True)
        else:
            parent_text = cac_label.parent.get_text(separator=" ", strip=True)
            data['cac_certification'] = parent_text.replace(cac_label.get_text(strip=True), '').strip()

    # Dividend Policy
    div_policy_label = soup.find('label', string=re.compile('Dividend Policy', re.IGNORECASE))
    if div_policy_label:
        policy_span = div_policy_label.find_next_sibling('span')
        if policy_span:
            data['dividend_policy'] = policy_span.get_text(" ", strip=True)
        else:
            parent_text = div_policy_label.parent.get_text(" ", strip=True)
            data['dividend_policy'] = parent_text.replace('Dividend Policy', '').strip()

    return data



class SETStockData:
    """This class uses undetected_chromedriver to scrape stock data"""
    def __init__(self, version=146):
        """Initializes the Chrome driver with optimizations for faster scraping."""
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        
        # Do not load images
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        
        self.driver = uc.Chrome(options=options, version_main=version)

    def _get_page_source(self, url, page_name="Page", needs_scroll=True):
        """Navigates to URL and optionally scrolls."""
        self.driver.get(url)
        
        try:
            # Wait for the specific table rows to load, which indicates the page is ready for data extraction
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
            )
            
            # Some pages require scrolling to load all data (e.g., shareholder lists), while others like the factsheet load most data immediately. The 'needs_scroll' flag allows us to optimize waiting time.
            if needs_scroll:
                last_height = self.driver.execute_script("return document.body.scrollHeight")
                for _ in range(6):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.5)
                    
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    
                    if new_height == last_height:
                        break 
                    last_height = new_height
                    
            return self.driver.page_source
        except Exception as e:
            print(f"Warning: Timeout waiting for tables at {url}.")
            return self.driver.page_source

    def _clean_df(self, df):
        """Cleans the raw DataFrame by flattening multi-level columns and removing unnecessary index columns."""
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [' '.join(map(str, col)).strip() for col in df.columns]
        df.columns = [c.replace('Unnamed: 0_level_0 ', '').replace('Unnamed: 0 ', '') for c in df.columns]
        return df

    def get_full_report(self, symbol):
        """Fetches and parses all relevant data for a given stock symbol, returning a structured dictionary."""
        overall_start = time.time()
        symbol = symbol.upper()
        
        # SHAREHOLDER PAGE
        sh_source = self._get_page_source(
            f"https://www.set.or.th/en/market/product/stock/quote/{symbol}/major-shareholders", 
            "Shareholder Page", 
            needs_scroll=True 
        )
        try:
            sh_tables = pd.read_html(io.StringIO(sh_source))
        except ValueError:
            sh_tables = []

        # FACTSHEET PAGE
        fs_source = self._get_page_source(
            f"https://www.set.or.th/en/market/product/stock/quote/{symbol}/factsheet", 
            "Factsheet Page", 
            needs_scroll=True
        )
        try:
            fs_tables = pd.read_html(io.StringIO(fs_source))
        except ValueError:
            fs_tables = []
        
        # Construct a comprehensive report dictionary that includes metadata and all the relevant tables. The metadata is extracted using the dedicated function, while the tables are identified and cleaned based on their content.
        report = {
            "metadata": self._extract_metadata(fs_source),
            "shareholders": self._clean_df(sh_tables[0]) if len(sh_tables) > 0 else pd.DataFrame(),
            "nvdr": self._clean_df(sh_tables[1]) if len(sh_tables) > 1 else None,
            "board_of_directors": pd.DataFrame(),
            "adjusted_price_performance": pd.DataFrame(),
            "trading_statistics": pd.DataFrame(),
            "rate_of_return": pd.DataFrame(),
            "dividend": pd.DataFrame(),
            "financial_statements_submission": pd.DataFrame(),
            "balance_sheet": pd.DataFrame(),
            "income_statement": pd.DataFrame(),
            "cash_flow_statement": pd.DataFrame(),
            "financial_ratios": pd.DataFrame(),
            "growth_rate": pd.DataFrame(),
            "cash_cycle": pd.DataFrame()
        }

        # Identify each table based on unique keywords in their content, then clean and assign them to the appropriate section in the report. This allows us to handle variations in table order and presence across different stock pages.
        for df in fs_tables:
            df = self._clean_df(df)
            content = df.to_string()
            if "Position" in content: report["board_of_directors"] = df
            elif "Compare to Stock" in content: report["adjusted_price_performance"] = df
            elif "Market Cap" in content and "P/E" in content: report["trading_statistics"] = df
            elif "Price Change (%)" in content and "Dividend Yield (%)" in content: report["rate_of_return"] = df
            elif "Dividend/Share" in content: report["dividend"] = df
            elif "Date of Submission" in content and "Auditor’s Opinion" in content: report["financial_statements_submission"] = df
            elif "Total Assets" in content: report["balance_sheet"] = df
            elif "Total Revenues" in content: report["income_statement"] = df
            elif "Net Cash Flow" in content: report["cash_flow_statement"] = df
            elif "Net Profit Margin (%)" in content: report["financial_ratios"] = df
            elif "Sales Growth" in content: report["growth_rate"] = df
            elif "Cash Cycle (Days)" in content: report["cash_cycle"] = df

        print(f"Extracted {symbol} in {time.time() - overall_start:.2f}s")
        return report

    def _extract_metadata(self, source):
        """Extracts key metadata from the factsheet page HTML content. This includes company name, business description, sector/subsector info, ESG ratings, dividend policy, and more. The function uses BeautifulSoup to parse the HTML and locate specific elements based on their tags and classes."""
        meta = extract_set_metadata(source)
        try:
            date_el = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Factsheet as of')]")
            meta['factsheet_as_of'] = date_el.text.replace('Factsheet as of ', '').strip()
        except:
            pass
        return meta
    
    def close(self):
        """Closes the Chrome driver to free up resources."""
        self.driver.quit()

    def get_sector_index_links(self):
        """Navigates to the SET stock search page and extracts all sector and subsector index links."""
        url = "https://www.set.or.th/en/market/product/stock/search"
        print(f"Loading {url} to extract master index mappings...")
        self.driver.get(url)

        try:
            # Wait for the specific table rows to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.search-SETMAI table tbody tr"))
            )
            # Give the Javascript an extra second to finish hydrating all the rows
            time.sleep(1)
            
            # Parse the page source with BeautifulSoup to extract the sector/subsector index links.
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            target_div = soup.find('div', class_='search-SETMAI')
            
            if not target_div:
                print("Error: Could not find <div class='search-SETMAI'> on the page.")
                return pd.DataFrame()

            # Parse the table
            tbody = target_div.find('tbody')
            data = []
            
            # Each row corresponds to either a Sector or a Subsector. We can classify them based on the depth of their URL (Sectors have shorter URLs, Subsectors have longer URLs).
            for tr in tbody.find_all('tr', role='row'):
                a_tag = tr.find('a', href=True)
                if not a_tag:
                    continue
                    
                href = a_tag['href']
                full_url = f"https://www.set.or.th{href}" if href.startswith('/') else href
                
                raw_name = a_tag.get_text(separator=" ", strip=True)
                clean_name = re.sub(r'\s+', ' ', raw_name)
                
                if ' - ' in clean_name:
                    symbol, description = clean_name.split(' - ', 1)
                else:
                    symbol = clean_name
                    description = clean_name
                    
                # Classify based on URL depth
                url_parts = [p for p in href.split('/') if p] 
                if len(url_parts) > 5:
                    index_type = "Subsector"
                    parent_sector = url_parts[4].upper()
                else:
                    index_type = "Sector"
                    parent_sector = None
                
                # Append the extracted information to the data list
                data.append({
                    "Type": index_type,
                    "Symbol": symbol.strip().upper(),
                    "Description": description.strip(),
                    "Parent_Sector": parent_sector,
                    "URL": full_url
                })
                
            df = pd.DataFrame(data)
            return df

        except Exception as e:
            print(f"Error fetching index links: {e}")
            return pd.DataFrame()
        
    def get_index_members(self, index_url):
        """Given a sector or subsector index URL, this function loads the page and extracts the list of member stock tickers."""
        print(f"Loading {index_url} to extract peer tickers...")
        
        source = self._get_page_source(index_url, page_name="Index Page", needs_scroll=True)
        soup = BeautifulSoup(source, 'html.parser')
        
        peers = []
        
        for a_tag in soup.find_all('a', attrs={'data-symbol': True}):
            symbol = a_tag['data-symbol'].strip().upper()
            
            if symbol and symbol not in peers:
                peers.append(symbol)
                
        df = pd.DataFrame(peers, columns=['Symbol'])
        
        if not df.empty:
            df = df.sort_values('Symbol').reset_index(drop=True)
            
        return df



class SETPeerComparator:
    """This class takes a list of peer tickers and a year, then builds comparison tables for trading stats, profitability, balance sheet, and dividends."""
    def __init__(self, scraper_instance):
        """The comparator is initialized with a reference to the scraper instance, allowing it to fetch and cache reports for multiple tickers efficiently."""
        self.scraper = scraper_instance
        self.reports = {}

    def fetch_peer_data(self, peers):
        """Fetches and caches the full reports for a list of peer tickers."""
        for ticker in peers:
            if ticker not in self.reports:
                self.reports[ticker] = self.scraper.get_full_report(ticker)

    def _extract_val(self, ticker, table_key, row_keyword, requested_year):
        """This helper function looks up a specific value from a given table in the stock report based on the row keyword and the requested year. It includes a fallback mechanism to find the closest available year if the exact one is not present."""
        report = self.reports.get(ticker, {})
        df = report.get(table_key)
        
        if df is None or df.empty:
            return "N/A"
            
        # Find the target row
        mask = df.iloc[:, 0].astype(str).str.contains(row_keyword, case=False, regex=False, na=False)
        if not mask.any():
            return "N/A"
        row_idx = mask.idxmax()
        
        # Look for the exact requested year in the column headers
        target_col = None
        for col in df.columns:
            if str(requested_year) in str(col):
                target_col = col
                break
                
        # Fallback: Find the closest available year
        if not target_col:
            available_years = {}
            for col in df.columns:
                if 'YTD' in str(col).upper():
                    continue
                # Extract any 4-digit year from the column name
                match = re.search(r'\b(20\d{2})\b', str(col))
                if match:
                    year_found = int(match.group(1))
                    available_years[year_found] = col
            
            if available_years:
                # Calculate the minimum difference to find the closest year
                closest_year = min(available_years.keys(), key=lambda y: abs(y - int(requested_year)))
                target_col = available_years[closest_year]
                val = df.loc[row_idx, target_col]
                # Return the value but append (YYYY)
                return f"{str(val).strip()} ({closest_year})"
            
            return "N/A"
                
        # Exact year found
        val = df.loc[row_idx, target_col]
        return str(val).strip()

    def trading_comparables(self, peers, year):
        """Builds a comparison table for trading statistics like Price, Market Cap, P/E, P/BV, and Beta for a list of peer tickers."""
        data = []
        for ticker in peers:
            data.append({
                "Ticker": ticker,
                "Price (Baht/share)": self._extract_val(ticker, "trading_statistics", "Price", year),
                "Market Cap (M.Baht)": self._extract_val(ticker, "trading_statistics", "Market Cap", year),
                "P/E (X)": self._extract_val(ticker, "trading_statistics", "P/E", year),
                "P/BV (X)": self._extract_val(ticker, "trading_statistics", "P/BV", year),
                "Beta": self._extract_val(ticker, "trading_statistics", "Beta", year) 
            })
        return pd.DataFrame(data).set_index("Ticker")

    def profitability_comparables(self, peers, year):
        """Builds a comparison table for profitability metrics like Total Revenues, EBITDA, Net Profit, Gross Profit Margin, Net Profit Margin, ROE, and ROA for a list of peer tickers."""
        data = []
        for ticker in peers:
            data.append({
                "Ticker": ticker,
                "Total Revenues": self._extract_val(ticker, "income_statement", "Total Revenues", year),
                "EBITDA": self._extract_val(ticker, "income_statement", "EBITDA", year),
                "Net Profit (Parent)": self._extract_val(ticker, "income_statement", "Owners Of The Parent", year),
                "Gross Profit Margin (%)": self._extract_val(ticker, "financial_ratios", "Gross Profit Margin", year),
                "Net Profit Margin (%)": self._extract_val(ticker, "financial_ratios", "Net Profit Margin", year),
                "ROE (%)": self._extract_val(ticker, "financial_ratios", "ROE", year),
                "ROA (%)": self._extract_val(ticker, "financial_ratios", "ROA", year)
            })
        return pd.DataFrame(data).set_index("Ticker")

    def balance_sheet_comparables(self, peers, year):
        """Builds a comparison table for balance sheet metrics like Cash & Equivalents, Inventories, PP&E Net, Total Assets, Total Liabilities, Paid-Up Capital, Retained Earnings, Shareholders' Equity, and D/E Ratio for a list of peer tickers."""
        data = []
        for ticker in peers:
            data.append({
                "Ticker": ticker,
                "Cash & Equivalents": self._extract_val(ticker, "balance_sheet", "Cash And Cash Equivalents", year),
                "Inventories": self._extract_val(ticker, "balance_sheet", "Inventories", year),
                "PP&E Net": self._extract_val(ticker, "balance_sheet", "PP&E Net", year),
                "Total Assets": self._extract_val(ticker, "balance_sheet", "Total Assets", year),
                "Total Liabilities": self._extract_val(ticker, "balance_sheet", "Total Liabilities", year),
                "Paid-Up Capital": self._extract_val(ticker, "balance_sheet", "Paid-Up Capital", year),
                "Retained Earnings": self._extract_val(ticker, "balance_sheet", "Retained Earnings", year),
                "Shareholders' Equity": self._extract_val(ticker, "balance_sheet", "Shareholders' Equity", year),
                "D/E (X)": self._extract_val(ticker, "financial_ratios", "D/E", year)
            })
        return pd.DataFrame(data).set_index("Ticker")

    def dividend_comparables(self, peers, year):
        """Builds a comparison table for dividend-related metrics like Dividend Yield, Payout Ratio, Dividend Policy, Net Profit, Cash & Equivalents, and Retained Earnings for a list of peer tickers."""
        data = []
        for ticker in peers:
            # Extract dividend policy
            report = self.reports.get(ticker, {})
            div_policy = report.get("metadata", {}).get("dividend_policy", "N/A")
            
            data.append({
                "Ticker": ticker,
                "Dividend Yield (%)": self._extract_val(ticker, "rate_of_return", "Dividend Yield", year),
                "Payout Ratio": self._extract_val(ticker, "rate_of_return", "Payout Ratio", year),
                "Dividend Policy": div_policy,
                "Net Profit (Parent)": self._extract_val(ticker, "income_statement", "Owners Of The Parent", year),
                "Cash & Equivalents": self._extract_val(ticker, "balance_sheet", "Cash And Cash Equivalents", year),
                "Retained Earnings": self._extract_val(ticker, "balance_sheet", "Retained Earnings", year)
            })
        return pd.DataFrame(data).set_index("Ticker")
    


class SETAgentTools:
    """This class serves as a centralized interface for all the tools that the LLM agent can call. It includes methods to get full stock reports, fetch sector index links, retrieve index members, and generate various comparable tables for trading stats, profitability, balance sheet, and dividends."""
    def __init__(self, scraper_instance):
        """The tools are initialized with a reference to the scraper instance, allowing them to fetch and cache data efficiently. A centralized cache is used to store stock reports, which can be accessed by both the tools and the comparator to avoid redundant scraping."""
        self.scraper = scraper_instance
        self.comparator = SETPeerComparator(self.scraper)
        
        # Centralized Cache
        self.report_cache = {} 
        self.comparator.reports = self.report_cache # Share cache with comparator!
        self.master_index_map = None

    def get_full_report(self, symbol):
        """Fetches the full report for a given stock symbol. This method checks the cache first to avoid redundant scraping. If the symbol is not in the cache, it scrapes the data and stores it in the cache before returning the metadata as a JSON string."""
        symbol = symbol.upper()
        if symbol not in self.report_cache:
            self.report_cache[symbol] = self.scraper.get_full_report(symbol)
        
        # Return ONLY the metadata to the LLM to save Context Window space
        meta = self.report_cache[symbol].get('metadata', {})
        return json.dumps(meta, ensure_ascii=False)

    def get_sector_index_links(self):
        """Fetches the master index mapping of all sectors and subsectors to their corresponding URLs. This method checks if the mapping is already stored in memory to avoid redundant scraping. If not, it scrapes the data, stores it in memory, and returns it as a JSON string for the LLM to read."""
        if self.master_index_map is None:
            self.master_index_map = self.scraper.get_sector_index_links()
        
        # Return as a JSON string so the LLM can read the URLs
        return self.master_index_map.to_json(orient='records')

    def get_index_members(self, index_url):
        """Given a sector or subsector index URL, this method fetches the list of member stock tickers. It uses the scraper to load the page and extract the tickers, then returns just the list of tickers as a JSON string for the LLM to read."""
        df = self.scraper.get_index_members(index_url)
        # Return just the list of tickers to the LLM
        return json.dumps(df['Symbol'].tolist())

    def trading_comparables(self, peers, year):
        """Generates a comparison table for trading statistics for a list of peer tickers and a specified year."""
        self.comparator.fetch_peer_data(peers) # This auto-uses the cache!
        df = self.comparator.trading_comparables(peers, year)
        return df.to_markdown()

    def profitability_comparables(self, peers, year):
        """Generates a comparison table for profitability metrics for a list of peer tickers and a specified year."""
        self.comparator.fetch_peer_data(peers)
        df = self.comparator.profitability_comparables(peers, year)
        return df.to_markdown()

    def balance_sheet_comparables(self, peers, year):
        """Generates a comparison table for balance sheet metrics for a list of peer tickers and a specified year."""
        self.comparator.fetch_peer_data(peers)
        df = self.comparator.balance_sheet_comparables(peers, year)
        return df.to_markdown()

    def dividend_comparables(self, peers, year):
        """Generates a comparison table for dividend metrics for a list of peer tickers and a specified year."""
        self.comparator.fetch_peer_data(peers)
        df = self.comparator.dividend_comparables(peers, year)
        return df.to_markdown()
    


class LocalFinancialAgent:
    """This class implements the core logic of the LLM agent that interacts with the user, processes LLM responses, and executes tool calls. It initializes with a system prompt that includes the tool definitions from an external JSON registry, and it maintains a conversation history to manage the interaction flow with the LLM."""
    def __init__(self, model_name, tool_manager, registry_path="function_registry.json"):
        """Initializes the agent with the specified LLM model, tool manager, and path to the function registry JSON file. The function registry is loaded and embedded into the system prompt to inform the LLM about the available tools and how to use them."""
        self.model_name = model_name
        self.tools = tool_manager
        self.messages = []
        
        # Load the external JSON registry
        with open(registry_path, 'r', encoding='utf-8') as f:
            self.registry_schema = json.load(f)
            
        # Map the string names from JSON to actual Python functions in the Tool Manager
        self.function_map = {
            "get_full_report": self.tools.get_full_report,
            "get_sector_index_links": self.tools.get_sector_index_links,
            "get_index_members": self.tools.get_index_members,
            "trading_comparables": self.tools.trading_comparables,
            "profitability_comparables": self.tools.profitability_comparables,
            "balance_sheet_comparables": self.tools.balance_sheet_comparables,
            "dividend_comparables": self.tools.dividend_comparables
        }
        
        self._init_system_prompt()

    def _init_system_prompt(self):
        schema_string = json.dumps(self.registry_schema, indent=2)
        prompt = f"""You are an expert AI Financial Analyst specializing in the Stock Exchange of Thailand (SET). 
You have access to the following tools defined in JSON schema:
<tools>\n{schema_string}\n</tools>

To use a tool, you MUST output a JSON block wrapped in <action> tags, exactly like this:
<action>
{{"name": "tool_name", "arguments": {{"arg1": "value1"}}}}
</action>

CRITICAL RULES:
1. Call ONLY ONE tool at a time and wait for the Observation.
2. NEVER ask the user for permission to proceed. If the user asks to compare a stock to its peers, you MUST autonomously find the peers AND generate the comparison tables without stopping.
3. NEVER hallucinate arguments. Only use the exact parameters defined in the schema.
4. If the user asks for multiple years, you must call the comparables tool multiple times, once for each individual year.
"""
        self.messages.append({"role": "system", "content": prompt})

    def execute_tool(self, action_json):
        """This method takes the JSON string extracted from the <action> tags in the LLM's response, parses it to identify which tool to call and with what arguments, then executes the corresponding Python function from the Tool Manager."""
        try:
            # Parse the JSON to get the tool name and arguments
            action_data = json.loads(action_json)
            func_name = action_data.get("name")
            kwargs = action_data.get("arguments", {})
            
            # Check if the function name from the JSON matches any of the available tools in the function map. If it does, execute the corresponding Python function with the provided arguments and return the result as a string.
            if func_name in self.function_map:
                print(f"[Agent executing -> {func_name}({kwargs})]")
                # Execute the matched python function with the arguments
                func = self.function_map[func_name]
                result = func(**kwargs)
                return str(result)
            else:
                return f"Error: Tool '{func_name}' not found."
                
        except json.JSONDecodeError:
            return "Error: Invalid JSON format for action. Remember to wrap valid JSON in <action> tags."
        except Exception as e:
            return f"Error executing tool: {str(e)}"

    def run(self, user_input, max_steps=8):
        """This method manages the interaction loop with the LLM. It takes the user's input, appends it to the conversation history, and then enters a loop where it sends the conversation history to the LLM, processes the response, checks for any tool calls, executes them if present, and appends the observations back to the conversation history. The loop continues until either a final answer is given (no more tool calls) or a maximum number of steps is reached to prevent infinite loops."""
        self.messages.append({"role": "user", "content": user_input})
        
        # Loop to allow the agent to reason, call tools, and observe results iteratively. The loop will break if the agent provides a final answer without any tool calls or if the maximum number of steps is reached.
        for step in range(max_steps):
            print(f"\nAgent Step {step+1}")
            
            # Call the LLM with the current conversation history and get the response. 
            response = ollama.chat(model=self.model_name, messages=self.messages)
            llm_reply = response['message']['content']
            
            print(f"Agent Output:\n{llm_reply}")
            self.messages.append({"role": "assistant", "content": llm_reply})
            
            # Regex to find <action> blocks
            action_match = re.search(r"<action>(.*?)</action>", llm_reply, re.DOTALL)
            
            if action_match:
                action_json = action_match.group(1).strip()
                observation = self.execute_tool(action_json)
                
                print(f"[Observation length: {len(observation)} chars]")
                self.messages.append({"role": "user", "content": f"Observation: {observation}"})
            else:
                print("\nTask Complete.")
                break
                
        if step == max_steps - 1:
            print("\nMax steps reached. Terminating early to prevent infinite loop.")
    
    def run_streamlit(self, user_input, st_container, max_steps=8):
        """This method is a Streamlit-compatible version of the run() method. It manages the interaction loop with the LLM while also updating the Streamlit UI with status messages, tool execution feedback, and the final answer."""
        self.messages.append({"role": "user", "content": user_input})
        
        # Loop to allow the agent to reason, call tools, and observe results iteratively. The loop will break if the agent provides a final answer without any tool calls or if the maximum number of steps is reached to prevent infinite loops. The Streamlit UI is updated at each step to reflect the agent's thinking process and tool usage.
        for step in range(max_steps):
            # Creates a collapsible "Thinking" box in the UI
            with st.status(f"Agent Thinking (Step {step+1})...", expanded=True) as status:
                st.write("Calling Local LLM...")
                
                # Call the LLM with the current conversation history and get the response.
                response = ollama.chat(model=self.model_name, messages=self.messages)
                llm_reply = response['message']['content']
                
                # Display the LLM's response in the UI for debugging and transparency
                st.markdown(f"**Thought Process:**\n\n{llm_reply}")
                self.messages.append({"role": "assistant", "content": llm_reply})
                
                # Check for tool usage
                action_match = re.search(r"<action>(.*?)</action>", llm_reply, re.DOTALL)
                
                if action_match:
                    action_json = action_match.group(1).strip()
                    tool_name = json.loads(action_json).get('name', 'Unknown')
                    st.write(f"**Executing Tool:** `{tool_name}`")
                    
                    observation = self.execute_tool(action_json)
                    st.write(f"**Observation Received** ({len(observation)} chars)")
                    
                    self.messages.append({"role": "user", "content": f"Observation: {observation}"})
                    status.update(label=f"Step {step+1}: Used '{tool_name}'", state="complete", expanded=False)
                else:
                    status.update(label="Task Complete!", state="complete", expanded=False)
                    st_container.markdown(llm_reply)
                    return llm_reply
                    
        if step == max_steps - 1:
            st_container.error("Max steps reached. Terminated early.")
            return "Error: Agent reached maximum reasoning steps."



