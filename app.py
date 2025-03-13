from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import pytesseract
import re
import cv2
import json
import logging

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Set Tesseract path based on the operating system
if os.name == 'nt':  # Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'
else:  # Linux/Mac
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
# try:
#     pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract" if os.name != "nt" else r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# except Exception as e:
#     logging.error(f"Error setting Tesseract path: {e}")
#     exit(1)

def extract_amount(image_path):
    """Extract amounts from the uploaded image."""
    try:
        # Load the image
        image = cv2.imread(image_path)
        if image is None:
            return ['Error: Image not loaded']

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Resize to enhance OCR accuracy
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Reduce noise
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        # Otsu’s binarization
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Extract text using PyTesseract
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(thresh, config=custom_config)

        # Debug: Log raw OCR output
        logging.debug(f"Raw OCR Output: {text}")

        # Find amounts using regex (handles commas)
        amount_pattern = re.compile(r'\d{1,3}(?:,\d{3})+')
        amounts = amount_pattern.findall(text)

        # Remove duplicates & clean commas
        if amounts:
            amounts = [amount.replace(',', '') for amount in set(amounts)]
            amounts.sort(key=lambda x: int(x))
        else:
            amounts = ['No amount found']

        return amounts
    except Exception as e:
        logging.error(f"Error extracting amounts: {e}")
        return ['Error processing image']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    """Upload file and extract amounts."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        amounts = extract_amount(filepath)
        return redirect(url_for('result', image_path=file.filename, amounts=json.dumps(amounts)))
    return jsonify({'error': 'Invalid file type'})

@app.route('/result')
def result():
    """Display extracted amounts."""
    image_path = request.args.get('image_path', None)
    amounts_json = request.args.get('amounts', '[]')
    extracted_amounts = json.loads(amounts_json)
    return render_template('result.html', image_path='/' + os.path.join(app.config['UPLOAD_FOLDER'], image_path), extracted_amounts=extracted_amounts)

if __name__ == '__main__':
    app.run(debug=True)
