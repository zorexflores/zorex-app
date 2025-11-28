import streamlit as st
import json
import sys
from pathlib import Path
from datetime import datetime

# Ensure current directory is in path
sys.path.insert(0, str(Path(__file__).parent))

# Import local modules
from answer_pipeline_wrapper import AnswerPipeline
from resources_qa import ResourcesQA

# Page config
st.set_page_config(page_title="Zorex Knowledge Dashboard", layout="wide", initial_sidebar_state="expanded")

# Initialize session state
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False
if 'recently_viewed' not in st.session_state:
    st.session_state.recently_viewed = []
if 'qa_history' not in st.session_state:
    st.session_state.qa_history = []

# Dark mode toggle in sidebar
with st.sidebar:
    st.title("⚙️ Settings")
    dark_mode = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)
    if dark_mode != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_mode
        st.rerun()

# Apply dark mode styling
if st.session_state.dark_mode:
    st.markdown("""
        <style>
        .stApp {
            background-color: #1E1E1E;
            color: #FFFFFF;
        }
        .stTextInput > div > div > input {
            background-color: #2D2D2D;
            color: #FFFFFF;
        }
        </style>
    """, unsafe_allow_html=True)

# Main title
st.title("🧬 Zorex Knowledge Dashboard")

# Create tabs

# User Guide in sidebar
with st.sidebar:
    st.markdown("---")
    with st.expander("📖 User Guide", expanded=False):
        st.markdown("""
        ### Quick Start
        
        **Product Summaries Tab:**
        1. Type product name in search box
        2. Click "Get Summary" 
        3. View: What conditions, How it works, Why choose this
        
        **Resources Q&A Tab:**
        1. Type your question (e.g., "vitamin D dosage")
        2. Click "Search"
        3. Review highlighted results from manuals
        
        ### Tips
        - Search is case-insensitive ("b6" finds "B6 B1")
        - Partial names work ("immune" finds all immune products)
        - Recently viewed products appear in sidebar
        
        ### Troubleshooting
        - **No results?** Try shorter search terms
        - **Slow?** First search builds cache, then fast
        - **Wrong product?** Check dropdown for similar names
        """)


tab1, tab2 = st.tabs(["📦 Product Summaries", "📚 Resources Q&A"])

