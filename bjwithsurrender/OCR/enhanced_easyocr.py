import easyocr
import cv2
import numpy as np
from pathlib import Path
import os

# SETTINGS - MODIFY THESE
IMAGE_PATH = "../Screenshot/013.PNG"  # Change to your image path
SHOW_VISUALIZATION = True

# Regions to search - four regions total
REGIONS = [
    [(633, 588), (800, 588), (800, 680), (633, 680)],  # Region 1 - Upper "14" region
    [(633, 1415), (800, 1415), (800, 1515), (633, 1515)],  # Region 2 - Lower region
    [(370, 725), (740, 725), (740, 800), (370, 800)],  # Region 3 - New region
    [(370, 1550), (740, 1550), (740, 1650), (370, 1650)]  # Region 4 - New region
]

# OCR SETTINGS
# Number-only settings for regions 1 and 2
NUMBER_SETTINGS = {
    'allowlist': '0123456789',  # Only detect digits
    'text_threshold': 0.5,  # Lower threshold for better detection of small digits
    'low_text': 0.3,  # Lower threshold for text confidence
    'contrast_ths': 0.1,  # Check low contrast areas
    'adjust_contrast': 0.7  # Higher contrast adjustment for numbers
}

# General settings for regions 3 and 4
GENERAL_SETTINGS = {
    'text_threshold': 0.6,  # Standard text threshold
    'low_text': 0.4,  # Standard low text threshold
    'contrast_ths': 0.1,  # Standard contrast threshold
    'adjust_contrast': 0.5  # Standard contrast adjustment
}


def main():
    # Initialize EasyOCR with optimized settings for number detection
    # print("Initializing EasyOCR...")
    reader = easyocr.Reader(['en'], gpu=True)

    # Load the image
    # print(f"Processing {IMAGE_PATH}...")
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        print(f"Error: Could not read image {IMAGE_PATH}")
        return

    # Process each region
    all_detections = []
    region_texts = ["", "", "", ""]  # To store text from each region

    for i, region in enumerate(REGIONS):
        # print(f"Processing region {i + 1}")

        # Extract region coordinates
        x_min = min(p[0] for p in region)
        y_min = min(p[1] for p in region)
        x_max = max(p[0] for p in region)
        y_max = max(p[1] for p in region)

        # Crop the image to the region
        cropped = img[y_min:y_max, x_min:x_max]

        # Apply different settings based on region number
        if i < 2:  # Regions 1 and 2 (index 0 and 1) - use number settings
            # print(f"Using number-only settings for Region {i+1}")
            detections = reader.readtext(
                cropped,
                allowlist=NUMBER_SETTINGS['allowlist'],
                text_threshold=NUMBER_SETTINGS['text_threshold'],
                low_text=NUMBER_SETTINGS['low_text'],
                contrast_ths=NUMBER_SETTINGS['contrast_ths'],
                adjust_contrast=NUMBER_SETTINGS['adjust_contrast'],
                decoder='greedy'
            )
        else:  # Regions 3 and 4 (index 2 and 3) - use general settings
            # print(f"Using general settings for Region {i+1}")
            detections = reader.readtext(
                cropped,
                text_threshold=GENERAL_SETTINGS['text_threshold'],
                low_text=GENERAL_SETTINGS['low_text'],
                contrast_ths=GENERAL_SETTINGS['contrast_ths'],
                adjust_contrast=GENERAL_SETTINGS['adjust_contrast'],
                decoder='greedy'
            )

        # Process results
        for bbox, text, confidence in detections:
            # Adjust coordinates back to original image
            adjusted_bbox = [
                (int(bbox[0][0] + x_min), int(bbox[0][1] + y_min)),
                (int(bbox[1][0] + x_min), int(bbox[1][1] + y_min)),
                (int(bbox[2][0] + x_min), int(bbox[2][1] + y_min)),
                (int(bbox[3][0] + x_min), int(bbox[3][1] + y_min))
            ]

            # Collect text from this region
            region_texts[i] += text + " "

            # Add to all detections for visualization
            all_detections.append((text, confidence, adjusted_bbox))

    # Print only the text from each region
    # print("\nDetected Text by Region:")
    for i, text in enumerate(region_texts):
        print(f"Region {i + 1}: {text.strip()}")

    # Visualize results if enabled
    if SHOW_VISUALIZATION and all_detections:
        # Draw regions and detections
        for i, region in enumerate(REGIONS):
            region_np = np.array(region, dtype=np.int32)
            cv2.polylines(img, [region_np], True, (0, 0, 255), 2)

            # Label outside the region
            max_x = max(p[0] for p in region)
            min_y = min(p[1] for p in region)
            cv2.putText(img, f"Region {i + 1}", (max_x + 10, min_y + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

        # Draw detection boxes
        for text, confidence, bbox in all_detections:
            bbox_np = np.array(bbox).astype(int)
            cv2.polylines(img, [bbox_np], True, (0, 255, 0), 2)
            cv2.putText(img, f"{text} ({confidence:.2f})",
                        (bbox[0][0], bbox[0][1] - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 3)

        # Save and show the result
        Path('ocr_results').mkdir(exist_ok=True)
        output_path = f"ocr_results/annotated_{os.path.basename(IMAGE_PATH)}"
        cv2.imwrite(output_path, img)
        # print(f"Visualization saved to {output_path}")

        # Display in a window
        cv2.imshow("OCR Results", img)
        # print("Press any key to exit...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()