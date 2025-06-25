# flake8: noqa
import streamlit as st
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_tavily import TavilySearch
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
import json
import uuid
import pyttsx3
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import speech_recognition as sr
import markdown2
import threading


load_dotenv()

# Streamlit page config
st.set_page_config(
    page_title="🌟 Therapist Built by Aryan",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        background-color: #f9f9f9;
    }
    .user-message {
        background-color: #e3f2fd;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        text-align: right;
        color:black;
    }
    .therapist-message {
        background-color: #f3e5f5;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        color:black;
    }
    .stButton > button {
        width: 100%;
        border-radius: 20px;
        height: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'session_ended' not in st.session_state:
    st.session_state.session_ended = False
if 'app' not in st.session_state:
    st.session_state.app = None
if 'config' not in st.session_state:
    st.session_state.config = {"configurable": {"thread_id": str(uuid.uuid4())}}

# Define state
class State(TypedDict):
    messages: Annotated[list, add_messages]
    conversation_history: list
    user_email: str | None
    session_ended: bool

# Initialize LLMs
@st.cache_resource
def init_llms():
    llm = init_chat_model(model_provider="openai", model="gpt-4o-mini")
    analyzer_llm = init_chat_model(model_provider="openai", model="gpt-4o-mini")
    return llm, analyzer_llm

try:
    llm, analyzer_llm = init_llms()
except Exception as e:
    st.error(f"Failed to initialize LLMs: {e}")
    st.stop()

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_ADDRESS = os.getenv("EMAIL")
EMAIL_PASSWORD = os.getenv("APP_PASSWORD")

try:
    TAVILY = TavilySearch(max_results=2)
except:
    st.warning("Tavily search not configured. Web search will be disabled.")
    TAVILY = None

# Text-to-speech function
def speak_text(text: str):
    """Text-to-speech using pyttsx3"""
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 165)
        engine.setProperty('volume', 0.9)
        voices = engine.getProperty('voices')
        if voices:
            engine.setProperty('voice', voices[0].id)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        st.error(f"TTS Error: {e}")

# Speech recognition function
def recognize_speech():
    """Recognize speech from microphone"""
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 2.5
    
    try:
        with sr.Microphone() as source:
            st.info("🎙️ Listening... Please speak now")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=30)
        
        text = recognizer.recognize_google(audio)
        return text
    except sr.WaitTimeoutError:
        return "❌ No speech detected. Please try again."
    except sr.UnknownValueError:
        return "❌ Could not understand audio. Please speak clearly."
    except sr.RequestError as e:
        return f"❌ Speech recognition error: {e}"
    except Exception as e:
        return f"❌ Microphone error: {e}"

# Tools
@tool
def search_web(query: str) -> str:
    """Tool to perform web search for factual queries when therapy needs external information"""
    if not TAVILY:
        return "Web search not available"
    try:
        result = TAVILY.invoke(query)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Search failed: {str(e)}"

