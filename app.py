import streamlit as st
import google.generativeai as genai
from PIL import Image
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import re
from bson.binary import Binary
import io
import datetime
import warnings
warnings.filterwarnings(action="ignore")

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

client = MongoClient(os.getenv('mdb'))

db = client['DB1']
collection = db['IDs']

# Function to retrieve the name of the logged-in user
def get_logged_in_user_name(username):
    user = collection.find_one({"username": username})
    if user:
        return user.get("name")
    return None

# Session management: Initialize session state
if 'username' not in st.session_state:
    st.session_state['username'] = None

def login():
    st.title("NutriFind")
    st.write("Check, Plan & Adapt your Diet with NutriFind!")
    st.write("Please login to continue.")
    
    with st.form(key="login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.form_submit_button("Login"):
            # Check if username and password match
            user = collection.find_one({"username": username, "password": password})
            if user:
                st.session_state.username = username
                st.session_state.user_info = user  # Store user info in session state
                st.success("Login successful!")
                st.experimental_set_query_params(page="app")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password.")

    st.markdown('<center>Dont have an account? <a href="?page=signup" target="_self">Sign Up!</a></center>', unsafe_allow_html=True)

def signup():
    def passwrd_valid(password):
        # Regular expression to check if the password meets the criteria
        regex = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,16}$"
        if re.match(regex, password):
            return True
        else:
            return False

    st.header('NutriFind Sign Up')

    with st.form(key="register_form"):
        name = st.text_input("Name", max_chars=50)
        username = st.text_input("Username", max_chars=16)
        password = st.text_input("Password", type="password", max_chars=16)
        confirm_password = st.text_input("Confirm Password", type="password")
        weight = st.number_input("Weight (kg)", min_value=1, max_value=300)
        height = st.number_input("Height (cm)", min_value=50, max_value=250)
        age = st.number_input("Age", min_value=1, max_value=120)
        
        if st.form_submit_button("Register"):
            # Check if all fields are filled
            if not name or not username or not password or not confirm_password or not weight or not height or not age:
                st.warning("Please fill in all fields")
                st.stop()

            if not name.replace(" ","").isalpha():
                st.warning("Name should contain only letters")
                st.stop()

            if not username.isalnum():
                st.warning("Username should be alphanumeric")
                st.stop()

            if not passwrd_valid(password):
                st.error("Password should contain upper, lower, numbers and symbols. Length 8 to 16.")
                st.stop()

            # Password confirmation
            if password != confirm_password:
                st.error("The passwords do not match")
                st.stop()

            # Check if username already exists
            existing_user = collection.find_one({"username": username})
            if existing_user:
                st.error("Username already exists. Please choose a different one.")
            else:
                # Insert new user into the database
                user_data = {
                    "name": name.title(),
                    "username": username,
                    "password": password,
                    "weight": weight,
                    "height": height,
                    "age": age
                }
                collection.insert_one(user_data)
                st.success("User registered successfully! Go back to Login")
                st.balloons()

    st.markdown('<a href="?page=login" target="_self">Back to Login</a>', unsafe_allow_html=True)

def profile():
    user = collection.find_one({"username": st.session_state.username})
    st.header("Profile")
    st.write(f"Name: {user.get('name')}")
    st.write(f"Username: {user.get('username')}")
    st.write(f"Weight: {user.get('weight')} kg")
    st.write(f"Height: {user.get('height')} cm")
    st.write(f"Age: {user.get('age')}")

    if st.button("Edit Profile"):
        st.experimental_set_query_params(page="edit_profile")

    if st.sidebar.button("Log out"):
        st.session_state.username = None
        st.experimental_rerun()

def edit_profile():
    user = collection.find_one({"username": st.session_state.username})
    st.header("Edit Profile")

    with st.form(key="edit_profile_form"):
        name = st.text_input("Name", value=user.get('name'), max_chars=50)
        password = st.text_input("Password", type="password", max_chars=16)
        weight = st.number_input("Weight (kg)", min_value=1, max_value=300, value=user.get('weight'))
        height = st.number_input("Height (cm)", min_value=50, max_value=250, value=user.get('height'))
        age = st.number_input("Age", min_value=1, max_value=120, value=user.get('age'))

        if st.form_submit_button("Save"):
            if not name.replace(" ","").isalpha():
                st.warning("Name should contain only letters")
                st.stop()

            user_update = {"name": name.title(), "weight": weight, "height": height, "age": age}
            if password:
                def passwrd_valid(password):
                    regex = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,16}$"
                    if re.match(regex, password):
                        return True
                    else:
                        return False

                if passwrd_valid(password):
                    user_update["password"] = password
                else:
                    st.error("Password should contain upper, lower, numbers and symbols. Length 8 to 16.")
                    st.stop()

            collection.update_one({"username": st.session_state.username}, {"$set": user_update})
            st.success("Profile updated successfully!")
            st.experimental_rerun()

    st.markdown('<a href="?page=app" target="_self">Back to Home</a>', unsafe_allow_html=True)

