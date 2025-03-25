import random
import time
from pathlib import Path
import os

# Card rank mapping for standardization
CARD_RANK_MAP = {
    '2': '2', 'two': '2', 
    '3': '3', 'three': '3',
    '4': '4', 'four': '4',
    '5': '5', 'five': '5',
    '6': '6', 'six': '6',
    '7': '7', 'seven': '7',
    '8': '8', 'eight': '8',
    '9': '9', 'nine': '9',
    '10': '10', 'ten': '10',
    'j': 'jack', 'jack': 'jack',
    'q': 'queen', 'queen': 'queen',
    'k': 'king', 'king': 'king',
    'a': 'ace', 'ace': 'ace'
}

# Available ranks for simulation
AVAILABLE_RANKS = list(set(CARD_RANK_MAP.values()))

class CardOCR:
    def __init__(self, specific_image=None):
        print("Initializing Card OCR (simulated)...")
        self.screenshot_dir = Path('Screenshot')
        self.specific_image = specific_image
        
        # Use default image if none specified
        if self.specific_image is None:
            self.specific_image = "Screenshot/001.PNG"
            
        # Check if the specific image exists
        if not os.path.exists(self.specific_image):
            print(f"Warning: Image {self.specific_image} not found.")
            # Try with full path
            full_path = os.path.join(os.getcwd(), self.specific_image)
            if not os.path.exists(full_path):
                print(f"Warning: Image not found at {full_path}")
        else:
            print(f"Using image file: {self.specific_image}")
        
    def take_screenshot(self):
        """Return the path to the specified image instead of taking a screenshot"""
        print(f"Using specified image file: {self.specific_image}")
        return self.specific_image
    
    def detect_cards(self, image_path=None):
        """Simulate detecting cards from regions of the image"""
        # Use the specified image if no image path provided
        if image_path is None:
            image_path = self.take_screenshot()
            
        print(f"Processing {image_path}...")
        
        # Simulate processing delay
        time.sleep(1)
            
        # Simulate different card detection results based on image number
        image_number = os.path.basename(image_path).split('.')[0]
        print(f"Image number: {image_number}")
        
        # Set specific card values based on the image number
        if image_number == "001":
            dealer_card = "ace"
            player_card1 = "10"
            player_card2 = "king"
        elif image_number == "002":
            dealer_card = "king"
            player_card1 = "7"
            player_card2 = "6"
        elif image_number == "003":
            dealer_card = "5"
            player_card1 = "jack"
            player_card2 = "9"
        else:
            # Random values for other images
            dealer_card = random.choice(AVAILABLE_RANKS)
            player_cards = random.sample([c for c in AVAILABLE_RANKS if c != dealer_card], 2)
            player_card1, player_card2 = player_cards
            
        # Format results
        results = [
            {
                'region': 1,
                'raw_text': dealer_card,
                'card_value': dealer_card,
                'confidence': random.uniform(0.75, 0.99)
            },
            {
                'region': 2,
                'raw_text': player_card1,
                'card_value': player_card1,
                'confidence': random.uniform(0.75, 0.99)
            }
        ]
        
        return results
    
    def get_dealer_card(self):
        """Get the dealer's card"""
        results = self.detect_cards()
        if results and results[0]:
            return results[0]['card_value']
        return None
        
    def get_player_cards(self):
        """Get the player's card(s)"""
        results = self.detect_cards()
        
        # First card from region 2
        if results and len(results) > 1 and results[1]:
            # For testing purposes, we'll create a second card value that's different from the first
            first_card = results[1]['card_value']
            
            # For images 001-003, use predefined pairs of cards
            image_number = os.path.basename(self.specific_image).split('.')[0]
            
            if image_number == "001":
                second_card = "king"
            elif image_number == "002":
                second_card = "6"
            elif image_number == "003":
                second_card = "9"
            else:
                # Otherwise generate a different second card
                second_card = random.choice([rank for rank in AVAILABLE_RANKS 
                                           if rank not in [first_card, results[0]['card_value']]])
            
            return first_card, second_card
        
        return None, None

# Simple test function
def test_card_detection(image_path=None):
    ocr = CardOCR(image_path)
    dealer_card = ocr.get_dealer_card()
    player_card1, player_card2 = ocr.get_player_cards()
    
    print(f"\nDetection Results:")
    print(f"Dealer's card: {dealer_card}")
    print(f"Player's first card: {player_card1}")
    print(f"Player's second card: {player_card2}")

if __name__ == "__main__":
    test_card_detection("Screenshot/001.PNG") 