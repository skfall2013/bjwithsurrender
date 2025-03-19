import easyocr
import argparse
import os
import json
from pathlib import Path
import cv2
import numpy as np


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract text from images using EasyOCR')
    parser.add_argument('--input', '-i', required=True, help='Input image path or directory')
    parser.add_argument('--languages', '-l', nargs='+', default=['en'], help='Languages to detect (e.g., en ch_sim)')
    parser.add_argument('--output', '-o', help='Output file path (if not specified, prints to console)')
    parser.add_argument('--min-confidence', '-c', type=float, default=0.0, help='Minimum confidence threshold (0-1)')
    parser.add_argument('--format', '-f', choices=['text', 'json', 'csv'], default='text', help='Output format')
    parser.add_argument('--visualize', '-v', action='store_true', help='Visualize results on image')
    args = parser.parse_args()

    # Initialize the reader with specified languages
    print(f"Initializing EasyOCR with languages: {args.languages}")
    reader = easyocr.Reader(args.languages)

    # Process single image or directory
    results = {}
    if os.path.isdir(args.input):
        # Process all images in directory
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        for file in os.listdir(args.input):
            file_path = os.path.join(args.input, file)
            if os.path.isfile(file_path) and os.path.splitext(file_path)[1].lower() in image_extensions:
                process_image(reader, file_path, results, args)
    else:
        # Process single image
        process_image(reader, args.input, results, args)

    # Output results based on format
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            if args.format == 'json':
                json.dump(results, f, ensure_ascii=False, indent=2)
            elif args.format == 'csv':
                f.write('file,text,confidence,bounding_box\n')
                for img_path, detections in results.items():
                    for text, confidence, bbox in detections:
                        f.write(f'"{img_path}","{text}",{confidence},{bbox}\n')
            else:  # text format
                for img_path, detections in results.items():
                    f.write(f"File: {img_path}\n")
                    for text, confidence, _ in detections:
                        f.write(f"- {text} (Confidence: {confidence:.2f})\n")
                    f.write("\n")
        print(f"Results saved to {args.output}")
    else:
        # Print to console
        for img_path, detections in results.items():
            print(f"\nFile: {img_path}")
            for text, confidence, _ in detections:
                print(f"- {text} (Confidence: {confidence:.2f})")


def process_image(reader, img_path, results, args):
    print(f"Processing {img_path}...")
    try:
        # Read text from image with details (includes confidence scores)
        detections = reader.readtext(img_path)

        # Filter by confidence threshold
        filtered_results = []
        for detection in detections:
            bbox, text, confidence = detection
            if confidence >= args.min_confidence:
                filtered_results.append((text, confidence, bbox))

        # Add to results dictionary
        results[img_path] = filtered_results

        # Visualize if requested
        if args.visualize and filtered_results:
            visualize_results(img_path, filtered_results)

    except Exception as e:
        print(f"Error processing {img_path}: {e}")


def visualize_results(img_path, detections):
    # Load image
    img = cv2.imread(img_path)

    # Draw bounding boxes and text
    for text, confidence, bbox in detections:
        # Convert bbox to integer coordinates
        bbox = np.array(bbox).astype(int)

        # Draw bounding box
        cv2.polylines(img, [bbox], True, (0, 255, 0), 2)

        # Add text with confidence
        cv2.putText(img, f"{text} ({confidence:.2f})",
                    (bbox[0][0], bbox[0][1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Create output directory if it doesn't exist
    output_dir = Path('ocr_results')
    output_dir.mkdir(exist_ok=True)

    # Save the annotated image
    output_path = output_dir / f"annotated_{os.path.basename(img_path)}"
    cv2.imwrite(str(output_path), img)
    print(f"Visualization saved to {output_path}")


if __name__ == '__main__':
    main()