import streamlit as st
import atexit
from set_agent import SETStockData, SETAgentTools, LocalFinancialAgent

# Streamlit App Configuration
st.set_page_config(page_title="SET AI Agent", layout="wide")
st.title("Thailand's Stock AI Agent")

# Initialize Agent and Chat History in Session State
if "agent" not in st.session_state:
    with st.spinner("Booting up Chrome and initializing AI Agent..."):
        # Initialize Scraper
        scraper = SETStockData(version=146)
        
        # Register a cleanup function to close Chrome when the Streamlit server stops
        atexit.register(scraper.close)
        
        # Initialize Tools and Agent
        tool_manager = SETAgentTools(scraper)
        st.session_state.agent = LocalFinancialAgent(
            model_name="qwen2.5:7b", 
            tool_manager=tool_manager,
            registry_path="function_registry.json"
        )
        
        # Initialize chat history
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Hi! I am your local SET AI Agent. I can fetch SET stock reports, find sector peers, and build comparison tables. What would you like to analyze today?", "is_final": True}
        ]

# Display Chat History
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat Input & Execution
if prompt := st.chat_input("Example: Compare the profitability of PTT against its peers for 2023"):
    
    # Show User Message
    st.session_state.chat_history.append({"role": "user", "content": prompt, "is_final": True})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Agent Response
    with st.chat_message("assistant"):
        final_answer_container = st.empty()
        
        final_response = st.session_state.agent.run_streamlit(
            user_input=prompt, 
            st_container=final_answer_container
        )
        
        # Save final response to Streamlit chat history
        st.session_state.chat_history.append({"role": "assistant", "content": final_response, "is_final": True})

# Sidebar: System Diagnostics
with st.sidebar:
    # Show cached stock data
    cached_stocks = list(st.session_state.agent.tools.report_cache.keys())
    st.write(f"**Cached Stock Reports ({len(cached_stocks)}):**")
    if cached_stocks:
        st.code(", ".join(cached_stocks))
    else:
        st.write("None yet.")