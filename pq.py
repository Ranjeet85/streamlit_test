import streamlit as st
from PIL import Image
import io
import boto3
import requests
import replicate
import os
from botocore.exceptions import NoCredentialsError

# AWS S3 Configuration - Get credentials from Streamlit secrets
BUCKET_NAME = "mytestbucket3publiq"
AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
REGION = "ap-south-1"
API_KEY = "API_KEY"

# Set Replicate API Token - Get from Streamlit secrets
os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]

# Function to upload the image and get the public URL
def upload_to_s3(file, file_name):
    try:
        image = Image.open(file)
        buffered = io.BytesIO()
        if image.format == "PNG":
            image.save(buffered, format="PNG")
            content_type = "image/png"
        elif image.format == "JPEG":
            image.save(buffered, format="JPEG")
            content_type = "image/jpeg"
        else:
            st.error("Unsupported image format. Only PNG and JPEG are allowed.")
            return None
        buffered.seek(0)
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=REGION,
        )
        s3.upload_fileobj(buffered, BUCKET_NAME, file_name, ExtraArgs={"ContentType": content_type})
        return f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{file_name}"
    except NoCredentialsError:
        st.error("AWS credentials not available.")
        return None
    except Exception as e:
        st.error(f"Error uploading file: {e}")
        return None

# Function to call Replicate API for lighting effect
def generate_lighting_effect(subject_image_url, prompt):
    try:
        output = replicate.run(
            "zsxkib/ic-light:d41bcb10d8c159868f4cfbd7c6a2ca01484f7d39e4613419d5952c61562f1ba7",
            input={
                "cfg": 1,
                "steps": 25,
                "width": 512,
                "height": 512,
                "prompt": prompt,
                "light_source": "None",
                "highres_scale": 1.5,
                "output_format": "jpg",
                "subject_image": subject_image_url,
                "lowres_denoise": 0.9,
                "output_quality": 80,
                "appended_prompt": "best quality",
                "highres_denoise": 0.5,
                "negative_prompt": "lowres, bad anatomy, bad hands, cropped, worst quality",
                "number_of_images": 1,
            },
        )
        return output
    except Exception as e:
        st.error(f"Error generating lighting effect: {e}")
        return None

# Function to send a try-on request
def send_run_request(model_image_url, garment_image_url, category, flat_lay):
    url = "https://api.fashn.ai/v1/run"
    headers = {
        "Authorization": f"Bearer {st.secrets['API_KEY']}",
        "Content-Type": "application/json",
    }
    data = {
        "model_image": model_image_url,
        "garment_image": garment_image_url,
        "category": category,
        "flat_lay": flat_lay,
    }
    response = requests.post(url, json=data, headers=headers)
    st.write("Response Status Code:", response.status_code)
    st.write("Response Body:", response.text)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 429:
        st.warning("Rate limit exceeded. Please wait and try again.")
        return None
    elif response.status_code == 404:
        st.error("API endpoint not found. Verify the URL.")
        return None
    else:
        st.error(f"Error while initiating prediction: {response.status_code}")
        return None

# Function to poll prediction status
def get_prediction_status(prediction_id):
    url = f"https://api.fashn.ai/v1/status/{prediction_id}"
    headers = {"Authorization": f"Bearer {st.secrets['API_KEY']}"}
    
    try:
        response = requests.get(url, headers=headers)
        st.write("Prediction Status Response Code:", response.status_code)
        st.write("Prediction Status Response Body:", response.text)

        if response.status_code == 200:
            try:
                status_response = response.json()
                st.write("Parsed Response (JSON):", status_response)
            except ValueError as e:
                st.error(f"Error parsing JSON response: {e}")
                return None
            
            if isinstance(status_response, dict):
                prediction_status = status_response.get("status")
                if prediction_status == "completed":
                    output_image_url = status_response.get("output", [None])[0]
                    if output_image_url:
                        st.success("Prediction completed!")
                        st.image(output_image_url, caption="Predicted Image", use_container_width=True)
                        return output_image_url
                    else:
                        st.error("Output image URL not found.")
                elif prediction_status == "failed":
                    st.error("Prediction failed!")
                elif prediction_status in ["in_queue", "processing"]:
                    st.write(f"Prediction status: {prediction_status}. Retrying...")
                else:
                    st.error(f"Unexpected status: {prediction_status}")
            else:
                st.error(f"Unexpected response type: {type(status_response)}")
                return None
        elif response.status_code == 404:
            st.error(f"Prediction ID not found. Please verify the prediction ID.")
            return None
        elif response.status_code == 401:
            st.error("Unauthorized request. Check your API key.")
            return None
        else:
            st.error(f"Unexpected error: {response.status_code}")
            return None

    except Exception as e:
        st.error(f"Error fetching prediction status: {e}")
    return None