# TAB 1: Product Summaries
with tab1:
    st.markdown("### Product Literature Summaries")
    st.markdown("Get benefit-first summaries of Zorex product literature")
    
    # Load pipeline and products
    @st.cache_resource
    def load_pipeline():
        return AnswerPipeline()
    
    try:
        pipeline = load_pipeline()
        all_products = pipeline.get_product_list()
        
        if not all_products:
            st.warning("No product files found")
        else:
            # Use form to enable Enter key
            with st.form(key="product_form", clear_on_submit=False):
                # SEARCH FILTER
                search_term = st.text_input(
                    "🔍 Search products:",
                    placeholder="Type to filter products...",
                    key="product_search"
                )
                
                # Filter products based on search
                if search_term:
                    filtered_products = [p for p in all_products if search_term.lower() in p.lower()]
                    if not filtered_products:
                        st.warning(f"No products found matching '{search_term}'")
                        filtered_products = all_products
                else:
                    filtered_products = all_products
                
                st.caption(f"Showing {len(filtered_products)} of {len(all_products)} products")
                
                # Product selection
                col1, col2 = st.columns([3, 1])
                with col1:
                    selected_product = st.selectbox(
                        "Select a product:",
                        options=filtered_products,
                        index=0,
                        key="product_selector",
                        label_visibility="collapsed"
                    )
                with col2:
                    search_button = st.form_submit_button("🔍 Get Summary", type="primary", use_container_width=True)
            
            # Display summary when button clicked
            if search_button and selected_product:
                # Add to recently viewed (keep last 5 unique)
                if selected_product in st.session_state.recently_viewed:
                    st.session_state.recently_viewed.remove(selected_product)
                st.session_state.recently_viewed.insert(0, selected_product)
                st.session_state.recently_viewed = st.session_state.recently_viewed[:5]
                
                with st.spinner('Generating summary...'):
                    try:
                        summary = pipeline.get_cached_summary(selected_product)
                        
                        # Display in a nice card
                        st.markdown(f"""
                            <div style='padding: 20px; border-radius: 10px; background-color: {"#2D2D2D" if st.session_state.dark_mode else "#F0F2F6"}; margin: 10px 0;'>
                                <h3 style='margin-top: 0; color: {"#FFFFFF" if st.session_state.dark_mode else "#1E1E1E"};'>
                                    {selected_product}
                                </h3>
                                <div style='font-size: 16px; line-height: 1.6; color: {"#E0E0E0" if st.session_state.dark_mode else "#333333"};'>
                                    {summary}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        st.success("✅ Summary generated successfully!")
                        
                    except Exception as e:
                        st.error(f"Error generating summary: {str(e)}")
    
    except Exception as e:
        st.error(f"Error loading products: {str(e)}")

# TAB 2: Resources Q&A
with tab2:
    st.markdown("### Ask Questions About Manuals")
    st.markdown("Search across all Zorex manuals and protocols for specific information")
    
    # Initialize QA system
    @st.cache_resource
    def load_qa_system():
        return ResourcesQA()
    
    try:
        qa = load_qa_system()
        
        # Question input with form to enable Enter key
        with st.form(key="qa_form", clear_on_submit=False):
            question = st.text_input(
                "Ask a question:",
                placeholder="e.g., What is the recommended dosage for vitamin D?",
                key="qa_question_input"
            )
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                num_results = st.selectbox("Show results:", [3, 5, 10], index=0)
            with col2:
                search_qa = st.form_submit_button("🔍 Search", type="primary", use_container_width=True)
        
        # Perform search
        if search_qa and question:
            # Add to Q&A history
            st.session_state.qa_history.insert(0, {
                'question': question,
                'timestamp': datetime.now().strftime("%I:%M %p"),
                'result_count': 0
            })
            st.session_state.qa_history = st.session_state.qa_history[:10]
            
            with st.spinner('Searching manuals...'):
                results = qa.search(question, max_results=num_results)
                
                # Update result count
                if st.session_state.qa_history:
                    st.session_state.qa_history[0]['result_count'] = len(results)
                
                if results:
                    st.markdown(f"**Found {len(results)} relevant page(s):**")
                    
                    # Display results with highlighted keywords
                    for i, result in enumerate(results, 1):
                        manual_name = result['file'].replace('.pdf', '').replace('_', ' ')
                        
                        with st.expander(f"📄 {manual_name} - Page {result['page']} (Relevance: {result['score']} matches)", expanded=(i==1)):
                            # Highlighted key excerpt
                            st.markdown("**📌 Key Excerpt:**")
                            highlighted_snippet = qa.highlight_keywords(result['snippet'], result['keywords'])
                            st.info(highlighted_snippet)
                            
                            st.markdown("---")
                            
                            # Contextual excerpt with keywords highlighted
                            st.markdown("**📖 Relevant Context:**")
                            highlighted_context = qa.highlight_keywords(result['context'], result['keywords'])
                            st.markdown(highlighted_context)
                            
                            # Full page text in collapsible section
                            st.markdown("---")
                            if st.checkbox(f"📄 Show complete page text", key=f"fulltext_{i}"):
                                with st.container():
                                    st.markdown("**Complete Page Text:**")
                                    st.text(result['text'])
                else:
                    st.warning("No relevant information found. Try rephrasing your question.")
        
        # Example questions
        st.markdown("---")
        st.markdown("**💡 Example Questions:**")
        example_cols = st.columns(3)
        with example_cols[0]:
            if st.button("Vitamin D dosage?", use_container_width=True):
                st.rerun()
        with example_cols[1]:
            if st.button("Blood chemistry?", use_container_width=True):
                st.rerun()
        with example_cols[2]:
            if st.button("Progesterone benefits?", use_container_width=True):
                st.rerun()
        
        # Show available manuals
        with st.expander("📚 Available Manuals"):
            manuals = {}
            for page in qa.index:
                file = page['file']
                if file not in manuals:
                    manuals[file] = 0
                manuals[file] += 1
            
            col_a, col_b = st.columns(2)
            for idx, (manual, page_count) in enumerate(sorted(manuals.items())):
                with col_a if idx % 2 == 0 else col_b:
                    st.markdown(f"📄 **{manual.replace('.pdf', '')}** ({page_count} pages)")
                
    except FileNotFoundError:
        st.error("⚠️ Manual index not found. Please run `python3 process_manuals.py` first.")
    except Exception as e:
        st.error(f"⚠️ Error loading Q&A system: {str(e)}")

# Sidebar info
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📊 Dashboard Stats")
    
    try:
        pipeline = load_pipeline()
        st.metric("Products Indexed", len(pipeline.get_product_list()))
    except:
        st.metric("Products Indexed", "N/A")
    
    try:
        with open('manuals_index.json', 'r') as f:
            manual_pages = len(json.load(f))
        st.metric("Manual Pages Indexed", manual_pages)
    except:
        st.metric("Manual Pages Indexed", "N/A")
    
    # Recently Viewed Products
    if st.session_state.recently_viewed:
        st.markdown("---")
        st.markdown("### 🕐 Recently Viewed")
        for product in st.session_state.recently_viewed:
            if st.button(f"📦 {product[:30]}...", key=f"recent_{product}", use_container_width=True):
                st.rerun()
    
    # Recent Q&A searches
    if st.session_state.qa_history:
        st.markdown("---")
        st.markdown("### 🔍 Recent Searches")
        for i, search in enumerate(st.session_state.qa_history[:5]):
            st.caption(f"**{search['timestamp']}** - {search['question'][:40]}... ({search['result_count']} results)")
    
    st.markdown("---")
    st.markdown("**🔧 Built with:**")
    st.markdown("- Benefit-first summaries")
    st.markdown("- Citation-based Q&A")
    st.markdown("- Smart search & history")
    st.sidebar.markdown("")
    st.sidebar.markdown("""
    <div style='font-size: 10px; color: #666; padding: 8px; background-color: #f9f9f9; border-radius: 4px; margin-top: 10px;'>
    ⚠️ <strong>Disclaimer:</strong> These statements have not been evaluated by the FDA. 
    These products are not intended to diagnose, treat, cure, or prevent any disease. 
    For professional use only.
    </div>
    """, unsafe_allow_html=True)

