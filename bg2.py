import streamlit as st
import requests
import time

st.title("SegMind Image Processing App")

api_key = "SG_412ba4d19dd13bbc"  # Store API key securely in Streamlit secrets
url = "https://api.segmind.com/workflows/674e866b0cbb977e665e86ec-v5"

image_url = st.text_input("Enter Image URL:", "Paste your image URL here")

if st.button("Process Image"):
    if not image_url:
        st.error("Please enter an image URL.")
    else:
        st.write("Processing...")
        with st.spinner("Processing..."):
            try:
                # Send the POST request to start image processing
                response = requests.post(url, json={"image_in": image_url}, headers={"x-api-key": api_key, "Content-Type": "application/json"})
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                data = response.json()
                
                poll_url = data["poll_url"]
                request_id = data["request_id"]

                st.write("Polling for result...")

                while True:
                    # Poll for the image processing status
                    poll_response = requests.get(poll_url, headers={"x-api-key": api_key})
                    poll_response.raise_for_status()  # Check if the GET request was successful
                    poll_data = poll_response.json()
                    
                    # Print full response for debugging
                    st.write(f"Full poll response: {poll_data}")
                    
                    status = poll_data.get("status", "UNKNOWN")
                    st.write(f"Status: {status}")
                    
                    if status == "COMPLETED":
                        # If the processing is complete, display the processed image
                        processed_image_url = poll_data.get("image_2cdjx")  # Check if this is the correct key
                        if processed_image_url:
                            st.image(processed_image_url)
                            st.success("Image processing complete!")
                            break
                    elif status == "FAILED":
                        # If the processing failed, show the error message
                        error_message = poll_data.get('error', 'Unknown error')
                        st.error(f"Image processing failed: {error_message}")
                        st.write(f"Full error response: {poll_data}")  # Print full error response for debugging
                        break
                    else:
                        # Handle unexpected status
                        st.warning(f"Unexpected status: {status}")
                        st.write(f"Full response data: {poll_data}")
                        time.sleep(5)  # Wait before polling again

            except requests.exceptions.RequestException as e:
                # Catch and display any request errors (e.g., network issues, invalid response)
                st.error(f"An error occurred: {e}")
            except KeyError as e:
                # Handle cases where the response data format is unexpected
                st.error(f"Unexpected response format: Missing key {e}")
