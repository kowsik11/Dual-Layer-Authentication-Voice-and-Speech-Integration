# 🎙️ Dual-Layer Authentication: Voice and Speech Integration 🔐

This project focuses on enhancing security by implementing **Dual-Layer Authentication** using both **Voice Recognition** and **Speech Integration**. The system requires the user to authenticate through both voice biometrics (voice recognition) and spoken passphrases, providing an extra layer of protection beyond traditional authentication methods.

## 📝 Project Description

The **Dual-Layer Authentication System** is designed to improve user authentication through the integration of **Voice Recognition** and **Speech-based Passphrases**. By using voice biometrics to recognize users' unique voice patterns and a spoken passphrase as an additional factor, this system aims to provide an extra layer of security for sensitive applications and data. This solution can be applied in various fields like banking, healthcare, and secure online platforms, ensuring both ease of use and robust security.

### 🔑 Key Features:
- **Voice Biometrics**: Recognizes and authenticates users based on unique voice characteristics.
- **Speech Passphrase Authentication**: Requires users to speak a predefined passphrase for access.
- **Two-Factor Authentication (2FA)**: Combines voice recognition with speech to offer double-layered security.
- **Real-Time Authentication**: Performs authentication instantly with low latency.
- **Secure Access**: Ensures only authorized users can access protected resources.
  
## 🧠 Features of the System

- **Voice Recognition**: Analyzes the user's voice to identify unique features like pitch, tone, and cadence.
- **Passphrase Speech**: Requires users to speak a specific phrase, which is then analyzed for both accuracy and voice match.
- **Liveness Detection**: Verifies that the voice input is from a live person to prevent replay attacks.
- **Database Storage**: Stores voice samples and passphrases securely for future authentication attempts.
- **Real-Time Matching**: Matches the recorded voice and spoken passphrase in real-time for seamless authentication.
  
## 🔧 Technologies Used

- **Programming Language**: Python
- **Libraries**: `speech_recognition`, `pyttsx3`, `pyaudio`
- **Machine Learning**: `Librosa`, `scikit-learn` for feature extraction and classification
- **Voice Authentication Model**: GMM (Gaussian Mixture Model) or other classifiers for voice recognition
- **Speech-to-Text**: Google Speech API, CMU Sphinx for converting spoken passphrases into text
- **Web Framework**: Flask (for web integration, if needed)
- **Database**: SQLite or MySQL for storing user data and voice samples

## 🚀 How to Run

### 📥 Prerequisites
Make sure you have the following installed:
- Python 3.x
- Required libraries listed in `requirements.txt`

### ⚙️ Installation Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/dual-layer-authentication.git
   cd dual-layer-authentication
