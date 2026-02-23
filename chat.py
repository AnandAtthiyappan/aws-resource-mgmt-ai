import streamlit as st
import requests

st.set_page_config(page_title="AWS Chatbot", layout="centered")
st.title("AI AWS Chatbot - Basic Infrastructrure Management")

# Initialize conversation state
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display message history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
user_input = st.chat_input("Say something...")

if user_input:
    # Add user's message to UI
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state["messages"].append({"role": "user", "content": user_input})

    # Get response from FastAPI
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    "http://localhost:8000/chat",
                    json={
                        "message": user_input,
                        "history": st.session_state["messages"]
                    }
                )

                print("AI RESPONSE : *****************")
                print(response.text)

                data = response.json()
                reply = data.get("response", "⚠️ No reply received.")
                st.session_state["messages"] = data.get("updated_history", st.session_state["messages"])
                st.markdown(reply)

            except Exception as e:
                error_msg = f"❌ Error communicating with backend: {e}"
                st.markdown(error_msg)
                st.session_state["messages"].append({"role": "assistant", "content": error_msg})