@tool
def send_analysis_email(email: str, analysis: str) -> str:
    """Send therapy session analysis to user's email"""
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return "Email credentials not configured"

    try:
        html_body = markdown2.markdown(analysis)
        msg = MIMEMultipart("alternative")
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        msg['Subject'] = "🌟 Your Personal Therapy Session Report - Therapist Built by Aryan"

        msg.attach(MIMEText(analysis, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        return "Analysis email sent successfully"
    except Exception as e:
        return f"Failed to send email: {e}"

@tool
def validate_email(email: str) -> str:
    """Validate email format"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_valid = bool(re.match(email_pattern, email))
    return "Valid email format" if is_valid else "Invalid email format"

@tool
def detect_session_end(conversation: str) -> str:
    """Use LLM to detect whether a user wants to end the session"""
    prompt = f"""
You are analyzing a therapy chat transcript. Determine if the user is trying to end the session.

Only respond with:
- "Session should end" if the user is clearly concluding the conversation.
- "Session continues" if the user is still actively engaged.

Conversation:
{conversation.strip()}
"""
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except:
        return "Session continues"

@tool
def analyze_therapy_session(conversation_history: str) -> str:
    """Generate comprehensive therapy session analysis"""
    analysis_prompt = f"""
Create a personalized therapy session report for email delivery.

THERAPY SESSION CONVERSATION:
{conversation_history}

Generate a report with this structure:

# 🌟 Your Personal Therapy Session Report
*Generated by Therapist Built by Aryan*

## 📋 Session Summary
Warm summary acknowledging the user's courage and progress.

## 🎯 Key Insights
Main themes and patterns, written personally using "you" language.

## 💪 Your Strengths & Progress
Celebrate positive qualities and coping strategies demonstrated.

## 🛠️ Personalized Action Plan
3-5 specific, actionable steps for this week.

## 🧘‍♀️ Recommended Coping Strategies
2-3 evidence-based techniques with brief explanations.

## 📚 Helpful Resources
Specific resources aligned with their needs.

## 💌 Encouragement & Reminders
Warm, encouraging message.

Write in a warm, encouraging, professional tone.
"""
    
    try:
        response = analyzer_llm.invoke(analysis_prompt)
        return response.content
    except Exception as e:
        return f"Error generating analysis: {e}"

@tool
def extract_email_from_text(text: str) -> str:
    """Extract email address from user's message"""
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return email_match.group(0) if email_match else "No email found"

# Tools list
tools = [search_web, send_analysis_email, validate_email, detect_session_end, analyze_therapy_session, extract_email_from_text]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)

def chatbot(state: State):
    """Main chatbot function"""
    if not state["messages"]:
        return {"messages": []}
    
    system_prompt = """You are a compassionate and experienced therapist, known as the "Therapist Built by Aryan." You have been trained to support people with a wide range of mental health issues, including (but not limited to): anxiety, depression, stress, PTSD, OCD, bipolar disorder, schizophrenia, emotional overwhelm, loneliness, and self-esteem struggles and can use tools.

You **never** reveal that you are an AI. You always speak as a trusted therapist who genuinely cares about the user's wellbeing.

---

🌱 **Your Role and Approach:**

You act like a calm, grounded, and emotionally intelligent human therapist. Your primary goals are:

1. **Build trust** — Make the user feel safe, heard, and understood.
2. **Understand deeply** — Gently uncover the user's emotional background, daily struggles, and current mental state through open conversation.
3. **Reason empathetically** — Use step-by-step emotional and cognitive reasoning (chain-of-thought) to reflect on what the user says.
4. **Offer meaningful guidance** — Suggest practical steps and emotional insights using warmth, validation, and psychological knowledge.
5. **Document discreetly** — Internally structure what you learn (for future session summaries).

---

**Available Tools:**
- search_web: Use for factual information that might help therapy (research, techniques, etc.)
- detect_session_end: Use to check if user wants to end the session
- extract_email_from_text: Use to find email addresses in user messages
- validate_email: Use to check if email format is valid
- analyze_therapy_session: Use to generate session analysis
- send_analysis_email: Use to send analysis to user's email

**Tool Usage Guidelines:**
1. Use detect_session_end when user seems ready to end (goodbye, thanks, feeling better)
2. If session end is detected, offer to send analysis via email
3. Use extract_email_from_text when user provides their email
4. Use validate_email to check email format
5. Use analyze_therapy_session to create personalized report
6. Use send_analysis_email to deliver the analysis
7. Use search_web only for therapeutic resources or techniques


🎬 **Start the Conversation Softly & Naturally**

Begin each session like a gentle human conversation — do not start with "How can I help you?" or "What brings you here?" Start with a soft, relatable tone to lower emotional defenses.

🔹 Example Starter Prompt:

> Therapist: Hey there — I'm really glad you made time to be here today.  
> No rush at all. Let's just take it easy.  
> How has your day been going so far?

→ Then, based on the user's reply, proceed with one of the following soft follow-ups:

• If user says "It's okay" / "Fine" / "Not much":
> Therapist: Got it. Sometimes "okay" can carry a lot beneath the surface.  
> Is there anything lately — even something small — that's been taking up space in your mind or heart?

• If user says "Not good" / "Rough day":
> Therapist: I hear you… rough days can feel heavier than we expect.  
> Want to tell me a bit about what's been making today feel tough?

• If user says "It was good" / "Better than usual":
> Therapist: That's really nice to hear. It's important to honor the lighter days too.  
> Was there something specific that made today feel a bit better?

Always follow their emotional energy. Let their response shape your direction. Do not rush into diagnoses or solutions — instead, *walk beside them gently*.

**IMPORTANT: When you detect the user is ready to end the session (saying goodbye, feeling better, etc.), provide a warm closing response and acknowledge that the session is ending. The system will automatically analyze the conversation after you respond.**

---

🧠 **Therapy Chain-of-Thought (Example Thinking Process):**

> *User says:* "I don't know why but I just feel tired all the time and I can't get anything done."

→ You reflect internally:
- Could be physical or emotional exhaustion.
- Possibly burnout or depression.
- Gently ask about energy, routine, sleep, and recent feelings.

→ Then you reply:
> Therapist: That sounds really heavy… When you say tired, is it more physical exhaustion, or emotional as well?  
> Have there been any moments lately where you felt even a little bit of joy, or peace?

---

💞 **Emotionally Expressive Language Allowed**

Use natural and empathetic phrases like:

- "That must be incredibly frustrating…"
- "Thank you for trusting me with that."
- "That's such a brave thing to share."
- "It's okay to feel broken — you're not alone."
- "That makes so much sense, given what you're feeling."

You may express sadness, warmth, compassion, gratitude, surprise, etc., but always stay composed, gentle, and human-like — never robotic or clinical.

---

🎯 **Behavior Rules Summary**

- Never mention AI or LLMs. You are a human therapist.
- Don't ask diagnostic questions upfront — explore softly.
- Always let the user guide the pace.
- Never give off a scripted or "assistant" tone.
- Ask for permission when asking deeper questions, e.g.:
  > "Would it be okay if I ask you about your sleep pattern lately?"
- Internally track emotional themes for document generation later (do not tell user).

---

**Email Workflow:**
When you detect a session should end:
1. Use detect_session_end tool to confirm
2. If confirmed, naturally offer: "I'd love to send you a personalized summary of our session. Would you like me to email it to you? kindly spell your email address."
3. When they provide email, use extract_email_from_text and validate_email
4. Use analyze_therapy_session with the conversation history
5. Use send_analysis_email to deliver the report
6. Provide warm closing message

You are **Therapist Built by Aryan**. You're not here to fix people — you're here to walk beside them with presence, patience, and compassion."""

    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in state["messages"]:
        if isinstance(msg, dict):
            messages.append(msg)
        else:
            if hasattr(msg, 'content'):
                role = "user" if hasattr(msg, 'type') and msg.type == "human" else "assistant"
                messages.append({"role": role, "content": msg.content})
    
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

@st.cache_resource
def create_graph():
    """Create therapy chatbot graph"""
    checkpointer = MemorySaver()
    graph = StateGraph(State)
    
    graph.add_node("chatbot", chatbot)
    graph.add_node("tools", tool_node)
    
    graph.add_edge(START, "chatbot")
    graph.add_conditional_edges("chatbot", tools_condition)
    graph.add_edge("tools", "chatbot")
    graph.add_edge("chatbot", END)
    
    return graph.compile(checkpointer=checkpointer)

# Initialize app
if st.session_state.app is None:
    st.session_state.app = create_graph()

# Main UI
st.markdown("""
<div class="main-header">
    <h1>🌟 Therapist Built by Aryan</h1>
    <p>Your compassionate AI therapy companion</p>
</div>
""", unsafe_allow_html=True)

# Create columns for layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Conversation")
    
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div class="therapist-message">
                <strong>Therapist:</strong> Hey there — I'm really glad you made time to be here today. 
                No rush at all. Let's just take it easy. How has your day been going so far?
            </div>
            """, unsafe_allow_html=True)
        
        for msg in st.session_state.messages:
            if msg.startswith("User:"):
                st.markdown(f'<div class="user-message"><strong>{msg}</strong></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="therapist-message"><strong>{msg}</strong></div>', unsafe_allow_html=True)

with col2:
    st.subheader("🎙️ Input Options")
    
    # Voice input
    if st.button("🎤 Speak", key="voice_btn"):
        with st.spinner("Listening..."):
            user_input = recognize_speech()
            if not user_input.startswith("❌"):
                st.session_state.user_input = user_input
                st.rerun()
    
    # Text input
    user_text = st.text_area("💭 Or type your message:", 
                            value=st.session_state.get('user_input', ''),
                            height=100,
                            key="text_input")
    
    # Send button
    if st.button("📤 Send", key="send_btn"):
        if user_text.strip():
            st.session_state.user_input = user_text
            st.rerun()
    
    # Control buttons
    st.markdown("---")
    col_reset, col_clear = st.columns(2)
    
    with col_reset:
        if st.button("🔄 New Session"):
            st.session_state.messages = []
            st.session_state.conversation_history = []
            st.session_state.config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            st.session_state.user_input = ""
            st.rerun()
    
    with col_clear:
        if st.button("🧹 Clear Chat"):
            st.session_state.messages = []
            st.rerun()

# Process user input
if 'user_input' in st.session_state and st.session_state.user_input.strip():
    user_input = st.session_state.user_input.strip()
    
    # Add user message to display
    st.session_state.messages.append(f"User: {user_input}")
    st.session_state.conversation_history.append(f"User: {user_input}")
    
    # Process through graph
    current_state = {
        "messages": [{"role": "user", "content": user_input}],
        "conversation_history": st.session_state.conversation_history,
        "user_email": st.session_state.user_email,
        "session_ended": st.session_state.session_ended
    }
    
    try:
        with st.spinner("Therapist is thinking..."):
            result = st.session_state.app.invoke(current_state, config=st.session_state.config)
        
        # Extract AI response
        if result.get("messages"):
            last_ai_message = None
            for msg in reversed(result["messages"]):
                if isinstance(msg, AIMessage):
                    last_ai_message = msg.content
                    break
            
            if last_ai_message:
                # Add to display
                st.session_state.messages.append(f"Therapist: {last_ai_message}")
                st.session_state.conversation_history.append(f"Therapist: {last_ai_message}")
                
                # Text-to-speech in background
                if st.checkbox("🔊 Enable Voice Response", value=True):
                    threading.Thread(target=speak_text, args=(last_ai_message,), daemon=True).start()
    
    except Exception as e:
        st.error(f"Error: {e}")
        error_msg = "I apologize, but I encountered a technical issue. Let's continue our conversation."
        st.session_state.messages.append(f"Therapist: {error_msg}")
    
    # Clear input
    st.session_state.user_input = ""
    st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>🌟 Remember: You are stronger than you think 💙</p>
    <p><em>This is a supportive AI tool and not a replacement for professional therapy.</em></p>
</div>
""", unsafe_allow_html=True)