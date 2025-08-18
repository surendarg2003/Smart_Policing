import cv2
import numpy as np
from ultralytics import YOLO
import os
from tkinter import Tk, Button, filedialog, Label
import datetime
import requests
from pathlib import Path

# Download specialized security model if not exists
def download_security_model():
    """Download a specialized security model"""
    model_path = "security_yolov8.pt"
    
    if not os.path.exists(model_path):
        print("Downloading specialized security model...")
        try:
            # This is a placeholder URL - you'll need to find or train your own model
            # For demonstration, we'll use a generic model
            url = "https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5s.pt"
            response = requests.get(url)
            with open(model_path, 'wb') as f:
                f.write(response.content)
            print(f"Model downloaded: {model_path}")
        except Exception as e:
            print(f"Failed to download model: {e}")
            return None
    
    return model_path

# Load specialized model (or fallback to standard model)
def load_weapon_detection_model():
    """Load a model specifically trained for weapon detection"""
    # First try to load specialized security model
    security_model_path = download_security_model()
    
    if security_model_path and os.path.exists(security_model_path):
        try:
            model = YOLO(security_model_path)
            print("Loaded specialized security model")
            return model
        except Exception as e:
            print(f"Error loading specialized model: {e}")
    
    # Fallback to standard YOLOv8 model
    print("Using standard YOLOv8 model (fallback)")
    return YOLO('yolov8n.pt')

# Define weapon-specific classes
weapon_classes = [
    "knife", "gun", "pistol", "rifle", "shotgun", "machine gun", 
    "blade", "sword", "axe", "hammer", "crowbar", "bomb", "grenade",
    "firearm", "weapon", "cutlery", "scissors", "baseball bat",
    "military rifle", "assault rifle", "handgun", "revolver"
]

# Custom class mapping for better weapon detection
class_mapping = {
    "knife": ["knife", "bladed weapon"],
    "gun": ["gun", "firearm", "weapon", "pistol", "rifle", "shotgun", "machine gun"],
    "pistol": ["pistol", "handgun", "revolver"],
    "rifle": ["rifle", "assault rifle", "military rifle"],
    "shotgun": ["shotgun", "scatter gun"],
    "machine gun": ["machine gun", "automatic weapon"],
    "blade": ["blade", "sharp object"],
    "sword": ["sword", "melee weapon"],
    "axe": ["axe", "hatchet"],
    "hammer": ["hammer", "crowbar", "wrench"],
    "bomb": ["bomb", "explosive", "grenade"],
    "grenade": ["grenade", "hand grenade"]
}

def detect_weapons(image_path, model):
    """Detect weapons in an image using specialized approach"""
    img = cv2.imread(image_path)
    if img is None:
        return "Error: Could not load image."

    height, width = img.shape[:2]
    output_img = img.copy()
    
    # Run inference
    results = model(img)
    
    suspicious_object_detected = False
    detected_weapons = []
    
    # Process results
    for result in results:
        boxes = result.boxes
        if boxes is not None:
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].cpu().numpy()
                
                # Get class name safely
                if hasattr(model, 'names') and cls < len(model.names):
                    class_name = model.names[cls].lower()
                else:
                    class_name = str(cls).lower()
                
                # Check if this matches any weapon category
                is_weapon = False
                weapon_type = None
                
                # Check against custom weapon classes
                for weapon, synonyms in class_mapping.items():
                    if any(synonym in class_name for synonym in synonyms):
                        is_weapon = True
                        weapon_type = weapon
                        break
                
                # Also check direct matches
                if not is_weapon and class_name in weapon_classes:
                    is_weapon = True
                    weapon_type = class_name
                
                # If still not identified, check for similar patterns
                if not is_weapon and any(word in class_name for word in ['gun', 'rifle', 'pistol', 'knife']):
                    is_weapon = True
                    weapon_type = "unknown_weapon"
                
                if is_weapon:
                    x1, y1, x2, y2 = map(int, xyxy)
                    
                    # Draw bounding box
                    color = (0, 0, 255)  # Red for weapons
                    cv2.rectangle(output_img, (x1, y1), (x2, y2), color, 3)
                    cv2.putText(output_img, f"{weapon_type}: {conf:.2f}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    
                    suspicious_object_detected = True
                    detected_weapons.append({
                        'type': weapon_type,
                        'confidence': conf,
                        'bbox': (x1, y1, x2, y2)
                    })
    
    # Add summary information
    cv2.rectangle(output_img, (10, 10), (width-10, 80), (255, 255, 255), -1)
    summary_text = "WEAPON DETECTION SUMMARY:"
    cv2.putText(output_img, summary_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    status_text = "SUSPICIOUS WEAPON DETECTED!" if suspicious_object_detected else "NO WEAPONS DETECTED"
    cv2.putText(output_img, status_text, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255) if suspicious_object_detected else (0, 255, 0), 2)
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(output_img, f"Processed at: {timestamp}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Save output
    output_image_path = "weapon_detection_output.jpg"
    cv2.imwrite(output_image_path, output_img)
    
    # Create detailed report
    report_path = "weapon_detection_report.txt"
    with open(report_path, "w") as f:
        f.write("=== WEAPON DETECTION REPORT ===\n")
        f.write(f"Image processed: {os.path.basename(image_path)}\n")
        f.write(f"Processing time: {timestamp}\n")
        f.write(f"Result: {status_text}\n\n")
        
        if detected_weapons:
            f.write("=== DETECTED WEAPONS ===\n")
            for i, weapon in enumerate(detected_weapons, 1):
                f.write(f"{i}. Type: {weapon['type']}\n")
                f.write(f"   Confidence: {weapon['confidence']:.2f}\n")
                f.write(f"   Bounding Box: ({weapon['bbox'][0]}, {weapon['bbox'][1]}) to ({weapon['bbox'][2]}, {weapon['bbox'][3]})\n\n")
    
    return status_text

def upload_and_process():
    """Main function to handle file upload and processing"""
    filetypes = [("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff")]
    image_path = filedialog.askopenfilename(title="Select an Image", filetypes=filetypes)

    if not image_path:
        status_label.config(text="No file selected.")
        return

    status_label.config(text="Processing...")
    root.update()  # Update UI to show processing text
    
    try:
        # Load the specialized model
        model = load_weapon_detection_model()
        
        # Detect weapons
        result = detect_weapons(image_path, model)
        status_label.config(text=result)
        print(f"Detection result: {result}")
        
        # Show the output image
        output_img = cv2.imread("weapon_detection_output.jpg")
        if output_img is not None:
            cv2.imshow('Weapon Detection Result', output_img)
            print("Press any key to close the image window...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            print("Image window closed.")
            
            # Show file locations
            print(f"\nOutput files created:")
            print(f"- Output image: weapon_detection_output.jpg")
            print(f"- Report: weapon_detection_report.txt")
            
    except Exception as e:
        status_label.config(text=f"Error: {str(e)}")
        print(f"Error: {str(e)}")

# Tkinter GUI
root = Tk()
root.title("Specialized Weapon Detection System")
root.geometry("400x200")

upload_button = Button(root, text="Import Image", command=upload_and_process, width=20, height=2)
upload_button.pack(pady=20)

status_label = Label(root, text="", wraplength=350)
status_label.pack(pady=10)

quit_button = Button(root, text="Quit", command=root.quit, width=20, height=2)
quit_button.pack(pady=20)

root.mainloop()