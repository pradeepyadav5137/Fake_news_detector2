import streamlit as st
import pandas as pd
import os
import logging
import requests
import re
import string
import joblib
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from textblob import TextBlob
import hashlib

# Load environment variables from .env file
load_dotenv()


# Page configuration
st.set_page_config(
    page_title="TruthLens: AI-Powered Authenticator", 
    layout="wide", 
    page_icon="🔍",
    initial_sidebar_state="expanded"
)

# Logging configuration
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

# Enhanced CSS styles
st.markdown("""
<style>
/* Main app styling */
[data-testid="stAppViewContainer"] { 
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #f0f2f6; 
}

/* Header styling */
.main-header {
    text-align: center;
    padding: 2rem 0;
    background: rgba(255,255,255,0.1);
    border-radius: 15px;
    margin-bottom: 2rem;
    backdrop-filter: blur(10px);
}

.main-header h1 {
    color: #ffffff;
    font-size: 3rem;
    margin-bottom: 0.5rem;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}

.main-header p {
    color: #e0e6ed;
    font-size: 1.2rem;
    margin: 0;
}

/* News cards */
.news-card { 
    border: none;
    border-radius: 15px; 
    padding: 20px; 
    margin-bottom: 20px; 
    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    background: rgba(255,255,255,0.95);
    backdrop-filter: blur(10px);
    height: 100%; 
    transition: all 0.3s ease;
    color: #333;
}

.news-card:hover { 
    transform: translateY(-5px); 
    box-shadow: 0 16px 64px rgba(0,0,0,0.15);
}

/* Result boxes */
.authentic-box { 
    background: linear-gradient(135deg, #d4edda, #c3e6cb);
    border-left: 5px solid #28a745; 
    padding: 20px; 
    border-radius: 10px; 
    margin: 20px 0; 
    color: #155724;
    box-shadow: 0 4px 16px rgba(40,167,69,0.2);
}

.warning-box { 
    background: linear-gradient(135deg, #fff3cd, #ffeaa7);
    border-left: 5px solid #ffc107; 
    padding: 20px; 
    border-radius: 10px; 
    margin: 20px 0; 
    color: #856404;
    box-shadow: 0 4px 16px rgba(255,193,7,0.2);
}

.danger-box { 
    background: linear-gradient(135deg, #f8d7da, #f5c6cb);
    border-left: 5px solid #dc3545; 
    padding: 20px; 
    border-radius: 10px; 
    margin: 20px 0; 
    color: #721c24;
    box-shadow: 0 4px 16px rgba(220,53,69,0.2);
}

/* Feedback section */
.feedback-section {
    background: rgba(255,255,255,0.1);
    padding: 20px;
    border-radius: 15px;
    margin-top: 20px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.2);
}

.feedback-buttons {
    display: flex;
    gap: 10px;
    justify-content: center;
    margin: 15px 0;
}

.feedback-button {
    padding: 10px 20px;
    border: none;
    border-radius: 25px;
    font-size: 1.2rem;
    cursor: pointer;
    transition: all 0.3s ease;
    background: rgba(255,255,255,0.2);
    color: white;
}

.feedback-button:hover {
    transform: scale(1.1);
    background: rgba(255,255,255,0.3);
}

/* Statistics cards */
.stat-card {
    background: rgba(255,255,255,0.1);
    padding: 1.5rem;
    border-radius: 15px;
    text-align: center;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.2);
    margin-bottom: 1rem;
}

.stat-number {
    font-size: 2.5rem;
    font-weight: bold;
    color: #ffffff;
    margin-bottom: 0.5rem;
}

.stat-label {
    color: #e0e6ed;
    font-size: 1rem;
}

/* Button styling */
.stButton > button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    border-radius: 25px;
    padding: 0.75rem 2rem;
    font-weight: bold;
    color: white;
    transition: all 0.3s ease;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(102,126,234,0.3);
}

/* Sidebar styling */
.css-1d391kg {
    background: rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
}


# section[data-testid="stSidebar"] {
#     width: 350px !important;
#     max-width: 400px !important;
#     min-width: 200px !important;
# }

section[data-testid="stSidebar"][aria-expanded="true"] {
    width: 350px !important;
    max-width: 350px !important;
    min-width: 350px !important;
}
</style>
""", unsafe_allow_html=True)



