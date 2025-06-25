# flake8: noqa
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.mongodb import MongoDBSaver
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
import asyncio
from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer
load_dotenv()

# Define state
class State(TypedDict):
    messages: Annotated[list, add_messages]
    conversation_history: list
    user_email: str | None
    session_ended: bool

# Initialize LLMs
llm = init_chat_model(model_provider="openai", model="gpt-4.1")
analyzer_llm = init_chat_model(model_provider="openai", model="gpt-4.1")

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_ADDRESS = os.getenv("EMAIL")
EMAIL_PASSWORD = os.getenv("APP_PASSWORD")

TAVILY = TavilySearch(max_results=2)

openai = AsyncOpenAI()

def speak_local(text: str):
    """
    Fallback text-to-speech using pyttsx3 (offline).
    """
    engine = pyttsx3.init()
    engine.setProperty('rate', 165)
    engine.setProperty('volume', 0.9)

    voices = engine.getProperty('voices')
    if voices:
        engine.setProperty('voice', voices[0].id)  # Choose different index if needed

    engine.say(text)
    engine.runAndWait()


async def speak_therapist_response(text: str):
    """
    Streams TTS playback of the therapist's response using OpenAI's streaming API.
    Falls back to offline TTS if OpenAI fails.
    """
    instructions = (
        "Speak with a calm, grounded, emotionally intelligent human tone — "
        "gentle, warm, patient, and deeply compassionate. Sound like an experienced therapist "
        "who genuinely cares, validating emotions without sounding robotic or clinical."
    )

    try:
        async with openai.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="nova",  # You can also try 'shimmer', 'coral', etc.
            input=text,
            instructions=instructions,
            response_format="pcm",
        ) as response:
            await LocalAudioPlayer().play(response)

    except Exception as e:
        print(f"🔁 OpenAI TTS failed: {e}")
        print("🎤 Falling back to local speech engine...")
        speak_local(text)

def recognize_from_mic():
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 2.5  # Auto stop after ~2.5 sec silence

    with sr.Microphone() as source:
        print("🎙️ Listening... (speak now, will auto-stop after pause)")
        audio = recognizer.listen(source)
    
    try:
        text = recognizer.recognize_google(audio)
        print("📝 You said:", text)
        return text
    except sr.UnknownValueError:
        return "❌ Could not understand audio"
    except sr.RequestError as e:
        return f"❌ API error: {e}"

@tool
def search_web(query: str) -> str:
    """Tool to perform web search for factual queries when therapy needs external information"""
    print("🌐 Performing search...")
    try:
        result = TAVILY.invoke(query)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Search failed: {str(e)}"

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import markdown2

