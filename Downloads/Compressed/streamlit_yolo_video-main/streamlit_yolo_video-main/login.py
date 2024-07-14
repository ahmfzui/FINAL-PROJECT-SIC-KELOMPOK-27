import streamlit as st
import numpy as np
import pandas as pd
from PIL import Image
import cv2
import os
from ultralytics import YOLO
import uuid
from streamlit_option_menu import option_menu


# Function to simulate sensor data
def simulate_sensor_data():
    # Simulating sensor data
    data = {
        'Sensor': ['Temperature', 'Humidity', 'Light Intensity', 'pH Level', 'CO2 Level'],
        'Value': [np.random.randint(20, 35), np.random.randint(40, 70), np.random.randint(100, 1000),
                  np.random.uniform(5.5, 7.5), np.random.randint(300, 1000)]
    }
    df = pd.DataFrame(data)
    return df

# Function to detect objects in an image
def detect_objects_in_image(model, uploaded_file, selected_objects, min_confidence):
    try:
        unique_id = str(uuid.uuid4().hex)[:8]
        input_path = os.path.join(os.getcwd(), f"temp_{unique_id}.jpg")

        with open(input_path, "wb") as temp_file:
            temp_file.write(uploaded_file.read())

        image = Image.open(input_path)
        frame = np.array(image)

        with st.spinner('Processing image...'):
            result = model(frame)
            detected_objects = 0
            for detection in result[0].boxes.data:
                x0, y0, x1, y1, conf, cls = detection
                object_name = model.names[int(cls)]
                if object_name in selected_objects and conf > min_confidence:
                    cv2.rectangle(frame, (int(x0), int(y0)), (int(x1), int(y1)), (255, 0, 0), 2)
                    cv2.putText(frame, f'{object_name} {conf:.2f}', (int(x0), int(y0 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    detected_objects += 1

            detections = result[0].verbose()
            cv2.putText(frame, detections, (10, 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        processed_image = Image.fromarray(frame)
        st.image(processed_image, caption='Processed Image', use_column_width=True)

        # Display the count of detected objects
        st.write(f'Total detected objects: {detected_objects}')

    except Exception as e:
        st.error(f"An error occurred: {e}")

    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

def detect_objects_in_video(model, uploaded_file, selected_objects, min_confidence):
    try:
        unique_id = str(uuid.uuid4().hex)[:8]
        input_path = os.path.join(os.getcwd(), f"temp_{unique_id}.mp4")
        output_path = os.path.join(os.getcwd(), f"output_{unique_id}.mp4")

        with open(input_path, "wb") as temp_file:
            temp_file.write(uploaded_file.read())

        video_stream = cv2.VideoCapture(input_path)
        width = int(video_stream.get(cv2.CAP_PROP_FRAME_WIDTH)) 
        height = int(video_stream.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'h264') 
        fps = int(video_stream.get(cv2.CAP_PROP_FPS)) 

        out_video = cv2.VideoWriter(output_path, int(fourcc), fps, (width, height)) 

        with st.spinner('Processing video...'): 
            while True:
                ret, frame = video_stream.read()
                if not ret:
                    break
                result = model(frame)
                for detection in result[0].boxes.data:
                    x0, y0 = (int(detection[0]), int(detection[1]))
                    x1, y1 = (int(detection[2]), int(detection[3]))
                    score = round(float(detection[4]), 2)
                    cls = int(detection[5])
                    object_name =  model.names[cls]
                    label = f'{object_name} {score}'

                    if model.names[cls] in selected_objects and score > min_confidence:
                        cv2.rectangle(frame, (x0, y0), (x1, y1), (255, 0, 0), 2)
                        cv2.putText(frame, label, (x0, y0 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    else:
                        continue
                
                detections = result[0].verbose()
                cv2.putText(frame, detections, (10, 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                #frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  
                out_video.write(frame) 
            video_stream.release()
            out_video.release()

            # Delete temporary files after processing
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                st.video(output_path)

    except Exception as e:
        st.error(f"An error occurred: {e}")

# Main function to create the application
def main():
    # Sidebar navigation using option_menu function
    with st.sidebar:
        menu_selection = option_menu(
            menu_title="Navigation Menu",
            options=["Home", "Monitoring", "Object Detection"],
            icons=["house", "clipboard-data-fill", "search"],
            menu_icon='cast',
            default_index=1,
            orientation="vertical"
        )

    if menu_selection == "Home":
        st.title("Hydroponic Tech House - IoT Dashboard")
        st.markdown("<hr/>", unsafe_allow_html=True)
        # Load your image
        image = Image.open('Hydroponic.jpg')
        # Display the image with a frame
        st.image(image, caption='Hydroponic', use_column_width=True, output_format='JPEG')
        st.markdown(
            """
            Welcome to Hydroponic Tech House, where you can manage and monitor your hydroponic system smartly!
            Use the sidebar navigation on the left to explore our features.
            """
        )

    elif menu_selection == "Monitoring":
        st.subheader("Monitoring")
        st.write("View real-time sensor data and environmental conditions of your hydroponic system.")

        # Simulate sensor data
        sensor_data = simulate_sensor_data()

        # Display sensor data
        st.markdown("### Current Sensor Readings:")
        st.dataframe(sensor_data, height=400)  # Adjust height to show full table

    elif menu_selection == "Object Detection":
        st.title("Object Detection")
        st.markdown("<hr/>", unsafe_allow_html=True) 
        st.write("Upload an image or video to detect objects using YOLOv8.")

        model = YOLO('yolov8n.pt')  # Change to yolov8n.pt if needed
        object_names = list(model.names.values())

        with st.form("object_detection_form"):
            uploaded_file = st.file_uploader("Upload image or video", type=['jpg', 'png', 'mp4'], label_visibility='collapsed')
            selected_objects = st.multiselect('Choose objects to detect', object_names, default=['person'])
            min_confidence = st.slider('Confidence score', 0.0, 1.0, 0.5)
            submit_button = st.form_submit_button(label='Submit')

        if uploaded_file is not None and submit_button:
            if uploaded_file.type.startswith('image'):
                detect_objects_in_image(model, uploaded_file, selected_objects, min_confidence)
            elif uploaded_file.type.startswith('video'):
                detect_objects_in_video(model, uploaded_file, selected_objects, min_confidence)

if __name__ == "__main__":
    main()