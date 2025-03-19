import easyocr
import cv2
import numpy as np
from pathlib import Path
import os

# SETTINGS - MODIFY THESE
IMAGE_PATH = "Screenshot/007.png"  # Change to your image path
SHOW_VISUALIZATION = True

# Regions to search - upper and lower "14" regions
REGIONS = [
    [(633, 588), (721, 588), (721, 680), (633, 680)],  # Upper region
    [(633, 1415), (721, 1415), (721, 1503), (633, 1503)]  # Lower region
]


def main():
    # Initialize EasyOCR
    print("Initializing EasyOCR...")
    reader = easyocr.Reader(['en'])

    # Load the image
    print(f"Processing {IMAGE_PATH}...")
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        print(f"Error: Could not read image {IMAGE_PATH}")
        return

    # Process each region
    all_detections = []
    for i, region in enumerate(REGIONS):
        # print(f"Processing region {i + 1}")

        # Extract region coordinates
        x_min = min(p[0] for p in region)
        y_min = min(p[1] for p in region)
        x_max = max(p[0] for p in region)
        y_max = max(p[1] for p in region)

        # Crop the image to the region
        cropped = img[y_min:y_max, x_min:x_max]

        # Perform OCR on the region
        detections = reader.readtext(cropped)

        # Process results
        for bbox, text, confidence in detections:
            # Adjust coordinates back to original image
            adjusted_bbox = [
                (int(bbox[0][0] + x_min), int(bbox[0][1] + y_min)),
                (int(bbox[1][0] + x_min), int(bbox[1][1] + y_min)),
                (int(bbox[2][0] + x_min), int(bbox[2][1] + y_min)),
                (int(bbox[3][0] + x_min), int(bbox[3][1] + y_min))
            ]

            # Print result
            print(f"Text: {text}")
            print(f"Confidence: {confidence:.2f}")
            # print(f"Coordinates: {' '.join([f'({pt[0]},{pt[1]})' for pt in adjusted_bbox])}")

            all_detections.append((text, confidence, adjusted_bbox))

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
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Draw detection boxes
        for text, confidence, bbox in all_detections:
            bbox_np = np.array(bbox).astype(int)
            cv2.polylines(img, [bbox_np], True, (0, 255, 0), 2)
            cv2.putText(img, f"{text} ({confidence:.2f})",
                        (bbox[0][0], bbox[0][1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Save and show the result
        Path('ocr_results').mkdir(exist_ok=True)
        output_path = f"ocr_results/annotated_{os.path.basename(IMAGE_PATH)}"
        cv2.imwrite(output_path, img)
        print(f"Visualization saved to {output_path}")

        # Display in a window
        cv2.imshow("OCR Results", img)
        print("Press any key to exit...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()