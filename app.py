import streamlit as st
import requests
import os
import urllib.parse

# 🔑 Replace with your actual SurveyMonkey API credentials
CLIENT_ID = "uKcTPUvLQ92OG_niuXgfkQ"
CLIENT_SECRET = "44702891992229546666261285313930943507"
REDIRECT_URI = "http://localhost:8501"

# 🔗 Generate OAuth URL with required scopes
SURVEYMONKEY_AUTH_URL = f"https://api.surveymonkey.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=surveys_read+responses_read"

st.title("📋 SurveyMonkey File Downloader")

# 🚀 Step 1: Auto-Logout if Token Expires
if "access_token" not in st.session_state:
    st.warning("🔑 You are not logged in. Please log in to continue.")
    
    if st.button("🔑 Login with SurveyMonkey"):
        st.markdown(f"[Click here to log in]({SURVEYMONKEY_AUTH_URL})", unsafe_allow_html=True)
else:
    # 🚀 Check if the token is still valid
    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
    response = requests.get("https://api.surveymonkey.com/v3/surveys", headers=headers)
    
    if "error" in response.json():
        st.warning("🔓 Your session has expired. Please log in again.")
        if os.path.exists("access_token.txt"):
            os.remove("access_token.txt")  # Remove old token
        st.session_state.clear()
        st.stop()

# ✅ Step 2: Handle Authentication & Extract OAuth Code
query_params = st.query_params  # Get query parameters
full_code = None

if "code" in query_params:
    raw_code = query_params["code"]
    if isinstance(raw_code, list):
        raw_code = raw_code[0]
    full_code = urllib.parse.unquote(raw_code)  # Decode any URL encoding

if full_code and "access_token" not in st.session_state:
    # Exchange code for access token
    token_url = "https://api.surveymonkey.com/oauth/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": full_code
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(token_url, data=data, headers=headers)
    api_response = response.json()

    access_token = api_response.get("access_token")

    if access_token:
        st.session_state["access_token"] = access_token
        st.success("✅ Successfully logged in! 🎉")
        with open("access_token.txt", "w") as token_file:
            token_file.write(access_token)
        st.query_params.clear()
        st.rerun()
    else:
        st.error(f"❌ Failed to authenticate. Error: {api_response.get('error_description', 'Unknown error')}")

# 🚀 Step 3: Fetch Available Surveys
def get_surveys(access_token):
    url = "https://api.surveymonkey.com/v3/surveys"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    return response.json()

if "access_token" in st.session_state:
    surveys = get_surveys(st.session_state["access_token"])
    survey_options = {s["title"]: s["id"] for s in surveys.get("data", [])}
    selected_survey = st.selectbox("📋 Select a Survey", list(survey_options.keys()))

# 🚀 Step 4: Fetch Survey Questions & File Upload Sections
def get_survey_questions(survey_id, access_token):
    url = f"https://api.surveymonkey.com/v3/surveys/{survey_id}/details"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    return response.json()

if "access_token" in st.session_state and selected_survey:
    survey_id = survey_options[selected_survey]
    questions = get_survey_questions(survey_id, st.session_state["access_token"])

    # 🚀 Extract file upload questions (always return an empty list if none found)
    file_questions = [
        q["headings"][0]["heading"]
        for page in questions.get("pages", [])
        for q in page.get("questions", [])
        if q.get("subtype") == "file_upload"
    ]

    # 🚀 Always Show the Dropdown (Even If No Files Found)
    selected_files = st.multiselect("📂 Select Files to Download", file_questions)

    # 🚀 Show a Warning If No File Uploads Exist
    if not file_questions:
        st.warning("⚠️ No file upload questions found in this survey. Please select a survey with file uploads.")

# 🚀 Step 5: Download Selected Files
def download_attached_files(survey_id, access_token, selected_files):
    url = f"https://api.surveymonkey.com/v3/surveys/{survey_id}/responses/bulk"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response_json = response.json()

    # 🚀 Debugging: Show the API response in case of issues
    st.write("🔍 API Response:", response_json)

    # ✅ Ensure "data" exists before accessing it
    if not isinstance(response_json, dict) or "data" not in response_json:
        st.error("❌ No survey responses found or API error occurred.")
        st.stop()  # Stop execution

    # ✅ Now we can safely loop through "data"
    for res in response_json["data"]:
        for question in res["pages"][0]["questions"]:
            if question["headings"][0]["heading"] in selected_files:
                for answer in question["answers"]:
                    if "file_url" in answer:
                        file_url = answer["file_url"]
                        file_name = file_url.split("/")[-1]

                        file_response = requests.get(file_url, headers=headers)
                        with open(file_name, "wb") as file:
                            file.write(file_response.content)

                        st.success(f"✅ File downloaded: {file_name}")

if st.button("📥 Download Selected Files"):
    download_attached_files(survey_id, st.session_state["access_token"], selected_files)

# 📌 Footer Branding
st.markdown("---")
st.markdown("🔹 **Developed by ATG** 🔹", unsafe_allow_html=True)

