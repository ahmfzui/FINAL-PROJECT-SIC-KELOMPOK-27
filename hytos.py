import streamlit as st
import cv2
import numpy as np
from ultralytics import YOLO
import urllib.request
from PIL import Image
from streamlit_option_menu import option_menu
from pymongo import MongoClient
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple
from datetime import datetime
import requests
import tensorflow as tf

# Set page configuration
st.set_page_config(page_title="HITOSH", page_icon=":seedling:", layout="wide")

# Koneksi ke MongoDB
client = MongoClient("mongodb+srv://regaarzula:YlDDs2OYHYOuuLPc@cluster0.nslprzn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['hydroponic_system']
collection = db['temperature_settings']
inputJam = db['clock_settings']

UBIDOTS_TOKEN = 'BBUS-xhl2VElj9gMEWA0aXyA9qnqkSd39Tp'
VARIABLE_ID_1 = '66a99dbade9a2d0ca44681c9'
VARIABLE_ID_2 = '66a21a1de770251891fa8abc'

# URL ESP32 CAM
url = 'http://192.168.1.8/cam-hi.jpg'
image_placeholder = st.empty()

# Kelas objek untuk model YOLO
classNames = ["Immature Sawi", "Mature Sawi", "Non-Sawi", "Partially Mature Sawi", "Rotten"]

def process_frame(frame, model, min_confidence):
    results = model(frame)
    detected_objects = []
    
    for detection in results[0].boxes.data:
        x0, y0 = (int(detection[0]), int(detection[1]))
        x1, y1 = (int(detection[2]), int(detection[3]))
        score = round(float(detection[4]), 2)
        cls = int(detection[5])
        object_name = classNames[cls]
        label = f'{object_name} {score}'

        if score > min_confidence:
            # Draw the bounding box
            cv2.rectangle(frame, (x0, y0), (x1, y1), (255, 0, 0), 2)

            # Compute text size
            label_size, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            label_width, label_height = label_size
            baseline = max(baseline, 1)  # Ensure baseline is at least 1

            # Define the rectangle background position
            label_x0 = x0
            label_y0 = y1 + 10
            label_x1 = x0 + label_width + 10
            label_y1 = label_y0 + label_height + baseline

            # Draw the filled rectangle as background for the label
            cv2.rectangle(frame, (label_x0, label_y0 - label_height - 10), (label_x1, label_y1), (0, 0, 255), -1)

            # Draw the label text
            cv2.putText(frame, label, (x0 + 5, y1 + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            detected_objects.append(label)  # Store detected objects

    return frame, detected_objects

def detect_maturity_in_image(model, uploaded_file, min_confidence):
    # Baca dan proses gambar
    image = Image.open(uploaded_file)
    image_np = np.array(image)
    image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    
    # Proses gambar untuk mendeteksi objek
    result_frame, detected_objects = process_frame(image_bgr, model, min_confidence)
    result_image = cv2.cvtColor(result_frame, cv2.COLOR_BGR2RGB)
    
    # Buat kolom untuk menampilkan hasil
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Tampilkan gambar yang diproses di kolom tengah
        st.image(result_image, caption='Processed Image', use_column_width=True)

        # Tampilkan label terakhir yang terdeteksi di kolom kanan
        if detected_objects:
            last_label = detected_objects[-1]
            st.success(f"This plant is classified as {last_label}.")
        else:
            st.warning("No objects detected.")

def detect_maturity_in_video(model, uploaded_file, min_confidence):
    video_file = uploaded_file.read()
    with open("temp_video.mp4", "wb") as f:
        f.write(video_file)
        
    cap = cv2.VideoCapture("temp_video.mp4")
    stframe = st.empty()
    last_detection = st.empty()  # Placeholder for last detected object

    last_detected_label = ""  # Initialize the variable to store the last detected label

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame, detected_objects = process_frame(frame, model, min_confidence)
        
        if isinstance(frame, np.ndarray):
            print("Frame type: ", type(frame))
            print("Frame shape: ", frame.shape)
            
            try:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                stframe.image(frame_rgb, channels="RGB", use_column_width=True)
            except cv2.error as e:
                print("OpenCV error: ", e)
        else:
            print("Frame is not a valid numpy array")
        
        # Update last detected object status
        if detected_objects:
            last_detected_label = detected_objects[-1]  # Update with new detection
        last_detection.text(f"Last detected object: {last_detected_label}")  # Display last detected label

    cap.release()
    st.write("Video processing completed.")

# Load your trained model
modelpest = tf.keras.models.load_model('DetectionPestPlant.h5')

# Define the classes based on your training
classes = ["pest detected", "no pest detected"]# Replace with your actual class names

def preprocess_imagepest(image):
    img = Image.open(image).convert("RGB")
    img = img.resize((128, 128))
    img = np.array(img) / 255.0
    img = np.expand_dims(img, axis=0)
    return img

def detect_pest_in_image(modelpest, uploaded_filepest, min_confidence_pest):
    # Preprocess the image
    image = preprocess_imagepest(uploaded_filepest)
    
    # Perform the prediction
    predictions = modelpest.predict(image)
    confidence = np.max(predictions)
    label_index = np.argmax(predictions)
    
    # Display the uploaded image in the center column
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        uploaded_image = Image.open(uploaded_filepest)
        st.image(uploaded_image, caption='Uploaded Image', use_column_width=True)
        # Determine status based on confidence
        if confidence >= min_confidence_pest:
            status = classes[label_index]
            if status == "pest detected":
                st.warning(f"This plant has {status} ⚠")
                st.write("Your plant is not healthy.")
                st.write("Steps to take:")
                st.write("1. Immediately isolate the affected plant from the others.")
                st.write("2. Inspect all plants in the hydroponic system to ensure the pest has not spread.")
                st.write("3. Clean the area around the plants, removing any plant debris or organic material where pests might thrive.")
                st.write("4. Use appropriate organic pesticides or manually control the pest.")
                st.write("5. Monitor the plants regularly to ensure the pest is completely eradicated.")
            else:
                st.success(f"This plant has {status} 👍")
                st.write("Your plant is healthy. Keep up the good work!")



def main():
    # Sidebar navigation menggunakan option_menu
    menu_selection = option_menu(
        menu_title=None,
        options=["Home", "Monitoring", "Controlling", "Maturity Detection","Pest Detection"],
        icons=["house-fill", "clipboard-data-fill", "gear-wide-connected", "search", "bug-fill"],
        default_index=0,
        orientation="horizontal",
    )

    if menu_selection == "Home":
        st.markdown("<hr/>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([0.2, 0.7, 0.2])

        # Muat gambar
        image = Image.open('Image/title.png')
        # Tampilkan gambar
        col2.image(image, use_column_width=True)
        st.markdown("<hr/>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style='display: flex; justify-content: center; margin-top: 20px; margin-bottom: 20px;'>
                <p style='text-align: center; max-width: 1200px;'>
                Welcome to Hydroponic Tech House, where you can manage and monitor your hydroponic system smartly!
                Use the Topbar navigation on the left to explore our features.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns([0.2, 0.4, 0.2])
        # Muat gambar
        image_hidro = Image.open('Image/Hydroponic.jpg')
        # Tampilkan gambar
        col2.image(image_hidro, use_column_width=True)

        st.markdown(
            """
            <div style='display: flex; flex-direction: column; align-items: flex-start; margin-top: 20px; margin-bottom: 20px;'>
                <p style='text-align: left;'>
                The Hydroponic Tech House project aims to develop a hydroponic farming system using Internet of Things (IoT) technology 
                with computer vision AI that can monitor and manage plant conditions and optimize crop yields. 
                This project will collect data from sensor readings such as temperature, humidity, air quality, water pH, 
                and a camera that can detect plant types and classify plant age using AI algorithms. 
                This system is web-based and in it farmers can also set the appropriate temperature to optimize crop yields. 
                We hope that this project can improve the quality of agriculture in Indonesia.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <h2 style='text-align: center;'>Our Technology Advantages</h2>
            <div style='display: flex; justify-content: space-around; flex-wrap: wrap;'>
                <div style='flex: 1; margin: 10px; padding: 20px; border: 1px solid #ccc; border-radius: 10px; text-align: center; background-color: #f9f9f9;'>
                    <h3 style='color: black; text-align: center;'>Real-Time Monitoring</h3>
                    <p style='color: black;'>Monitoring plant conditions (temperature, humidity, air quality, water pH, TDS, and water temperature) in real-time with sensors integrated into our website.</p>
                </div>
                <div style='flex: 1; margin: 10px; padding: 20px; border: 1px solid #ccc; border-radius: 10px; text-align: center; background-color: #f9f9f9;'>
                    <h3 style='color: black; text-align: center;'>Computer Vision</h3>
                    <p style='color: black;'>Classifying plant age and pest detection through image analysis. This advanced detection helps in monitoring the growth stages and health of your plants, ensuring optimal care and timely intervention.</p>
                </div>
                <div style='flex: 1; margin: 10px; padding: 20px; border: 1px solid #ccc; border-radius: 10px; text-align: center; background-color: #f9f9f9;'>
                    <h3 style='color: black; text-align: center;'>Controlling</h3>
                    <p style='color: black;'>Allow users to manage and adjust their hydroponic environment conditions in real-time. Users can control fans and heating lamps based on temperature sensor readings to maintain ideal climate conditions, and also manage nutrition as needed.</p>
                </div>
                <div style='flex: 1; margin: 10px; padding: 20px; border: 1px solid #ccc; border-radius: 10px; text-align: center; background-color: #f9f9f9;'>
                    <h3 style='color: black; text-align: center;'>Website Interface</h3>
                    <p style='color: black;'>Providing users with the ability to monitor and control plant conditions from anywhere and at any time. The user-friendly interface ensures that even those new to hydroponics can easily manage their system with confidence.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <h2 style='text-align: center;'>Tips for Hydroponic Care</h2>
            <div style='display: flex; justify-content: space-between; overflow-x: scroll;'>
                <div style='flex: 0 0 40%; margin: 10px; padding: 40px; border: 1px solid #ccc; border-radius: 10px; text-align: center; background-color: white;'>
                    <p style='color: black; font-size: 16px;'>
                    <strong>1. Maintain Water Temperature:</strong> Ensure that the water in your hydroponic system is clean and properly balanced. Regularly check the pH and nutrient levels to provide the best environment for your plants.
                    </p>
                </div>
                <div style='flex: 0 0 40%; margin: 10px; padding: 40px; border: 1px solid #ccc; border-radius: 10px; text-align: center; background-color: white;'>
                    <p style='color: black; font-size: 16px;'>
                    <strong>2. Monitor Light Exposure:</strong> Plants in a hydroponic system need sufficient light. Make sure they receive the right amount of light by using artificial lighting or placing them near natural light sources.
                    </p>
                </div>
                <div style='flex: 0 0 40%; margin: 10px; padding: 40px; border: 1px solid #ccc; border-radius: 10px; text-align: center; background-color: white;'>
                    <p style='color: black; font-size: 16px;'>
                    <strong>3. Control Temperature:</strong> Keep the temperature in your hydroponic environment within the optimal range for the specific plants you are growing. Use fans or heaters as needed to maintain ideal conditions.
                    </p>
                </div>
                <div style='flex: 0 0 40%; margin: 10px; padding: 40px; border: 1px solid #ccc; border-radius: 10px; text-align: center; background-color: white;'>
                    <p style='color: black; font-size: 16px;'>
                    <strong>4. Prune Regularly:</strong> Regularly prune your plants to promote healthy growth and prevent overcrowding. This helps in ensuring that each plant receives adequate nutrients and light.
                    </p>
                </div>
                <div style='flex: 0 0 40%; margin: 10px; padding: 40px; border: 1px solid #ccc; border-radius: 10px; text-align: center; background-color: white;'>
                    <p style='color: black; font-size: 16px;'>
                    <strong>5. Prevent Pests and Diseases:</strong> Even in a controlled environment, hydroponic plants can be susceptible to pests and diseases. Inspect your plants regularly and take action at the first sign of any issues.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("Blog_Form"):

            st.markdown("""
            <style>
            .stButton { display: flex; justify-content: center; }
            h3.custom-title { font-size: 24px; } /* Mengubah ukuran font title */
            </style>
            """, unsafe_allow_html=True)

            def blog_post_with_image(title, img_path, description, link):
                st.markdown(f"<h3 style='text-align: center;'>{title}</h3>", unsafe_allow_html=True)
                st.image(img_path, caption=title, use_column_width=True)
                st.markdown(f"<p style='text-align: center;'>{description}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align: center;'><a href='{link}' target='_blank'>Read More</a></p>", unsafe_allow_html=True)

            blog_data = [
                {
                    "title": "5 Tips for Caring for Hydroponic Plants",
                    "img_path": "Image/tips.jpg",
                    "description": "A Practical Guide to Maintaining Health and Optimal Growth for Your Hydroponic Plants, including how to manage nutrients, water, light, and system cleanliness.",
                    "link": "https://pustaka.setjen.pertanian.go.id/index-berita/5-tips-merawat-tanaman-hidroponik"
                },
                {
                    "title": "Hydroponic Nutrient Requirements",
                    "img_path": "Image/Nutrisi.jpg",
                    "description": "Discover the Secrets Behind Healthy Hydroponic Plant Growth! This article reviews the essential requirements for hydroponic nutrients.",
                    "link": "https://gokomodo.com/blog/inilah-syarat-nutrisi-hidroponik-dan-jenisnya"
                },
                {
                    "title": "7 Common Mistakes Beginners",
                    "img_path": "Image/blogkesalahan.jpg",
                    "description": "Discussing Common Mistakes Made by Beginners in Hydroponic Gardening",
                    "link": "https://hidroponikpedia.com/kesalahan-pemula-hidroponik/"
                },
                # Postingan tambahan
                {
                    "title": "4 Hydroponic Technologies in Japan",
                    "img_path": "Image/jepangHidroponik.jpg",
                    "description": "Discover the Latest Innovations in Hydroponics Transforming Farming in Japan! This article explores four advanced technologies being implemented in Japan.",
                    "link": "https://dlh.semarangkota.go.id/4-teknologi-hidroponik-di-jepang/"
                },
                {
                    "title": "Maximizing Hydroponic Lighting",
                    "img_path": "Image/tambahan.jpg",
                    "description": "Uncover the Secrets Behind Healthy Hydroponic Plant Growth! This article explores the essential requirements for hydroponic nutrition.",
                    "link": "https://www.kompasiana.com/madeyogi1918/60a34c648ede485a65284762/pencahayaan-tanaman-hidroponik-dalam-ruangan-guna-memaksimalkan-produktivitas-tanaman"
                },
                {
                    "title": "4 Tips for Maximizing Hydroponics",
                    "img_path": "Image/4tips.jpg",
                    "description": "Want a More Bountiful Hydroponic Harvest? Discover 4 Practical Tips to Optimize Hydroponic Plant Growth",
                    "link": "https://kebunpintar.id/blog/ketahui-4-tips-dalam-memaksimalkan-bercocok-tanam-metode-hidroponik/"
                }
            ]

            # Status untuk menentukan apakah lebih banyak postingan telah ditampilkan
            if 'more_posts' not in st.session_state:
                st.session_state.more_posts = False

            # Menampilkan blog dalam layout 3 kolom
            st.markdown("<h2 style='text-align: center;'>Latest Information on Hydroponics</h2>", unsafe_allow_html=True)
            st.markdown("<hr/>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)

            for i in range(3):
                with [col1, col2, col3][i]:
                    blog_post_with_image(**blog_data[i])

            # Mengatur tampilan tombol berdasarkan status more_posts
            if not st.session_state.more_posts:
                if st.form_submit_button("See More Posts"):
                    st.session_state.more_posts = True
            else:
                col4, col5, col6 = st.columns(3)
                for i in range(3, len(blog_data)):
                    with [col4, col5, col6][i - 3]:
                        blog_post_with_image(**blog_data[i])

                if st.form_submit_button("See Fewer Posts"):
                    st.session_state.more_posts = False

        st.markdown("---", unsafe_allow_html=True)

        st.markdown("<h2 style='text-align: center;'>FAQ - Hydroponic System Features</h2>", unsafe_allow_html=True)

        st.markdown("### Frequently Asked Questions")
        
        with st.expander("What does the Monitoring feature do, and how do I use it?"):
            st.write("""
            The **Monitoring** feature allows you to view real-time sensor data related to your hydroponic system's environment, such as temperature, humidity, air quality, water pH, Total dissolved solids, and Water Temperature. Here's how to use it:
            
            1. **Navigate to the Monitoring Section:** Select 'Monitoring' from the top navigation bar.
            2. **Choose a Monitoring Mode:**
            - **Numerical Sensor Monitoring:** Displays current values of various sensors in a numerical format.
            - **Graphical Sensor Monitoring:** Displays sensor data in graph form, showing trends over time.
            3. **Interpret the Data:**
            - Use the displayed data to assess the current conditions of your hydroponic system.
            - Make adjustments in the 'Controlling' section if needed to optimize conditions.
            """)
        
        with st.expander("How do I use the Temperature Control in the Controlling feature?"):
            st.write("""
            The **Temperature Control** feature allows you to manage the climate conditions within your hydroponic environment. To use this feature:
            1. **Navigate to the Controlling Section:** Select 'Controlling' from the top navigation bar.
            2. **Adjust the Temperature Settings:**
            - **Set Minimum and Maximum Temperature:**
                - **Minimum Temperature:** Use the first input field to set the minimum desired temperature.
                - **Maximum Temperature:** Use the second input field to set the maximum desired temperature.
            - **Activate Control:** Click the 'Save Temperature Settings' button to send these temperature settings to the system.
            3. **Automatic Control:**
            - **Fan Activation:** If the hydroponic system's temperature exceeds the maximum temperature, the fan will automatically turn on.
            - **Heater Activation:** If the hydroponic system's temperature drops below the minimum temperature, the heater will automatically turn on.
            4. **Monitor Changes:** Observe the effects in the 'Monitoring' section to ensure the system is maintaining the desired temperature range.
            """)

        with st.expander("How do I control the Nutrition Pump using the Controlling feature?"):
            st.write("""
            The **Nutrition Pump Control** feature allows you to manage the nutrient supply to your plants. Follow these steps:

            1. **Navigate to the Nutrition Pump Control Section:** Select 'Nutrition Pump Control' from the top navigation bar.

            2. **Set Pump Schedules:**
            - **Schedule 1:** Enter the time for the first feeding cycle (HH:MM).
            - **Schedule 2:** Enter the time for the second feeding cycle (HH:MM).
            - **Schedule 3:** Enter the time for the third feeding cycle (HH:MM).

            3. **Save the Schedule:** Click 'Save Pump Schedule' to apply the settings.

            4. **Monitor Pump Status:** Check the latest schedule settings in the 'Monitoring' section to ensure the pump is running according to the set times.
            """)
            
        with st.expander("How does the Maturity Detection feature work, and how do I use it?"):
            st.write("""
            The **Maturity Detection** feature uses computer vision to determine the growth stage of your plants. To use this feature:
            
            1. **Navigate to the Maturity Detection Section:** Select 'Maturity Detection' from the top navigation bar.
            2. **Choose a Detection Method:**
            - **Upload an Image or Video:**
                - **Image:** Upload a recent image of your plant.
                - **Video:** Upload a short video clip of your plants.
                - The system will analyze the visual data to detect plant maturity levels. Results will be displayed with labels indicating the detected maturity stage.
            - **Real-Time Detection with ESP32 Cam:**
                - The ESP32 Cam will continuously monitor and detect objects in real-time.
                - The system will display real-time maturity status based on the captured images.
            3. **Interpret Results:** Use the information to decide on actions such as harvesting or continued growth.
            """)
            
        with st.expander("How can I detect pests using the Pest Detection feature?"):
            st.write("""
            The **Pest Detection** feature allows you to identify pests on your plants using a trained AI model. To use this feature:
            
            1. **Navigate to the Pest Detection Section:** Select 'Pest Detection' from the top navigation bar.
            2. **Upload an Image:** Upload an image of your plant where you suspect pest presence.
            3. **Run the Detection:**
            - The AI model will analyze the image to detect any pests.
            - If pests are detected, the system will provide a warning.
            """)

    elif menu_selection == "Monitoring":
        # Center buttons
        st.markdown("""
            <style>
            .stButton { display: flex; justify-content: center; }
            </style>
            """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown("<h1 style='text-align: center;'>Monitoring</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center;'>View real-time sensor data and environmental conditions of your hydroponic system.</p>", unsafe_allow_html=True)
            st.markdown("<hr/>", unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["📊 **Numerical Sensor Monitoring**", "📈 **Graphical Sensor Monitoring**"])

            with tab1:
                # Create a form for Ubidots widgets
                with st.form("number_monitoring_form"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.subheader("🌡 Temperature")
                        widget_url1 = "https://stem.ubidots.com/app/dashboards/public/widget/n2DJ6zraCJkvxZYYAQ5egHCTgZLe6E3XBpVtLGnZsoQ"
                        st.components.v1.iframe(widget_url1, width=300, height=300, scrolling=True)

                        st.subheader("🌫️ Humidity")
                        widget_url2 = "https://stem.ubidots.com/app/dashboards/public/widget/XXSQaCPoG41tQ1W33PDj9xphZOO7DwF6tvflxiKnSkE"
                        st.components.v1.iframe(widget_url2, width=300, height=300, scrolling=True)

                    with col2:
                        st.subheader("🌬️ Air Quality")
                        widget_url3 = "https://stem.ubidots.com/app/dashboards/public/widget/r2vxbd2k48WLkhuDvjDSzZSkCzM2tTlyOOIXEjmlv70"
                        st.components.v1.iframe(widget_url3, width=300, height=300, scrolling=True)

                        st.subheader("🥤 pH Water")
                        widget_url8 = "https://stem.ubidots.com/app/dashboards/public/widget/ST57XPDVjOhWeqD1GHC1ejT2zCuxr078rU-tQH6WNKo"
                        st.components.v1.iframe(widget_url8, width=300, height=300, scrolling=True)
                        
                    with col3:
                        st.subheader("💧 TDS")
                        widget_url9 = "https://stem.ubidots.com/app/dashboards/public/widget/86h0bUdTlNWpqva7sev_1SOcxUcYMfkz8Xs-t5FtxzQ"
                        st.components.v1.iframe(widget_url9, width=300, height=300, scrolling=True)

                        st.subheader("🌊 Water Temperature")
                        widget_url9 = "https://stem.ubidots.com/app/dashboards/public/widget/YoIsf8xtepa3TtaBycMyeRjBorBDkjQRqEsNDF557KA"
                        st.components.v1.iframe(widget_url9, width=300, height=300, scrolling=True)
                    
                    # Add form submit button
                    st.write("")
                    submit_button = st.form_submit_button('Refresh Widget')

            with tab2:
                # Create a form for Ubidots widgets
                with st.form("graph_monitoring_form"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.subheader("📈 Temperature Graph")
                        widget_url4 = "https://stem.ubidots.com/app/dashboards/public/widget/PqQHvhWiU-ujHMqL9M8Bt0qXY4joNCYBsGyndRPZFmc"
                        st.components.v1.iframe(widget_url4, width=300, height=300, scrolling=True)
                        
                        st.subheader("📈 Humidity Graph")
                        widget_url5 = "https://stem.ubidots.com/app/dashboards/public/widget/5PK_qDpcR9PPX3VCjadctqXCBaADtD4VZXyiWiIDoAg"
                        st.components.v1.iframe(widget_url5, width=300, height=300, scrolling=True)

                    with col2:
                        st.subheader("📈 Air Quality Graph")
                        widget_url6 = "https://stem.ubidots.com/app/dashboards/public/widget/8I7B3uLzVmyMPljXs4Z-2o6pMOw0LkhqlWKSCzjPU6U"
                        st.components.v1.iframe(widget_url6, width=300, height=300, scrolling=True)

                        st.subheader("📈 pH Water Graph")
                        widget_url7 = "https://stem.ubidots.com/app/dashboards/public/widget/vcMLNX_AVuiKGRo8ZnQylqcy6k7YIaQLJcREMUc-0pI"
                        st.components.v1.iframe(widget_url7, width=300, height=300, scrolling=True)
                        
                    with col3:
                        st.subheader("📈 TDS Sensor Graph")
                        widget_url9 = "https://stem.ubidots.com/app/dashboards/public/widget/Zq58WYEeQEctENnxZMm__sbAp7mZad2FG05WboPlVeQ"
                        st.components.v1.iframe(widget_url9, width=300, height=300, scrolling=True)

                        st.subheader("📈 Water Temperature Sensor Graph")
                        widget_url9 = "https://stem.ubidots.com/app/dashboards/public/widget/1r7zP43MactxVUEIg832hXiw-xlQnu7V1t0qdfgP1dc"
                        st.components.v1.iframe(widget_url9, width=300, height=300, scrolling=True)
                    
                    # Add form submit button
                    st.write("")
                    submit_button = st.form_submit_button('Refresh Widget')

    elif menu_selection == "Controlling":
        st.markdown("<h1 style='text-align: center;'>Controlling</h1>", unsafe_allow_html=True)
        st.markdown("""
            <p style='text-align: center;'>
                Optimize your hydroponic tech house with advanced automation. 
                Control fans and heating lamps based on temperature sensor readings to maintain ideal climate conditions. 
                Additionally, manage the nutrition pump to efficiently distribute nutrients to your plants at the right intervals, ensuring optimal growth and preventing over- or under-fertilization. 
                Achieve precision and flexibility in your hydroponic system with our automated controls.
            </p>
        """, unsafe_allow_html=True)
        st.markdown("<hr/>", unsafe_allow_html=True)

        # Create tabs for controlling temperature and water motor
        tab1, tab2 = st.tabs(["🌡 **Temperature Control**", "💦 **Nutrition Motor Control**"])

        # Center buttons
        st.markdown("""
            <style>
            .stButton { display: flex; justify-content: center; }
            </style>
            """, unsafe_allow_html=True)

        # Temperature Control tab
        with tab1:
            st.write("")
            st.markdown("<h3 style='text-align: center;'>🌡 Set Minimum and Maximum Temperature</h3>", unsafe_allow_html=True)
            st.write("")

            with st.form(key='temperature_form'):
                min_temp = st.number_input('Minimum Temperature (°C)', value=20.0, step=0.1)
                max_temp = st.number_input('Maximum Temperature (°C)', value=30.0, step=0.1)
                submit_button = st.form_submit_button(label='Save Temperature Settings')

            if submit_button:
                collection.insert_one({'min_temp': min_temp, 'max_temp': max_temp})
                st.success('Temperature settings have been saved!')

            latest_setting = collection.find().sort([('_id', -1)]).limit(1)
            for setting in latest_setting:
                st.markdown(
                    f"""
                    <div style='display: flex; justify-content: center; margin: 20px 0;'>
                        <div style='padding: 20px; border: 1px solid #ccc; border-radius: 10px; background-color: #00502D; color: white; max-width: 600px; text-align: center;'>
                            <p><b>Latest Minimum Temperature:</b> {setting['min_temp']}</p>
                            <p><b>Latest Maximum Temperature:</b> {setting['max_temp']}</p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


        # Water Motor Control tab
        with tab2:
            st.write("")
            st.markdown("<h3 style='text-align: center;'>💦 Set Nutrition Motor Timing</h3>", unsafe_allow_html=True)
            st.write("")

            def validate_time(time_str):
                """Validate and convert the time string format."""
                try:
                    # Attempt to parse the string into a datetime.time object
                    return datetime.strptime(time_str, '%H:%M').time()
                except ValueError:
                    # Return None if the format is incorrect
                    return None

            with st.form(key='motor_form'):
                # Text input for pump schedule time
                alarm_time_str_1 = st.text_input('Water Pump Schedule 1 (HH : MM)', value=datetime.now().strftime('%H:%M'))
                alarm_time_str_2 = st.text_input('Water Pump Schedule 2 (HH : MM)', value=datetime.now().strftime('%H:%M'))
                alarm_time_str_3 = st.text_input('Water Pump Schedule 3 (HH : MM)', value=datetime.now().strftime('%H:%M'))
                # Submit button
                submit_button = st.form_submit_button(label='Save Pump Schedule')

                if submit_button:
                    # Validate the time format
                    alarm_time_1 = validate_time(alarm_time_str_1)
                    alarm_time_2 = validate_time(alarm_time_str_2)
                    alarm_time_3 = validate_time(alarm_time_str_3)

                    if alarm_time_1 and alarm_time_2 and alarm_time_3:
                        # Insert the schedules into the database
                        inputJam.insert_one({
                            'alarm_time_1': alarm_time_str_1,
                            'alarm_time_2': alarm_time_str_2,
                            'alarm_time_3': alarm_time_str_3
                        })

                        st.success('Water pump schedule has been saved!')
                    else:
                        st.error('Invalid time format. Please use HH:MM.')

            latest_jam_setting = inputJam.find().sort([('_id', -1)]).limit(1)
            for setting in latest_jam_setting:
                st.markdown(
                    f"""
                    <div style='display: flex; justify-content: center; margin: 20px 0;'>
                        <div style='padding: 20px; border: 1px solid #ccc; border-radius: 10px; background-color: #00502D; color: white; max-width: 600px; text-align: center;'>
                            <p><b>Latest Pump Schedule 1 :</b> {setting.get('alarm_time_1')}</p>
                            <p><b>Latest Pump Schedule 2 :</b> {setting.get('alarm_time_2')}</p>
                            <p><b>Latest Pump Schedule 3 :</b> {setting.get('alarm_time_3')}</p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


    elif menu_selection == "Maturity Detection":
        image_placeholder = st.empty()
        st.markdown("<h1 style='text-align: center;'>Maturity Detection</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Leverage advanced object detection to identify and classify different Sawi varieties. You can either upload images or videos for analysis or stream live video from an ESP32 CAM for real-time detection. Choose the method that best suits your needs for monitoring and analyzing your hydroponic system. </p>", unsafe_allow_html=True)
        st.markdown("<hr/>", unsafe_allow_html=True) 

        modelmature = YOLO('trained_pakcoy.pt')


        # Create tabs
        tab1, tab2, = st.tabs(["📷 **Upload Image and Video**", "📡 **Real-time Object Detection**"])

        with tab1:
            st.write("")
            st.markdown("<h3 style='text-align: center;'>📷 Upload Image and Video</h3>", unsafe_allow_html=True)
            st.write("")

            with st.form("maturity_detection_form"):
                st.write("Upload an image or video to detect objects4")
                uploaded_file = st.file_uploader("Upload image or video", type=['jpg', 'png', 'mp4'], label_visibility='collapsed')
                min_confidence = st.slider('Confidence Score', 0.0, 1.0, 0.2)
                submit_button = st.form_submit_button(label='Submit')

            if uploaded_file is not None and submit_button:
                if uploaded_file.type.startswith('image'):
                    detect_maturity_in_image(modelmature, uploaded_file, min_confidence)
                elif uploaded_file.type.startswith('video'):
                    detect_maturity_in_video(modelmature, uploaded_file, min_confidence)

        with tab2:
            st.write("")
            st.markdown("<h3 style='text-align: center;'>📡 Real-time Object Detection from ESP32 CAM</h3>", unsafe_allow_html=True)
            st.write("")

            # Create a form for webcam controls
            with st.form("webcam_form"):
                min_confidence = st.slider('Confidence Score', 0.0, 1.0, 0.2)
                submit_button_start = st.form_submit_button('Start Video Stream')
                submit_button_stop = st.form_submit_button('Stop Video Stream')

            # Center buttons
            st.markdown("""
                <style>
                .stButton { display: flex; justify-content: center; }
                </style>
                """, unsafe_allow_html=True)
            
            # Manage webcam stream control
            if submit_button_start:
                placeholder = st.empty()
                last_detection = st.empty()
                last_detected_label = ""  # Initialize the variable with a default value
                # Jalankan deteksi objek secara real-time
                while True:
                    img_resp = urllib.request.urlopen(url)
                    imgnp = np.array(bytearray(img_resp.read()), dtype=np.uint8)
                    frame = cv2.imdecode(imgnp, -1)
                    
                    if isinstance(frame, np.ndarray):
                        print("Frame type: ", type(frame))
                        print("Frame shape: ", frame.shape)
                        
                        result_frame, detected_objects = process_frame(frame, modelmature, min_confidence)
                        frame_rgb = cv2.cvtColor(result_frame, cv2.COLOR_BGR2RGB)
                        
                        try:
                            # Create two columns
                            col1, col2 = st.columns([2, 1])  # Adjust the width ratio as needed
                            
                            with col1:
                                # Display the image in the first column
                                placeholder.image(frame_rgb, channels="RGB", use_column_width=False, width=700)
                                
                            with col2:
                                # Display the detected object label in the second column
                                if detected_objects:
                                    last_detected_label = detected_objects[-1]  # Update with the latest detection
                                    last_detection.text(f"Last detected object: {last_detected_label}")  # Display the last detected label
                                else:
                                    last_detection.text("No objects detected.")
                        except cv2.error as e:
                            print("OpenCV error: ", e)
                    else:
                        print("Frame is not a valid numpy array")

            if submit_button_stop:
                st.write("Video stream stopped.")
    
    elif menu_selection == "Pest Detection":
        st.markdown("<h1 style='text-align: center;'>Pest Detection</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Use advanced image classification to detect pests affecting your Bok-Choy crops. Simply upload an image to analyze and determine if pests are present. Our model will process the image and provide results, helping you manage your hydroponic system effectively.</p>", unsafe_allow_html=True)
        st.markdown("<hr/>", unsafe_allow_html=True) 

        with st.form("pest_detection_form"):
            st.write("Upload an image to detect pests in your plant")
            uploaded_file_pest = st.file_uploader("Upload image", type=['jpg', 'png'], label_visibility='collapsed')
            min_confidence_pest = st.slider('Confidence Score', 0.0, 1.0, 0.2)
            submit_button_pest = st.form_submit_button(label='Submit')
            st.markdown("""
            <style>
            .stButton { display: flex; justify-content: center; }
            </style>
            """, unsafe_allow_html=True)
        
        if uploaded_file_pest is not None and submit_button_pest:
            if uploaded_file_pest.type.startswith('image'):
                detect_pest_in_image(modelpest, uploaded_file_pest, min_confidence_pest)
    

# Jalankan aplikasi Streamlit
if __name__ == '__main__':
    main()
