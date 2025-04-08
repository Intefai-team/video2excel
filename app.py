# app.py
import streamlit as st
import os
import tempfile
import torch
import whisper
import subprocess
import re
import pandas as pd
from moviepy.video.io.VideoFileClip import VideoFileClip
from datetime import datetime

# Add caching for the Whisper model
@st.cache_resource
def load_whisper_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return whisper.load_model("base", device=device)

def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        st.error("ffmpeg is NOT installed or not working correctly.")
        return False

def extract_audio(video_path):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            audio_path = temp_audio.name
        
        clip = VideoFileClip(video_path)
        if clip.audio is None:
            return None, "No audio stream found in video"
        
        clip.audio.write_audiofile(audio_path, codec="pcm_s16le", fps=16000)
        clip.close()
        return audio_path, None
    except Exception as e:
        return None, str(e)

def transcribe_audio(audio_path, model):
    try:
        result = model.transcribe(audio_path, language="en", fp16=torch.cuda.is_available())
        return result["text"], None
    except Exception as e:
        return None, str(e)

def extract_info(text):
    data = {
        "name": None, 
        "location": None,
        "date_mentioned": None,
        "time_mentioned": None,
        "full_description": text,
        "processed_description": text
    }
    
    # Enhanced name extraction
    name_patterns = [
        r"(?:my\s+name\s+is|i\s+am|myself|this\s+is|i\'m|call\s+me|known\s+as)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"name\s+(?:is|\'s)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:here|speaking|reporting)",
        r"i\s+am\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if 1 <= len(name.split()) <= 3:  # Reasonable name length
                data["name"] = name
                data["processed_description"] = data["processed_description"].replace(match.group(0), "").strip()
                break
    
    # Enhanced location extraction
    location_patterns = [
        r"(?:from|live\s+in|located\s+in|based\s+in|resident\s+of|in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"(?:located|based)\s+at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"in\s+the\s+(?:city|town|village)\s+of\s+([A-Z][a-z]+)",
        r"currently\s+in\s+([A-Z][a-z]+)"
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            if 1 <= len(location.split()) <= 3:  # Reasonable location length
                data["location"] = location
                data["processed_description"] = data["processed_description"].replace(match.group(0), "").strip()
                break
    
    # Date extraction from text
    date_patterns = [
        r"(?:date|today|on)\s+(?:is\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:,\s+\d{4})?",
        r"\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}"
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["date_mentioned"] = match.group().strip()
            data["processed_description"] = data["processed_description"].replace(match.group(0), "").strip()
            break
    
    # Time extraction from text
    time_patterns = [
        r"\d{1,2}:\d{2}\s*(?:am|pm)?",
        r"(?:at|time)\s+(?:is\s+)?\d{1,2}\s*(?:am|pm|o\'clock)"
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["time_mentioned"] = match.group().strip()
            data["processed_description"] = data["processed_description"].replace(match.group(0), "").strip()
            break
    
    # Clean up processed description
    data["processed_description"] = re.sub(r'\s+', ' ', data["processed_description"]).strip()
    
    return data

def main():
    st.title("Enhanced Video Transcription App")
    
    # Load model once at startup
    model = load_whisper_model()
    
    uploaded_file = st.file_uploader("Upload a video file", type=["mp4", "mov", "avi", "mkv"])
    
    if uploaded_file is not None:
        if not check_ffmpeg():
            return
        
        # Get processing metadata
        current_datetime = datetime.now()
        processing_date = current_datetime.strftime("%Y-%m-%d")
        processing_time = current_datetime.strftime("%H:%M:%S")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
            temp_video.write(uploaded_file.getbuffer())
            video_path = temp_video.name
        
        try:
            with st.spinner("Extracting audio..."):
                audio_path, audio_error = extract_audio(video_path)
                if audio_error:
                    raise Exception(audio_error)
            
            with st.spinner("Transcribing audio..."):
                transcription, transcribe_error = transcribe_audio(audio_path, model)
                if transcribe_error:
                    raise Exception(transcribe_error)
            
            extracted_data = extract_info(transcription)
            
            # Create organized Excel report with clear sections
                        # Create organized Excel report with clear sections
                        # Create organized Excel report with clear sections
            video_duration = round(VideoFileClip(video_path).duration, 2)
            df = pd.DataFrame([{
                # Metadata Section
                "Processing Date": processing_date,
                "Processing Time": processing_time,
                "Video File Name": uploaded_file.name,
                "Video Duration (sec)": video_duration,
                
                # Extracted Information Section
                "Extracted Name": extracted_data.get("name", "Not found"),
                "Extracted Location": extracted_data.get("location", "Not found"),
                "Date Mentioned": extracted_data.get("date_mentioned", "Not found"),
                "Time Mentioned": extracted_data.get("time_mentioned", "Not found"),
                
                # Content Section
                "Full Transcription": extracted_data["full_description"],
                "Processed Description": extracted_data["processed_description"]
            }])
            
            excel_path = "structured_transcription_report.xlsx"
            
            # Use ExcelWriter to add formatting
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Transcript')
                
                # Access the workbook and worksheet for formatting
                workbook = writer.book
                worksheet = writer.sheets['Transcript']
                
                # Set column widths
                worksheet.column_dimensions['A'].width = 15
                worksheet.column_dimensions['B'].width = 15
                worksheet.column_dimensions['C'].width = 25
                worksheet.column_dimensions['D'].width = 15
                worksheet.column_dimensions['E'].width = 20
                worksheet.column_dimensions['F'].width = 20
                worksheet.column_dimensions['G'].width = 20
                worksheet.column_dimensions['H'].width = 20
                worksheet.column_dimensions['I'].width = 50
                worksheet.column_dimensions['J'].width = 50
                
                # Freeze the header row
                worksheet.freeze_panes = "A2"
            
            with open(excel_path, "rb") as f:
                st.download_button(
                    label="Download Structured Report",
                    data=f,
                    file_name=excel_path,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            # Display results in a structured way
            st.subheader("Extracted Information")
            cols = st.columns(4)
            with cols[0]:
                st.metric("Name Found", extracted_data.get("name", "Not found"))
            with cols[1]:
                st.metric("Location Found", extracted_data.get("location", "Not found"))
            with cols[2]:
                st.metric("Date Mentioned", extracted_data.get("date_mentioned", "Not found"))
            with cols[3]:
                st.metric("Time Mentioned", extracted_data.get("time_mentioned", "Not found"))
            
            st.subheader("Transcript Content")
            with st.expander("View Full Transcription"):
                st.write(extracted_data["full_description"])
            with st.expander("View Processed Description"):
                st.write(extracted_data["processed_description"])
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
        finally:
            # Clean up temporary files
            if os.path.exists(video_path):
                os.remove(video_path)
            if 'audio_path' in locals() and audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            if 'excel_path' in locals() and os.path.exists(excel_path):
                os.remove(excel_path)

if __name__ == "__main__":
    main()