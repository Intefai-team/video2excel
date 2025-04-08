from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import openpyxl
import speech_recognition as sr
from gtts import gTTS
import playsound
import os
from difflib import get_close_matches

app = Flask(__name__)

# Twilio API Credentials (Get these from Twilio Console)
TWILIO_PHONE_NUMBER = "+12692934034"
MY_PHONE_NUMBER = "7747951011"

qa_dataset = {
    "What is IntefAI IT Solutions?": "IntefAI IT Solutions is an AI-driven IT solutions provider specializing in business transformation and technology training.",
    "What are the key offerings of IntefAI?": "Our key offerings include AI-driven CRM, ERP, HRM, SMS, AI-powered dashboards, custom AI software, AI in healthcare, blockchain integration, and IT consulting.",
    "How does IntefAI support businesses?": "We empower businesses with AI-driven solutions for streamlined operations, productivity enhancement, and intelligent decision-making.",
    "Where is IntefAI IT Solutions based?": "IntefAI IT Solutions is based in Indore, Madhya Pradesh, India.",
}

def get_best_match(user_input):
    matches = get_close_matches(user_input, qa_dataset.keys(), n=1, cutoff=0.6)
    return matches[0] if matches else None

def save_requirement(client_name, organization_type, purpose, referred_by, requirement):
    """Save client details into an Excel file."""
    excel_file = "client_requirements.xlsx"
    try:
        workbook = openpyxl.load_workbook(excel_file)
        sheet = workbook.active
    except FileNotFoundError:
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Client Name", "Organization Type", "Purpose", "Referred By", "Requirement"])
    
    sheet.append([client_name, organization_type, purpose, referred_by, requirement])
    workbook.save(excel_file)

@app.route("/voice", methods=["POST"])
def voice_assistant():
    """Handles incoming calls and responds with AI voice."""
    response = VoiceResponse()
    
    # Capture user input from call
    user_input = request.form.get("SpeechResult", "").lower()
    best_match = get_best_match(user_input)

    if best_match:
        bot_response = qa_dataset[best_match]
    else:
        bot_response = "I'm here to assist. Please provide your details for better assistance."

    response.say(bot_response, voice='alice')  # Respond in a natural voice

    # If additional information is needed, capture details
    if bot_response == "I'm here to assist. Please provide your details for better assistance.":
        response.say("Please say your name.", voice='alice')
        client_name = request.form.get("SpeechResult", "")

        response.say("Enter Organization Type: Business or Other.", voice='alice')
        organization_type = request.form.get("SpeechResult", "")

        response.say("What is the purpose?", voice='alice')
        purpose = request.form.get("SpeechResult", "")

        response.say("Referred By: Social Media or Other.", voice='alice')
        referred_by = request.form.get("SpeechResult", "")

        response.say("Please describe your requirement.", voice='alice')
        requirement = request.form.get("SpeechResult", "")

        save_requirement(client_name, organization_type, purpose, referred_by, requirement)
        response.say("Thank you! Your details have been saved.", voice='alice')

    return str(response)

if __name__ == "__main__":
    app.run(debug=True)
