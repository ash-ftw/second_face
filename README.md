# Second Face — AI Media Forensic Analysis Station

<p align="center">
  <img src="static/hud_test_upload.jpg" alt="Second Face Banner" width="400" />
</p>

<p align="center">
  <strong>Multi-modal digital forensics platform for detecting AI-generated faces, deepfakes, and synthetic media manipulations.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue?logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/Framework-Flask-black?logo=flask" alt="Flask" />
  <img src="https://img.shields.io/badge/Deep%20Learning-TensorFlow%20%7C%20Keras%203-orange?logo=tensorflow" alt="TensorFlow" />
  <img src="https://img.shields.io/badge/Computer%20Vision-OpenCV-green?logo=opencv" alt="OpenCV" />
  <img src="https://img.shields.io/badge/Biometrics-DeepFace-purple" alt="DeepFace" />
  <img src="https://img.shields.io/badge/Database-SQLite%20%28Hash%20Chain%29-lightgrey?logo=sqlite" alt="SQLite" />
</p>

---

## 📌 Overview

**Second Face** is an end-to-end digital media forensic analysis station designed to detect AI-generated face imagery (GANs, StyleGAN, Latent Diffusion models) and image tampering. Combining deep neural network inference, spectral frequency decomposition, error level compression analysis, and biometric profiling, Second Face produces explainable multi-signal forensic verdicts backed by a tamper-evident cryptographic audit chain.

---

## ✨ Key Features

- **Multi-Modal Deepfake Detection**:
  - **Deep Learning Classifier**: Pretrained convolutional neural network (`models/deepfake_detector.keras`) evaluating high-level spatial synthesis markers.
  - **Discrete Fourier Transform (DFT)**: Spectral frequency domain analysis detecting periodic grid artifacts and high-frequency noise spikes characteristic of GAN and Latent Diffusion generators.
  - **Adaptive Error Level Analysis (ELA)**: Resave difference compression analysis with automatic anomaly bounding box detection and colorized heatmaps.
  - **Consensus Scoring Engine**: Weighted synthesis metric synthesizing neural net probability, frequency artifacts, and compression inconsistencies into a calibrated certainty percentage.

- **Biometric Tracking & Demographics**:
  - OpenCV Haar Cascade target face detection and HUD overlays.
  - DeepFace facial analysis engine estimating age bracket and demographic profile per target.

- **Cryptographic Audit Trail & Chain of Custody**:
  - SHA-256 binary hash generation for every ingested asset.
  - Cryptographic block-hash chain linking previous case records, ensuring tamper-evident history in SQLite.
  - On-demand cryptographic ledger verification.

- **Forensic Reporting & Export**:
  - Auto-generated downloadable **Official Forensic PDF Reports** (built with ReportLab).
  - Complete historical forensic case export in CSV format.

- **Interactive Forensic Dashboard**:
  - Dual ingestion modes: local file upload and direct live webcam snapshot capture.
  - Non-blocking asynchronous processing pipeline using multi-threaded execution with status polling.
  - Interactive split-slider A/B comparison view (original vs. forensic overlays).
  - Built-in forensic assistant ("USHA") for natural language telemetry, log lookups, and system summaries.
  - Role-based authentication (User, Admin, Zookeeper).

---

## 🏗️ System Architecture

```
[ User Upload / Webcam ]
           │
           ▼
[ JPEG Matrix Normalization & SHA-256 Hashing ]
           │
           ├──────────────────────────────┬──────────────────────────────┐
           ▼                              ▼                              ▼
 [ Spectral Analysis ]          [ Compression Check ]          [ Deep Learning ]
 • 2D Fast Fourier Transform    • Adaptive Resave (ELA)        • Keras 3 CNN Model
 • High-frequency spike count   • Tamper Bounding Boxes        • Softmax / Sigmoid
 • Jet Colormap Spectrum        • Anomaly Heatmap              • Synthesis Probability
           │                              │                              │
           └──────────────────────────────┼──────────────────────────────┘
                                          ▼
                         [ Biometric & HUD Analysis ]
                         • Haar Cascade Face Localization
                         • DeepFace Demographic Profiling
                                          │
                                          ▼
                          [ Consensus Decision Core ]
                     (Weighted Matrix: Model + DFT + ELA)
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
       [ Cryptographic Block Chain ]               [ Output Deliverables ]
       • Genesis-linked Block Hash                 • Interactive HUD & Sliders
       • SQLite Ledger Audit Trail                 • Downloadable PDF Report
       • Tamper-Evident Ledger Integrity           • Telemetry Dashboard & CSV
```

---

## 📁 Repository Structure