# Streamlit UI
st.title("Product Styling with AI")

# Step 1: Select Product Category
category = st.selectbox(
    "Select Category",
    ["Select", "Food", "Jewelry", "Small and Indoor Items", "Furniture", "Apparel"]
)

# Step 2: Display relevant UI based on selected category
if category == "Apparel":
    # Apparel Section
    st.subheader("Apparel Styling")
    
    # Step 2.1: Garment image upload
    uploaded_garment_image = st.file_uploader("Upload Garment Image", type=["jpg", "jpeg", "png"])
    
    # Step 2.2: Model image selection
    st.subheader("Select Model Image")
    selected_model_url = st.radio(
        "Choose a model image:",
        options=MODEL_IMAGE_URLS,
        format_func=lambda url: f"Model Image ({MODEL_IMAGE_URLS.index(url) + 1})",
    )
    st.image(selected_model_url, caption="Selected Model Image", use_container_width=True)

    # Step 2.3: Category selection
    category = st.selectbox("Select Garment Category", ["tops", "bottoms", "one-pieces"])

    # Step 2.4: Flat-lay mode toggle
    flat_lay = st.checkbox("Enable Flat Lay Mode", value=False)

    # Step 2.5: Try-On Button
    if st.button("Request Try-On"):
        if uploaded_garment_image and selected_model_url and category:
            garment_image_url = upload_to_s3(uploaded_garment_image, "garment_image.jpg")
            if garment_image_url:
                response = send_run_request(selected_model_url, garment_image_url, category, flat_lay)
                if response:
                    prediction_id = response.get("id")
                    if prediction_id:
                        st.write("Prediction ID:", prediction_id)
                        progress_bar = st.progress(0)
                        retry_limit = 12
                        retries = 0
                        prediction_status = None
                        
                        while retries < retry_limit:
                            retries += 1
                            progress_bar.progress(retries / retry_limit)
                            status_response = get_prediction_status(prediction_id)
                            if status_response:
                                prediction_status = status_response.get("status")
                                if prediction_status == "completed":
                                    output_image_url = status_response["output"][0]
                                    st.success("Prediction completed!")
                                    st.image(output_image_url, caption="Predicted Image", uuse_container_width=True)
                                    break
                                elif prediction_status == "failed":
                                    st.error("Prediction failed!")
                                    break
                            else:
                                st.warning(f"Retrying... ({retries}/{retry_limit})")
                                time.sleep(5)
                        if retries >= retry_limit and prediction_status != "completed":
                            st.error("Prediction timed out. Please try again.")
        else:
            st.error("Please upload a garment image and select all options.")
            
elif category != "Select":
    # Product photoshoot section for other categories (excluding Apparel)
    st.subheader("Product Photoshoot with Lighting Effects")
    
    # Step 2.1: Image Upload
    uploaded_image = st.file_uploader("Upload Product Image", type=["jpg", "jpeg", "png"])

    # Lighting effects mapping
    prompt_map = {
        "Golden hour": "Golden hour lighting, soft warm glow, product photoshoot, high detail, 4k",
        "Moonlight": "Moonlight ambiance, cool silver tone, product photoshoot, high detail, 4k",
        "Candle Light": "Soft candlelight glow, warm and intimate lighting, product photoshoot, 4k",
        "Studio Light": "Bright studio lighting, clear shadows, product photoshoot, high detail, 4k",
        "Neon Light": "Vibrant neon lighting, colorful highlights, product photoshoot, high detail, 4k",
        "Backlight (Silhouette)": "Backlit product with glowing edges, soft shadows, product photoshoot, high detail, 4k",
        "Dusk Light": "Soft twilight lighting, moody ambiance, product photoshoot, high detail, 4k",
        "Sunset Light": "Warm sunset lighting, rich orange tones, product photoshoot, high detail, 4k",
        "Spotlight": "Focused spotlight on product, high contrast, product photoshoot, 4k",
        "Overhead Light": "Soft overhead lighting, minimal shadow, product photoshoot, high detail, 4k",
    }

    # Step 2.2: Lighting Effect Selection
    lighting_effect = st.selectbox("Select Lighting Effect", list(prompt_map.keys()))

    # Step 2.3: Lighting Effect Button
    if st.button("Generate Lighting Effect"):
        if uploaded_image:
            image_url = upload_to_s3(uploaded_image, "product_image.jpg")
            if image_url:
                prompt = prompt_map[lighting_effect]
                output = generate_lighting_effect(image_url, prompt)
                if output:
                    st.image(output, caption="Styled Image", use_container_width=True)