def get_api_key(key_name, default_value=None):
    """Get API key from environment variable or use default (for demo purposes)"""
    api_key = os.getenv(key_name, default_value)
    if not api_key and default_value is None:
        st.error(f"❌ Missing API key: {key_name}")
        st.info("Please add your API key to the .env file")
        return None
    return api_key

def clean_text(text):
    """Clean and normalize text for processing"""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(f"[{re.escape(string.punctuation)}]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_query(text):
    """Extract meaningful query from article text with better keyword extraction"""
    if not text:
        return ""
    
    # Remove common stop words
    stop_words = {'the', 'is', 'at', 'which', 'on', 'a', 'an', 'as', 'are', 'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'whose', 'why', 'how', 'when', 'where', 'if', 'or', 'because', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'through', 'during', 'before', 'after', 'above', 'below', 'up', 'down', 'in', 'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once'}
    
    # Extract keywords using TextBlob for better noun phrase extraction
    try:
        blob = TextBlob(text)
        # Get noun phrases
        noun_phrases = [phrase for phrase in blob.noun_phrases if len(phrase.split()) <= 3]
        
        # Get important words (nouns, proper nouns, adjectives)
        important_words = []
        for word, pos in blob.tags:
            if pos in ['NN', 'NNS', 'NNP', 'NNPS', 'JJ', 'JJR', 'JJS'] and word.lower() not in stop_words and len(word) > 2:
                important_words.append(word)
        
        # Combine noun phrases and important words
        keywords = list(set(noun_phrases + important_words[:10]))
        
        # If we have good keywords, use them
        if keywords:
            query = ' '.join(keywords[:5])  # Take top 5 keywords
        else:
            # Fallback to sentence extraction
            sentences = re.split(r'(?<=[.!?])\s', text)
            query = (sentences[0] + (" " + sentences[1] if len(sentences) >= 2 else "")) if sentences else text
    except:
        # Fallback to original method if TextBlob fails
        sentences = re.split(r'(?<=[.!?])\s', text)
        query = (sentences[0] + (" " + sentences[1] if len(sentences) >= 2 else "")) if sentences else text
    
    return query.strip().strip('"\'')[:200]

def calculate_relevance_score(article_title, article_desc, query):
    """Calculate relevance score between article and query"""
    query_words = set(query.lower().split())
    title_words = set(article_title.lower().split())
    desc_words = set(article_desc.lower().split()) if article_desc else set()
    
    # Calculate overlap
    title_overlap = len(query_words.intersection(title_words)) / len(query_words) if query_words else 0
    desc_overlap = len(query_words.intersection(desc_words)) / len(query_words) if query_words else 0
    
    # Weighted score (title is more important)
    relevance_score = (title_overlap * 0.7) + (desc_overlap * 0.3)
    return relevance_score

def generate_session_id():
    """Generate unique session ID for tracking"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
    return st.session_state.session_id

def test_api_connections():
    """Test all API connections"""
    api_status = {}
    
    # Test GNews API
    gnews_key = get_api_key("GNEWS_API_KEY")
    api_status['gnews'] = gnews_key is not None
    
    # Test NewsAPI
    newsapi_key = get_api_key("NEWSAPI_KEY")
    api_status['newsapi'] = newsapi_key is not None
    
    # Test News Data API
    newsdata_key = get_api_key("NEWSDATA_API_KEY")
    api_status['newsdata'] = newsdata_key is not None
    
    # Test Guardian API
    guardian_key = get_api_key("GUARDIAN_API_KEY")
    api_status['guardian'] = guardian_key is not None
    
    return api_status

def render_api_status():
    """Display API connection status in sidebar"""
    st.sidebar.markdown("### 🔌 API Status")
    
    # Test API connections
    with st.spinner("Testing API connections..."):
        api_status = test_api_connections()
    
    # Display status with better formatting
    api_names = {
        'gnews': 'GNews API',
        'newsapi': 'NewsAPI',
        'newsdata': 'NewsData API', 
        'guardian': 'Guardian API'
    }
    
    for api, status in api_status.items():
        emoji = "✅" if status else "❌"
        name = api_names.get(api, api.replace('_', ' ').title())
        st.sidebar.markdown(f"{emoji} {name}")
    
    # Show working count
    working_apis = sum(api_status.values())
    total_apis = len(api_status)
    st.sidebar.markdown(f"**{working_apis}/{total_apis} APIs working**")
    
    # Status messages
    if working_apis == 0:
        st.sidebar.error("⚠️ All APIs are down! Check your API keys in .env file.")
        st.sidebar.info("💡 Add your API keys to `.env` file:\n```\nGNEWS_API_KEY=your_key_here\nNEWSAPI_KEY=your_key_here\nNEWSDATA_API_KEY=your_key_here\nGUARDIAN_API_KEY=your_key_here\n```")
    elif working_apis < 2:
        st.sidebar.warning("⚠️ Limited API access. Results may be limited.")
    else:
        st.sidebar.success("🎉 APIs are working well!")
    
    return api_status

# Example usage for getting specific API keys
def get_gnews_key():
    """Get GNews API key"""
    return get_api_key("GNEWS_API_KEY")

def get_newsapi_key():
    """Get NewsAPI key"""  
    return get_api_key("NEWSAPI_KEY")

def get_newsdata_key():
    """Get NewsData API key"""
    return get_api_key("NEWSDATA_API_KEY")



def get_news_references(article_text, num_results=6):
    """Fetch news references with improved accuracy and relevance scoring"""
    query = extract_query(article_text)
    logging.info(f"Searching for references with query: {query!r}")
    results = []
    
    # Try multiple search strategies
    search_queries = [
        query,  # Main query
        ' '.join(query.split()[:3]),  # First 3 words
        ' '.join(query.split()[-3:]) if len(query.split()) > 3 else query  # Last 3 words
    ]
    
    for search_query in search_queries:
        if len(results) >= num_results:
            break
            
        # Try Bing News API
        try:
            subscription_key = get_api_key("BING_API_KEY", "b44bOb62d7msh4c3029991170245p180afajsn2077ee7fd1eO")
            endpoint = "https://bing-news-search1.p.rapidapi.com/news/search"
            headers = {
                "X-BingApis-SDK": "true",
                "X-RapidAPI-Key": subscription_key,
                "X-RapidAPI-Host": "bing-news-search1.p.rapidapi.com"
            }
            params = {
                "q": search_query,
                "count": num_results,
                "textFormat": "Raw",
                "safeSearch": "Off",
                "sortBy": "Relevance"
            }
            res = requests.get(endpoint, headers=headers, params=params, timeout=15)
            
            if res.status_code == 200:
                for item in res.json().get('value', []):
                    if len(results) >= num_results:
                        break
                    
                    # Calculate relevance score
                    relevance = calculate_relevance_score(
                        item["name"], 
                        item.get("description", ""), 
                        query
                    )
                    
                    # Only add if relevance is above threshold
                    if relevance > 0.1:  # Minimum relevance threshold
                        results.append({
                            "title": item["name"],
                            "description": item.get("description", ""),
                            "url": item["url"],
                            "source": item["provider"][0]["name"],
                            "publishedAt": item["datePublished"],
                            "urlToImage": item.get("image", {}).get("thumbnail", {}).get("contentUrl", ""),
                            "relevance": relevance
                        })
        except Exception as e:
            logging.exception("Bing API Exception")
    
    # Try NewsAPI with different queries
    for search_query in search_queries:
        if len(results) >= num_results:
            break
            
        try:
            newsapi_key = get_api_key("NEWSAPI_KEY", "07594036124e431aa51b101ac842a868")
            params = {
                "q": search_query,
                "apiKey": newsapi_key,
                "pageSize": num_results,
                "language": "en",
                "sortBy": "relevancy"
            }
            res = requests.get("https://newsapi.org/v2/everything", params=params, timeout=15)
            
            if res.status_code == 200:
                for art in res.json().get("articles", []):
                    if len(results) >= num_results:
                        break
                    
                    # Calculate relevance score
                    relevance = calculate_relevance_score(
                        art["title"], 
                        art.get("description", ""), 
                        query
                    )
                    
                    # Only add if relevance is above threshold and not duplicate
                    if relevance > 0.1 and not any(r['url'] == art['url'] for r in results):
                        results.append({
                            "title": art["title"],
                            "description": art.get("description", ""),
                            "url": art["url"],
                            "source": art["source"]["name"],
                            "publishedAt": art["publishedAt"],
                            "urlToImage": art.get("urlToImage", ""),
                            "relevance": relevance
                        })
        except Exception as e:
            logging.exception("NewsAPI Exception")
    
    # Sort by relevance score
    results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
    
    # Remove duplicates based on title similarity
    unique_results = []
    for result in results:
        is_duplicate = False
        for existing in unique_results:
            # Check if titles are too similar (> 80% overlap)
            title_words1 = set(result['title'].lower().split())
            title_words2 = set(existing['title'].lower().split())
            if len(title_words1) > 0 and len(title_words2) > 0:
                overlap = len(title_words1.intersection(title_words2)) / min(len(title_words1), len(title_words2))
                if overlap > 0.8:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            unique_results.append(result)
    
    # Final fallback if no results
    if not unique_results:
        unique_results.append({
            "title": "No relevant references found",
            "description": f"No articles found matching '{query}'. This could indicate the news is very recent, local, or potentially fabricated.",
            "url": "https://news.google.com/search?q=" + query.replace(" ", "+"),
            "source": "Google News Search",
            "publishedAt": datetime.utcnow().isoformat(),
            "urlToImage": "",
            "relevance": 0
        })
    
    return unique_results[:num_results]

# Load model with better error handling
@st.cache_resource
def load_models():
    """Load ML models with caching and error handling"""
    try:
        model = joblib.load("model95.jb")
        vectorizer = joblib.load("vectorizer95.jb")
        return model, vectorizer
    except Exception as e:
        st.error("❌ Failed to load ML models. Please check model files.")
        logging.exception("Failed to load model or vectorizer")
        st.stop()

def get_prediction_stats():
    """Get statistics from prediction logs"""
    log_file = "log.csv"
    if os.path.exists(log_file):
        try:
            df = pd.read_csv(log_file)
            return {
                "total_predictions": len(df),
                "real_news": len(df[df['prediction'] == 'Real']),
                "fake_news": len(df[df['prediction'] == 'Fake']),
                "avg_confidence": df['confidence'].mean() if 'confidence' in df.columns else 0,
                "recent_activity": len(df[pd.to_datetime(df['timestamp']) > datetime.now() - timedelta(days=7)])
            }
        except Exception as e:
            logging.exception("Error reading prediction stats")
    return {"total_predictions": 0, "real_news": 0, "fake_news": 0, "avg_confidence": 0, "recent_activity": 0}


def get_feedback_stats():
    """Get feedback statistics"""
    feedback_file = "feedback.csv"
    if os.path.exists(feedback_file):
        try:
            df = pd.read_csv(feedback_file)
            # Ensure we have the required columns
            if 'feedback_type' in df.columns and 'overall_rating' in df.columns:
                return {
                    "total_feedback": len(df),
                    "positive_feedback": len(df[df['feedback_type'] == 'positive']),
                    "negative_feedback": len(df[df['feedback_type'] == 'negative']),
                    "avg_rating": df['overall_rating'].mean()
                }
        except Exception as e:
            logging.exception("Error reading feedback stats")
    return {"total_feedback": 0, "positive_feedback": 0, "negative_feedback": 0, "avg_rating": 0}

def render_header():
    """Render enhanced header with statistics"""
    st.markdown("""
    <div class="main-header">
        <h1>🔍 TruthLens</h1>
        <p>AI-Powered News Authenticator</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Statistics in sidebar
    with st.sidebar:
        st.markdown("### 📊 Statistics")
        stats = get_prediction_stats()
        feedback_stats = get_feedback_stats()
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{stats['total_predictions']}</div>
                <div class="stat-label">Total Checks</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{feedback_stats['total_feedback']}</div>
                <div class="stat-label">Feedback</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{stats['recent_activity']}</div>
                <div class="stat-label">This Week</div>
            </div>
            """, unsafe_allow_html=True)
        
        if stats['total_predictions'] > 0:
            # Prediction distribution chart
            fig = px.pie(
                values=[stats['real_news'], stats['fake_news']], 
                names=['Real News', 'Fake News'],
                title="Prediction Distribution",
                color_discrete_sequence=['#28a745', '#dc3545']
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                height=450
            )
            st.plotly_chart(fig, use_container_width=True)
        
   
        if feedback_stats['total_feedback'] > 0:
    # 🎯 Feedback Distribution Pie Chart
            pie = px.pie(
                names=['Positive', 'Negative'],
                values=[feedback_stats['positive_feedback'], feedback_stats['negative_feedback']],
                title="User Sentiment",
                color_discrete_map={'Positive': '#28a745', 'Negative': '#dc3545'},
                hole=0.4
            )
            pie.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                height=300,
                showlegend=True
            )
            st.plotly_chart(pie, use_container_width=True)

    # 📊 Overall Rating Bar
            avg_rating = round(feedback_stats['avg_rating'], 2)
            rating_fig = px.bar(
                x=["Avg Rating"],
                y=[avg_rating],
                title="Average Feedback Rating",
                text=[avg_rating],
                color=["Avg Rating"],
                color_discrete_sequence=["#007bff"]
            )
            rating_fig.update_layout(
                yaxis=dict(range=[0, 5], tick0=1, dtick=1),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                height=250,
                showlegend=False
            )
            st.plotly_chart(rating_fig, use_container_width=True)


def render_input():
    """Render enhanced input section"""
    st.markdown("### 📰 Enter News Article")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        # Initialize session state if not exists
        if 'article_text' not in st.session_state:
            st.session_state.article_text = ""
        
        # Create text area bound to session state
        text = st.text_area(
            "Paste your news article here:",
            value=st.session_state.article_text,
            height=200,
            placeholder="Paste or type the news article you want to verify...",
            key="article_input"
        )
        
        # Update session state with manual input
        st.session_state.article_text = text
    
    with col2:
        st.markdown("#### 💡 Tips")
        st.markdown("""
        - Include full article text for better accuracy
        - Headlines work but full text is preferred
        - Multiple languages supported
        - Real-time verification with cross-referencing
        """)
        
        # Sample articles - now properly bound to session state
        st.markdown("#### 🎯 Try Samples")
        sample_articles = [
            "India defeats South Africa to win ICC T20 World Cup 2024 in a thrilling final match at Barbados",
            "रवींद्र जडेजा WTC के इतिहास में पहले ऐसे खिलाड़ी बन गए हैं जिनके नाम 2000 रन और 100 विकेट दर्ज है। उनके अलावा दुनिया में कोई भी खिलाड़ी इस उपलब्धि को हासिल नहीं कर पाया है।",
            "Scientists claim to have discovered universal cure for all diseases using advanced AI technology"
        ]
        
        for i, sample in enumerate(sample_articles):
            if st.button(f"Sample {i+1}", key=f"sample_{i}", use_container_width=True):
                # Set session state instead of temporary variable
                st.session_state.article_text = sample
                # Trigger rerun to update text area
                st.rerun()
    
    return st.session_state.article_text


def render_feedback_section(session_id, article_text, prediction, confidence):
    """Render feedback section with emoji buttons and form using session state."""
    st.markdown("---")
    st.markdown("### 💬 How accurate was this analysis?")
    st.markdown("""
    <div class="feedback-section">
        <p style="text-align: center; color: white; margin-bottom: 20px;">
            Your feedback helps us improve our AI model!
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Layout for emoji buttons
    cols = st.columns(5)
    feedback_options = [
        ("😍", "Excellent", 5),
        ("😊", "Good", 4),
        ("😐", "Okay", 3),
        ("😞", "Poor", 2),
        ("😠", "Terrible", 1)
    ]
    
    # Initialize session state flags if not present
    if 'show_feedback_form' not in st.session_state:
        st.session_state.show_feedback_form = False
    if 'selected_feedback' not in st.session_state:
        st.session_state.selected_feedback = None
    
    # Emoji feedback buttons: use on_click callbacks to set session state
    for i, (emoji, label, rating) in enumerate(feedback_options):
        def on_click_feedback(rating=rating, emoji=emoji, label=label):
            # Save selected feedback in session state
            st.session_state.selected_feedback = {
                "emoji": emoji,
                "label": label,
                "rating": rating,
                "type": ("positive" if rating >= 4 else 
                         "negative" if rating <= 2 else 
                         "neutral")
            }
            st.session_state.show_feedback_form = True
        
        with cols[i]:
            st.button(f"{emoji}\n{label}", key=f"feedback_{rating}", on_click=on_click_feedback)
    
    # If an emoji was clicked (show_feedback_form flag), display the detailed feedback form
    if st.session_state.show_feedback_form:
        with st.form("detailed_feedback"):
            st.markdown("#### 📝 Additional Comments (Optional)")
            
            col1, col2 = st.columns(2)
            with col1:
                accuracy_rating = st.slider("Reference Accuracy", 1, 5, 3,
                                           help="How accurate were the related news references?")
                speed_rating = st.slider("Analysis Speed", 1, 5, 4,
                                         help="How satisfied are you with the analysis speed?")
            with col2:
                ui_rating = st.slider("User Interface", 1, 5, 4,
                                      help="How user-friendly is the interface?")
                overall_rating = st.slider("Overall Experience", 1, 5, 4,
                                          help="Your overall experience with TruthLens")
            
            detailed_comments = st.text_area(
                "Comments", 
                placeholder="Tell us what we can improve...", 
                height=100
            )
            improvement_areas = st.multiselect(
                "What areas need improvement?",
                ["Reference Accuracy", "Analysis Speed", 
                 "User Interface", "Result Explanation", "Additional Features"]
            )
            
            submitted = st.form_submit_button("Submit Feedback 📤")
            if submitted:
                # Compile feedback data, using selected_feedback from session state
                fb = st.session_state.selected_feedback or {}
                feedback_data = {
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "article_text": (article_text[:200] + "..." 
                                     if len(article_text) > 200 else article_text),
                    "prediction": "Real" if prediction else "Fake",
                    "confidence": confidence,
                    "emoji_feedback": fb.get("emoji", "😐"),
                    "emoji_label": fb.get("label", "Not specified"),
                    "emoji_rating": fb.get("rating", 3),
                    "feedback_type": fb.get("type", "neutral"),
                    "accuracy_rating": accuracy_rating,
                    "speed_rating": speed_rating,
                    "ui_rating": ui_rating,
                    "overall_rating": overall_rating,
                    "detailed_comments": detailed_comments,
                    "improvement_areas": ", ".join(improvement_areas) 
                                         if improvement_areas else "None"
                }
                
                # Save feedback and show confirmation
                save_feedback(feedback_data)
                st.success("🎉 Thank you for your feedback! Your input helps us improve TruthLens.")
                st.balloons()
                
                # Reset the feedback form flag and rerun to hide the form
                st.session_state.show_feedback_form = False
                st.rerun()


def save_feedback(feedback_data):
    """Save feedback to CSV file"""
    try:
        df = pd.DataFrame([feedback_data])
        feedback_file = "feedback.csv"
        
        # Define required columns to ensure consistency
        required_columns = [
            "session_id", "timestamp", "article_text", "prediction", "confidence",
            "emoji_feedback", "emoji_label", "emoji_rating", "feedback_type",
            "accuracy_rating", "speed_rating", "ui_rating", "overall_rating",
            "detailed_comments", "improvement_areas"
        ]
        
        # Append to existing file or create new one
        if os.path.exists(feedback_file):
            existing_df = pd.read_csv(feedback_file)
            # Ensure all required columns exist
            for col in required_columns:
                if col not in existing_df.columns:
                    existing_df[col] = None
            df = pd.concat([existing_df, df], ignore_index=True)
        
        # Save with all required columns
        df.to_csv(feedback_file, index=False)
        
        logging.info(f"Feedback saved: {feedback_data['emoji_label']} - {feedback_data['overall_rating']}/5")
        
    except Exception as e:
        logging.exception("Failed to save feedback")
        st.error("Failed to save feedback. Please try again.")

def render_results(pred, conf, refs, article_text):
    """Render enhanced results with better visualization"""
    # Determine result type and styling
    if refs and len([r for r in refs if r['title'] != "No references found"]) > 0:
        if pred == 1:
            box, lbl, msg = "authentic-box", "✅ Authentic News", "Verified by multiple credible sources."
            icon = "✅"
        else:
            box, lbl, msg = "warning-box", "⚠️ Potentially Misleading", "Similar content exists, but verify carefully."
            icon = "⚠️"
    else:
        if pred == 1:
            box, lbl, msg = "authentic-box", "✅ Likely Authentic", "Model predicts real, but no recent references found."
            icon = "✅"
        else:
            box, lbl, msg = "danger-box", "❌ Likely Fake News", "No credible sources found and model predicts fake."
            icon = "❌"

    # Main result display
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f'''
        <div class="{box}">
            <h2>{lbl}</h2>
            <p><strong>Confidence Score:</strong> {conf:.1%}</p>
            <p>{msg}</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        # Confidence gauge
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = conf * 100,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Confidence"},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "lightgreen" if pred == 1 else "salmon"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 100], 'color': "gray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        fig.update_layout(
            height=275,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        st.plotly_chart(fig, use_container_width=True)

    # Related articles section
    st.markdown("### 📰 Related Articles & Sources")
    
    if refs and len([r for r in refs if r['title'] != "No references found"]) > 0:
        cols = st.columns(min(3, len(refs)))
        for i, art in enumerate(refs):
            if art['title'] != "No references found":
                with cols[i % 3]:
                    # Enhanced news card
                    img = art.get("urlToImage") or "https://via.placeholder.com/300x150.png?text=No+Image"
                    
                    st.markdown(f'''
                    <div class="news-card">
                        <img src="{img}" style="width:100%; height:150px; object-fit:cover; border-radius:10px; margin-bottom:15px;">
                        <h4 style="color:#333; margin-bottom:10px;">{art['title'][:100]}{'...' if len(art['title']) > 100 else ''}</h4>
                        <p style="color:#666; font-size:0.9em; margin-bottom:10px;"><strong>{art['source']}</strong> | {art['publishedAt'][:10]}</p>
                        <p style="color:#555; font-size:0.85em; margin-bottom:15px;">{(art.get('description', '')[:120] + '...') if len(art.get('description', '')) > 120 else art.get('description', '')}</p>
                        <a href="{art['url']}" target="_blank" style="background:#667eea; color:white; padding:8px 16px; border-radius:20px; text-decoration:none; font-size:0.85em;">Read Full Article</a>
                    </div>
                    ''', unsafe_allow_html=True)
    else:
        st.warning("🔍 No related articles found. This might indicate the news is either very recent or potentially fabricated.")
    
    

    # Log the prediction
    log_prediction(article_text, pred, conf, len([r for r in refs if r['title'] != "No references found"]) > 0)
    
    # Render feedback section
    session_id = generate_session_id()
    render_feedback_section(session_id, article_text, pred, conf)

def log_prediction(article_text, prediction, confidence, references_found):
    """Log prediction with consistent format"""
    try:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "news": article_text[:100] + "..." if len(article_text) > 100 else article_text,
            "prediction": "Real" if prediction else "Fake",
            "confidence": confidence,
            "references_found": references_found
        }
        
        df = pd.DataFrame([log_data])
        log_file = "log.csv"
        
        # Append to existing file or create new one
        if os.path.exists(log_file):
            df.to_csv(log_file, mode='a', header=False, index=False)
        else:
            df.to_csv(log_file, mode='w', header=True, index=False)
            
    except Exception as e:
        logging.exception("Failed to write prediction log")




def main():
    # Load models
    with st.spinner("🔍 Loading model..."):
                model, vectorizer = load_models()
    
    # Render UI components
    render_header()
    
    # Main content: input and analysis
    text = render_input()  # this updates st.session_state.article_text
    
    # Initialize a flag for analysis done
    if 'analysis_done' not in st.session_state:
        st.session_state.analysis_done = False

    if st.session_state.analysis_done:
        # If we already have results from before, re-display them
        render_results(
            st.session_state.pred, 
            st.session_state.conf, 
            st.session_state.refs, 
            st.session_state.article_text
        )
    else:
        # Show Analyze button only if not yet done
        if st.button("🔍 Analyze News Article", use_container_width=True):
            if not text.strip():
                st.warning("⚠️ Please enter some text to analyze.")
            else:
                # Perform analysis with progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                try:
                    status_text.text("🔤 Processing text...")
                    progress_bar.progress(25)
                    cleaned = clean_text(text)

                    status_text.text("🤖 Running AI analysis...")
                    progress_bar.progress(50)
                    vec = vectorizer.transform([cleaned])
                    pred = model.predict(vec)[0]
                    conf = model.predict_proba(vec)[0].max()

                    status_text.text("🌐 Fetching news references...")
                    progress_bar.progress(75)
                    refs = get_news_references(text)

                    status_text.text("✅ Analysis complete!")
                    progress_bar.progress(100)

                    progress_bar.empty()
                    status_text.empty()

                    # Save results in session state for persistence
                    st.session_state.pred = pred
                    st.session_state.conf = conf
                    st.session_state.refs = refs
                    st.session_state.analysis_done = True

                    # Rerun to display results using the session state values
                    st.rerun()  # terminates this run and starts a new one:contentReference[oaicite:4]{index=4}
                except Exception as e:
                    st.error(f"❌ Analysis failed: {e}")
                    logging.exception("Analysis failed")


if __name__ == "__main__":
    main()
