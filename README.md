# Escape Room Captcha Login System

A secure and gamified login interface that replaces traditional text/image captchas with an interactive escape-room-themed puzzle experience. This project not only provides a unique user experience but also employs advanced machine learning to detect and block automated bot interactions.

## 🌟 Features

- **Gamified Captcha Experience**: Users must solve interactive puzzles hidden within a dark-themed escape room environment to authenticate:
  - Bookshelf height sorting
  - Korean keyboard layout decryption
  - Symbol counting challenge
- **Advanced Bot Detection**: Collects detailed user interaction data (mouse movements, click events, timing) and scores it using an Isolation Forest machine learning model to accurately distinguish humans from bots.

- **Data Collection & Training**: Includes Python scripts and Selenium bots to generate synthetic bot data and train the AI classification model.

## 🛠️ Technology Stack

- **Frontend**: Next.js (App Router), React, CSS Modules, Lucide React

- **AI / Machine Learning**: Python, scikit-learn (Isolation Forest), Pandas
- **Data Automation**: Selenium (for bot data generation)

## 📂 Project Structure

- `/src`: Next.js frontend code (Pages, API routes, Components, Utilities).
- `/ai`: Python scripts for training the bot detection model (`training.py`, `score_model.py`).
- `/bot`: Selenium scripts for generating automated bot interaction datasets (`collect_bot_data.py`, `collect_human_data.py`).
- `/model`: Contains the trained machine learning models (e.g., `classifier.pkl`).
- `/dataset`: Stored interaction JSON logs for both bots and humans used for model training.

## 🚀 Getting Started

### Prerequisites

- Node.js 18.x or later
- Python 3.10+ (for AI model training and evaluation)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/a01086841531-gif/escapeCaptcha.git
   cd escapeCaptcha
   ```

2. **Install Node dependencies**
   ```bash
   npm install
   ```

3. **Run the Next.js Development Server**
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

### AI Model Setup (Optional)

If you want to retrain the bot detection model or run data collection scripts:

1. **Install Python dependencies**
   ```bash
   pip install pandas scikit-learn selenium
   ```

2. **Train the Model**
   Navigate to the project root and run the training script:
   ```bash
   python ai/training.py
   ```
   This will generate a new `classifier.pkl` model based on the datasets.

## 📝 License
This project is [MIT](https://choosealicense.com/licenses/mit/) licensed.
