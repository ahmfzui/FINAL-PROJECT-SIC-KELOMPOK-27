import os
from huggingface_hub import InferenceClient
import streamlit as st

# Ensure your Hugging Face API token is securely set
os.environ["HUGGINGFACEHUB_API_TOKEN"] = "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"

st.title("Tanya Gizi!")

# Initialize chat history if not already present
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    st.chat_message(message['role']).markdown(message['content'])

# Input area for the user
prompt = st.chat_input('Masukan pertanyaanmu di sini!')

# Process user input
if prompt:
    st.chat_message('user').markdown(prompt)
    st.session_state.messages.append({'role': 'user', 'content': prompt})

    # Generate a response using InferenceClient
    client = InferenceClient(
        model="mistralai/Mistral-Large-Instruct-2407",
        token=os.getenv("HUGGINGFACEHUB_API_TOKEN")
    )

    # Generating response
    response = client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        stream=False  # Disable streaming as it's not supported
    )

    response_text = response['choices'][0]['message']['content']

    # Display and store the assistant's response
    st.chat_message('assistant').markdown(response_text)
    st.session_state.messages.append({'role': 'assistant', 'content': response_text})