```text
second_face/
├── app.py                      # Flask web application & API routing
├── run_app.py                  # Standalone application entrypoint & error logger
├── ai_generator.py             # Forensic pipeline (DFT, ELA, DeepFace, PDF generation)
├── deepfake_ai.py              # Keras deepfake inference model wrapper
├── train_deepfake_model.py     # CLI training script for custom deepfake datasets
├── requirements.txt            # Python dependencies
├── forensic_history.db         # SQLite database storing cases, users & blockchain ledger
├── models/
│   ├── deepfake_detector.keras # Trained Keras 3 deepfake detection neural network
│   └── .deepface/              # Cached facial analysis model weights
├── static/
│   └── uploads/                # Upload directory for ingested media & generated artifacts
├── templates/
│   ├── index.html              # Forensic dashboard & interactive triage station
│   ├── login.html              # Authorization terminal
│   └── result.html             # Legacy result view
└── README.md                   # Project documentation
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10 to 3.12** installed on your system.
- Git (optional, for cloning).

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/second_face.git
cd second_face
```

### 2. Set Up a Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note**: For environments using TensorFlow and Keras 3 alongside DeepFace, ensure the standalone `keras` package is installed as specified in `requirements.txt`.

### 4. Run the Application

Launch using the application runner:

```bash
python run_app.py
```

Or directly via Flask:

```bash
python app.py
```

The application will start at:
```
http://127.0.0.1:5000
```

---

## 🔐 Default Access Credentials

The application initializes default credentials in `forensic_history.db` upon initial launch:

| Identity Address | Passkey | Role | Permissions |
| :--- | :--- | :--- | :--- |
| `guest_user` | `user123` | `user` | Standard triage, image analysis, PDF download |
| `site_admin` | `admin123` | `admin` | Full triage, history export, system operations |
| `master_zookeeper` | `zoo123` | `zookeeper` | Elevated station control |

*(Credentials are hashed using SHA-256 before storage).*

---

## 🔬 Forensic Methodology

| Technique | Description | Role in Verdict |
| :--- | :--- | :--- |
| **Convolutional Neural Network** | 224×224 feature extractor trained on authentic vs. synthetic datasets | 30% weight in final score; assesses high-level synthesis artifacts |
| **Discrete Fourier Transform (DFT)** | Analyzes 2D spatial frequency domain with bilateral pre-filtering | 65% base weight; identifies unnatural periodic patterns from upsamplers |
| **Adaptive Error Level Analysis (ELA)** | Analyzes compression loss variance across JPEG matrices | Identifies composite modifications and regional splicing |
| **Tamper Heatmap** | Contours anomalous compression differentials and overlays bounding boxes | Visual localization of localized image manipulation |
| **Biometric HUD** | Multi-scale face detection paired with DeepFace demographic analysis | Validates face count, target localization, and biometric continuity |
| **Cryptographic Block Hash** | Chained SHA-256 block hash incorporating previous hash, current hash, and verdict | Guarantees tamper-evident chain of custody |

---

## 🛠️ Model Training

To train the deepfake detector on a custom dataset, organize your data into class folders:

```text
dataset/
├── authentic/
│   ├── img001.jpg
│   └── ...
└── deepfake/
    ├── img002.jpg
    └── ...
```

Run the training pipeline:

```bash
python train_deepfake_model.py \
  --data-dir path/to/dataset \
  --output models/deepfake_detector.keras \
  --checkpoint-dir models/checkpoints \
  --image-size 224 \
  --batch-size 16 \
  --epochs 15
```

The script includes:
- Data augmentation (horizontal flip, random rotation, contrast adjustment).
- Validation AUC monitoring.
- Early stopping and model checkpointing.
- Training metric export to CSV.

---

## 📡 API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/process` | `POST` | Upload and trigger asynchronous forensic analysis of an image file. |
| `/process_webcam` | `POST` | Submit base64-encoded webcam snapshot for asynchronous analysis. |
| `/api/v1/task_status/<task_id>` | `GET` | Poll background analysis task status (`PROCESSING`, `SUCCESS`, `FAILED`). |
| `/api/v1/metrics` | `GET` | Returns aggregated metrics (total processed, deepfakes, authentic). |
| `/api/v1/chat` | `POST` | Query the USHA assistant chatbot for status, logs, or methodology. |
| `/api/v1/export/csv` | `GET` | Export forensic database cases as a CSV audit trail. |
| `/download_pdf/<filename>` | `GET` | Download the official generated PDF forensic acquisition report. |
| `/api/v1/clear_logs` | `POST` | Clear case log history. |

---

## 🛡️ Ethics & Disclaimer

Second Face is developed for digital media forensics, security research, and educational purposes. Forensic scores represent probabilistic confidence levels derived from computational heuristics and statistical models. They should be corroborated with additional evidentiary procedures in formal forensic or legal proceedings.