def app():
    def store_image_in_mongodb(image, response, protein, carbs, calories):
        # Convert image to binary format
        img_byte_array = io.BytesIO()
        image.save(img_byte_array, format='JPEG')  # Convert image to JPEG format for consistency
        img_binary_data = img_byte_array.getvalue()

        # Store image in MongoDB
        image_doc = {
            "image_data": Binary(img_byte_array),
            "image_format": "jpeg",  # Specify the format here, adjust as needed
            "response": response,
            "protein": protein,
            "carbs": carbs,
            "calories": calories
        }
        image_collection.insert_one(image_doc)
        st.write("Data stored successfully")
    def store_nutritional_data(protein, carbs, calories):
        track_collection = db['Track']
        track_data = {
            "username": st.session_state.username,
            "protein": protein,
            "carbs": carbs,
            "calories": calories,
            "timestamp": datetime.datetime.now()
        }
        track_collection.insert_one(track_data)
        st.write("Nutritional data stored successfully in Track collection")



    def get_gemini_resp(inpt_prompt, img):
        model = genai.GenerativeModel('gemini-pro-vision')
        resp = model.generate_content([inpt_prompt, img[0]])
        return resp.text

    def extract_nutritional_values(response):
        protein_pattern = re.compile(r"(\d+\.?\d*)\s*grams\s*protein", re.IGNORECASE)
        carbs_pattern = re.compile(r"Carbohydrates\s*\((\d+\.?\d*)g\)", re.IGNORECASE)
        calories_pattern = re.compile(r"(\d+)\s*calories", re.IGNORECASE)

        protein_matches = protein_pattern.findall(response)
        carbs_matches = carbs_pattern.findall(response)
        calories_matches = calories_pattern.findall(response)

        total_protein = sum(map(float, protein_matches))
        total_carbs = sum(map(float, carbs_matches))
        total_calories = sum(map(int, calories_matches))

        return total_protein, total_carbs, total_calories


    def inpt_img(uploaded_image):
        if uploaded_image is not None:
            image_parts = [
                {
                    "mime_type": uploaded_image.type,
                    "data": uploaded_image.getvalue()
                }
            ]
            return image_parts
        else:
            raise FileNotFoundError("No Image Uploaded.")
    
    st.title('Welcome to NutriFind')
    st.write("Please upload an image to get information about the food.")

    st.sidebar.subheader(f"Username: {st.session_state.username}")

    if st.sidebar.button("Profile"):
        st.experimental_set_query_params(page="profile")

    if st.sidebar.button("Log out"):
        st.session_state.username = None
        st.experimental_rerun()

    uploaded_image = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png", "webp"])
    
    if uploaded_image is not None:
        image = Image.open(uploaded_image)
        st.image(image, use_column_width=True)
        submit = st.button("Food Info")

        user_info = st.session_state.user_info
        weight = user_info['weight']
        height = user_info['height']
        age = user_info['age']
        input_msg = f"""
                    Based on the provided weight ({weight} kg), height ({height} cm), and age ({age}), you will act as an expert nutritionist and analyze the food items from the image. Your task is to:

1. Identify and list each food item in the image.
2. For each item, provide the following details in a tabular format:
   - Item name
   - Approximate serving size (in grams)
   - Calories per serving
   - Protein content per serving
   - Other notable nutrients (vitamins, minerals, etc.)

3. Provide an overall assessment of the nutritional value and healthiness of the meal.
4. Suggest potential modifications or substitutions to make the meal more balanced and nutritious, if applicable.
5. Estimate the amount of physical activity required to burn off the calories from the meal.
6. Offer any additional relevant advice or tips regarding digestion, portion control, or meal timing.

Please ensure that your analysis is comprehensive, accurate, and tailored to the provided personal details (weight, height, and age). If any crucial information is missing from the image, kindly request clarification or additional details from the user.                
        """
        
        if submit:
            img = inpt_img(uploaded_image)
            inpt_prompt = input_msg.format(weight=weight, height=height, age=age)
            response = get_gemini_resp(inpt_prompt, img)
            st.write(response)
            image_collection = db['images']
            #store_image_in_mongodb(image, response)

            #total_protein, total_carbs, total_calories = extract_nutritional_values(response)
            #if st.button("Store Nutritional Data"):
            #    store_nutritional_data(total_protein, total_carbs, total_calories)

def main():
    page = st.experimental_get_query_params().get("page", ["login"])[0]
    if not st.session_state.username:
        if page != "signup":
            page = "login"
    
    if page == "login":
        login()
    elif page == "signup":
        signup()
    elif page == "profile":
        profile()
    elif page == "edit_profile":
        edit_profile()
    else:
        app()

if __name__ == "__main__":
    main()