@tool
def send_analysis_email(email: str, analysis: str) -> str:
    """Send therapy session analysis to user's email"""
    print(f"📧 Sending analysis to {email}...")

    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return "Email credentials not configured"

    try:
        # Convert Markdown to HTML properly
        html_body = markdown2.markdown(analysis)

        # Create message
        msg = MIMEMultipart("alternative")
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        msg['Subject'] = "🌟 Your Personal Therapy Session Report - Therapist Built by Aryan"

        # Attach both plain and HTML
        msg.attach(MIMEText(analysis, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        print("✅ Analysis sent successfully!")
        return "Analysis email sent successfully"

    except Exception as e:
        error_msg = f"Failed to send email: {e}"
        print(f"❌ {error_msg}")
        return error_msg


@tool
def validate_email(email: str) -> str:
    """Validate email format"""
    print("VALIDATING EMAIL")
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_valid = bool(re.match(email_pattern, email))
    return "Valid email format" if is_valid else "Invalid email format"

@tool
def detect_session_end(conversation: str) -> str:
    """Use LLM to detect whether a user wants to end the session, based on conversation context."""
    print("DETECTING SESSION END")
    prompt = f"""
You are a helpful assistant analyzing a therapy chat transcript. Determine if the conversation indicates the user is trying to end the session.

Only respond with:
- "Session should end" if the user is clearly concluding the conversation.
- "Session continues" if the user is still actively engaged or has not clearly indicated an end.

Conversation:
\"\"\"
{conversation.strip()}
\"\"\"
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    print("DETECTING SESSION END",response.content)
    return response.content.strip()

@tool
def analyze_therapy_session(conversation_history: str) -> str:
    """Generate comprehensive therapy session analysis"""
    analysis_prompt = f"""
    Create a personalized therapy session report for email delivery. Make it supportive and actionable.

    THERAPY SESSION CONVERSATION:
    {conversation_history}

    Generate a report with this structure:

    # 🌟 Your Personal Therapy Session Report
    *Generated by Therapist Built by Aryan*

    ## 📋 Session Summary
    Warm summary acknowledging the user's courage and progress during the session.

    ## 🎯 Key Insights
    Main themes and patterns that emerged, written personally using "you" language.

    ## 💪 Your Strengths & Progress
    Celebrate positive qualities and coping strategies demonstrated.

    ## 🛠️ Personalized Action Plan
    Provide 3-5 specific, actionable steps for this week:
    - Concrete and easy to implement
    - Tailored to their situation
    - Progressive and realistic

    ## 🧘‍♀️ Recommended Coping Strategies
    Suggest 2-3 evidence-based techniques with brief explanations.

    ## 📚 Helpful Resources
    Specific resources (books, apps, websites) aligned with their needs.

    ## 💌 Encouragement & Reminders
    Warm, encouraging message reinforcing their worth and potential.

    ---
    *This report supports your growth journey. You are the expert on your experience.*

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
    print("EXTRACT EMAIL CALLED")
    email_match =  re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    
    return email_match.group(0) if email_match else "No email found"

# Define tools list
tools = [search_web, send_analysis_email, validate_email, detect_session_end, analyze_therapy_session, extract_email_from_text]

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# Tool node
tool_node = ToolNode(tools)

def chatbot(state: State):
    """Main chatbot function"""
    # Get the last user message
    if not state["messages"]:
        return {"messages": []}
    
    # Create system prompt
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

    # Prepare messages for LLM
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add conversation history
    for msg in state["messages"]:
        if isinstance(msg, dict):
            messages.append(msg)
        else:
            # Handle other message types
            if hasattr(msg, 'content'):
                role = "user" if hasattr(msg, 'type') and msg.type == "human" else "assistant"
                messages.append({"role": role, "content": msg.content})
    
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def create_graph(checkpointer):
    """Create therapy chatbot graph"""
    graph = StateGraph(State)
    
    # Add nodes
    graph.add_node("chatbot", chatbot)
    graph.add_node("tools", tool_node)
    
    # Add edges
    graph.add_edge(START, "chatbot")
    
    # Add conditional edges
    graph.add_conditional_edges(
        "chatbot",
        tools_condition
    )
    
    graph.add_edge("tools", "chatbot")
    graph.add_edge("chatbot",END)
    
    return graph.compile(checkpointer=checkpointer)

# Main execution
if __name__ == "__main__":
    DB_URI = "mongodb://admin:admin@localhost:27017"
    
    print("🌟 Therapist Built by Aryan")
    print("Commands: /reset (new session), /quit (exit)")
    print("="*60)
    
    conversation_history = []
    
    with MongoDBSaver.from_conn_string(DB_URI) as checkpointer:
        app = create_graph(checkpointer)
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        
        # Initial greeting
        print("\nTherapist: Hey there — I'm really glad you made time to be here today. No rush at all. Let's just take it easy. How has your day been going so far?")
        
        while True:
            user_input = recognize_from_mic()
            
            if user_input.lower() == "/reset":
                config = {"configurable": {"thread_id": str(uuid.uuid4())}}
                conversation_history = []
                print("🔄 New session started.")
                print("Therapist: Hey there — I'm really glad you made time to be here today. How has your day been going so far?")
                continue
            
            if user_input.lower() in ["/quit", "/exit"]:
                print("Take care! Remember, you're stronger than you think. 💙")
                break
            
            # Add to conversation history
            conversation_history.append(f"User: {user_input}")
            
            # Prepare state
            current_state = {
                "messages": [{"role": "user", "content": user_input}],
                "conversation_history": conversation_history,
                "user_email": None,
                "session_ended": False
            }
            
            # Process through graph
            try:
                result = app.invoke(current_state, config=config)
               
                # Extract and print response
                if result.get("messages"):
                    last_ai_message = None
                    for msg in reversed(result["messages"]):
                        if isinstance(msg, AIMessage):
                            last_ai_message = msg.content
                            break

                    if last_ai_message:
                        print(f"\nTherapist: {last_ai_message}")
                        asyncio.run( speak_local(last_ai_message))
                    conversation_history.append(f"\nTherapist: {last_ai_message}")
                
            except Exception as e:
                print(f"Error: {e}")
                asyncio.run( speak_therapist_response("I apologize, but I encountered a technical issue. Let's continue our conversation."))
                print("Therapist: I apologize, but I encountered a technical issue. Let's continue our conversation.")