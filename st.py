import streamlit as st
import requests

# Define the URL of your FastAPI endpoint
fastapi_url = "http://fastapi:8080/search"

# Create a Streamlit app
st.title("BOBCAT (beta)")

# # Create a search bar
# user_input = st.text_input("Ask a question:", placeholder="Enter your query")
#
# # Process the user input and display the output
# if user_input:
#     # response = requests.post(fastapi_url, json={"query": user_input})
#     response = requests.get(fastapi_url)
#     if response.status_code == 200:
#         # print(response.json())
#         output = response.json()
#         st.write("Response:")
#         st.write(output)
#     else:
#         st.error("Error:", response.text)

# Create a form with a text input and a submit button
with st.form("search_form"):
    user_input = st.text_input("Ask a question:", placeholder="Enter your query...")
    submitted = st.form_submit_button("Search")


# Process the user input when the form is submitted
if submitted:
    response = requests.post(fastapi_url, json={"query": user_input})
    # response = requests.get(fastapi_url)
    if response.status_code == 200:
        # print(response.json())
        output = response.json()
        st.write("Response:\n")
        st.write(output)
    else:
        st.error("Error:", response.text)
