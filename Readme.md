# 🌟 Therapist Built by Aryan

A compassionate AI-powered therapy companion built with Streamlit, LangChain, and OpenAI. This application provides a safe space for mental health support through conversational AI, complete with voice interaction, session analysis, and personalized email reports.

## ✨ Features

### 🗣️ Interactive Communication
- **Text Chat**: Type your thoughts and feelings in a comfortable chat interface
- **Voice Input**: Speak naturally using speech recognition technology
- **Voice Responses**: Hear the therapist's responses with text-to-speech capability

### 🧠 Advanced AI Capabilities
- **Empathetic Conversations**: Built on GPT-4o-mini with specialized therapy prompts
- **Session Analysis**: Automatic analysis of therapy sessions using AI
- **Web Search Integration**: Access to current mental health resources via Tavily Search
- **Email Reports**: Personalized session summaries sent directly to your email

### 🎨 User Experience
- **Modern UI**: Clean, responsive design with gradient themes
- **Real-time Processing**: Instant responses with thinking indicators
- **Session Management**: Start new sessions or clear chat history
- **Privacy Focused**: Secure handling of sensitive conversations

## 🚀 Quick Start

### Prerequisites

```bash
Python 3.8+
OpenAI API key
Email credentials (Gmail recommended)
Tavily Search API key (optional)
```

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Aryan-juneja/AI-Therapist
cd therapist-ai
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
Create a `.env` file in the root directory:
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Email Configuration
EMAIL=your_email@gmail.com
APP_PASSWORD=your_gmail_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Tavily Search (Optional)
TAVILY_API_KEY=your_tavily_api_key_here
```

4. **Run the application**
```bash
streamlit run app.py
```

## 📋 Dependencies

```txt
streamlit
langchain
python-dotenv
langgraph
langchain-tavily
langchain-core
pyttsx3
SpeechRecognition
openai
markdown2
```

### System Dependencies
- **Windows**: May require additional setup for speech recognition
- **macOS**: Built-in speech recognition support
- **Linux**: May need `python3-pyaudio` for microphone access

## 🔧 Configuration

### Email Setup (Gmail)
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. Use this app password in your `.env` file

### API Keys
- **OpenAI**: Required for AI conversations and analysis
- **Tavily**: Optional for web search functionality

## 🎯 Usage Guide

### Starting a Session
1. Launch the application with `streamlit run app.py`
2. The therapist will greet you with a warm, welcoming message
3. Choose your preferred input method:
   - 🎤 **Voice**: Click "Speak" and talk naturally
   - 💭 **Text**: Type in the text area and click "Send"

### During the Session
- Share your thoughts, feelings, and concerns openly
- The AI therapist will respond with empathy and understanding
- Enable voice responses for a more natural conversation experience
- The system automatically detects when you're ready to end the session

### Ending a Session
- When you indicate you're ready to finish (saying goodbye, feeling better, etc.)
- The therapist will offer to send a personalized session analysis
- Provide your email address to receive a comprehensive report
- The report includes insights, action plans, and recommended resources

### Session Management
- 🔄 **New Session**: Start fresh with a new conversation thread
- 🧹 **Clear Chat**: Remove messages from current display (keeps session context)

## 🏗️ Architecture

### Core Components

#### State Management
```python
class State(TypedDict):
    messages: Annotated[list, add_messages]
    conversation_history: list
    user_email: str | None
    session_ended: bool
```

#### LangGraph Workflow
- **Chatbot Node**: Main conversation handler with therapy-specific prompts
- **Tools Node**: Handles function calls for email, analysis, and search
- **Conditional Edges**: Routes between conversation and tool usage

#### Available Tools
- `search_web`: Access current mental health resources
- `detect_session_end`: Identify when user wants to conclude
- `analyze_therapy_session`: Generate comprehensive session analysis
- `send_analysis_email`: Deliver personalized reports via email
- `validate_email`: Ensure email format correctness
- `extract_email_from_text`: Parse email addresses from user input

## 🛡️ Privacy & Security

### Data Handling
- **No Persistent Storage**: Conversations are not saved to disk
- **Session-Based**: Data exists only during active sessions
- **Secure Email**: Uses encrypted SMTP connections
- **API Security**: All API keys stored in environment variables

### Limitations
- This is a supportive AI tool, not a replacement for professional therapy
- For crisis situations, please contact emergency services or mental health professionals
- The AI cannot provide medical diagnoses or prescriptions

## 🎨 Customization

### Styling
The app uses custom CSS for styling. Key classes:
- `.main-header`: Application header with gradient background
- `.chat-container`: Scrollable chat area
- `.user-message`: User message styling (right-aligned, blue theme)
- `.therapist-message`: AI response styling (left-aligned, purple theme)

### Therapy Prompts
The system prompt can be customized in the `chatbot` function to adjust:
- Conversation style and tone
- Therapeutic approach
- Response patterns
- Tool usage guidelines

## 🔍 Troubleshooting

### Common Issues

#### Speech Recognition Not Working
```bash
# Install system dependencies
sudo apt-get install python3-pyaudio  # Linux
brew install portaudio  # macOS
```

#### Email Not Sending
- Verify Gmail app password is correct
- Check that 2FA is enabled on Gmail account
- Ensure SMTP settings match your email provider

#### API Errors
- Confirm OpenAI API key has sufficient credits
- Check API key permissions and rate limits
- Verify Tavily API key if using web search

#### Memory Issues
- The app uses in-memory storage only
- Large conversation histories may impact performance
- Use "New Session" to reset if needed

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Install development dependencies
4. Make your changes
5. Test thoroughly
6. Submit a pull request

### Code Standards
- Follow PEP 8 for Python code style
- Use type hints where appropriate
- Add docstrings for new functions
- Test all features before submitting

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **OpenAI**: For providing the GPT-4o-mini model
- **LangChain**: For the powerful AI application framework
- **Streamlit**: For the intuitive web application framework
- **Tavily**: For web search capabilities
- **Contributors**: Thanks to all who help improve this tool

## 📞 Support

For support, questions, or feedback:
- Create an issue on GitHub
- Check the troubleshooting section above
- Review the documentation for API integrations

---

**Remember**: This application is designed to provide support and companionship. For serious mental health concerns, please consult with licensed mental health professionals.

🌟 **"You are stronger than you think"** 💙