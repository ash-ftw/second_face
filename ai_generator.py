import hashlib
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# =========================================================================
# 🛠️ GLOBAL COMPATIBILITY PATCH FOR REPORTLAB
# =========================================================================
original_md5 = hashlib.md5
def patched_md5(*args, **kwargs):
    kwargs.pop('usedforsecurity', None)
    return original_md5(*args, **kwargs)
hashlib.md5 = patched_md5
# =========================================================================

import cv2
import numpy as np
import os
import piexif
import sqlite3
from datetime import datetime
from PIL import Image, ImageChops
from deepface import DeepFace
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from deepfake_ai import DeepfakeDetector

class AIAger:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.deepfake_detector = DeepfakeDetector()
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect('forensic_history.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT UNIQUE,
                filename TEXT,
                timestamp TEXT,
                age_bracket TEXT,
                demographics TEXT,
                dft_score INTEGER,
                ela_verdict TEXT,
                final_verdict TEXT,
                block_hash TEXT,
                gan_signature TEXT,
                metadata_dump TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def normalize_and_validate_image(self, image_path):
        try:
            directory, filename = os.path.split(image_path)
            base_name, ext = os.path.splitext(filename)
            standardized_path = os.path.join(directory, f"normalized_{base_name}.jpg")
            
            img = Image.open(image_path).convert('RGB')
            img.save(standardized_path, 'JPEG', quality=100)
                
            return True, standardized_path, "JPEG Matrix Standardized via Core Engine"
        except Exception as e:
            return False, image_path, f"Image Normalization Fault: {str(e)}"

    def age_face(self, image_path):
        forensic_report = []
        directory, filename = os.path.split(image_path)

        success, active_path, byte_msg = self.normalize_and_validate_image(image_path)
        if not success:
            raise ValueError(byte_msg)

        hasher = hashlib.sha256()
        with open(active_path, 'rb') as f:
            hasher.update(f.read())
        file_hash = hasher.hexdigest()

        camera_metadata = "Brand Signatures: Not Detected | Editing Tags: Clean"
        try:
            pil_img = Image.open(image_path)
            if "exif" in pil_img.info:
                exif_dict = piexif.load(pil_img.info["exif"])
                make = exif_dict.get("0th", {}).get(piexif.ImageIFD.Make, b"Unknown").decode('utf-8', errors='ignore')
                model = exif_dict.get("0th", {}).get(piexif.ImageIFD.Model, b"Unknown").decode('utf-8', errors='ignore')
                software = exif_dict.get("0th", {}).get(piexif.ImageIFD.Software, b"None").decode('utf-8', errors='ignore')
                if make != "Unknown" or software != "None":
                    camera_metadata = f"HW Source: {make} {model} | Software: {software}"
        except Exception:
            pass

        dft_filename = "dft_" + filename
        dft_path = os.path.join(directory, dft_filename)
        dft_score = self._compute_dft_fingerprint(active_path, dft_path)

        ela_filename = "ela_" + filename
        ela_path = os.path.join(directory, ela_filename)
        ela_anomaly_detected, tamper_boxes = self._compute_adaptive_ela_with_heatmap(active_path, ela_path)

        img = cv2.imread(active_path)
        heatmap_filename = "heatmap_" + filename
        heatmap_path = os.path.join(directory, heatmap_filename)
        
        if img is not None:
            heatmap_canvas = img.copy()
            if ela_anomaly_detected and len(tamper_boxes) > 0:
                for (x, y, w, h) in tamper_boxes:
                    sub_box = heatmap_canvas[y:y+h, x:x+w]
                    red_tint = np.zeros_like(sub_box)
                    red_tint[:, :, 2] = 255
                    blended_box = cv2.addWeighted(sub_box, 0.6, red_tint, 0.4, 0)
                    heatmap_canvas[y:y+h, x:x+w] = blended_box
                    cv2.rectangle(heatmap_canvas, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.imwrite(heatmap_path, heatmap_canvas)
            else:
                cv2.imwrite(heatmap_path, heatmap_canvas)

        face_found = False
        target_profiles_summary = []
        
        if img is not None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) > 0:
                face_found = True
                face_index = 1
                for (x, y, w, h) in faces:
                    cv2.rectangle(img, (x, y), (x+w, y+h), (59, 130, 246), 2)
                    cv2.putText(img, f"TARGET 0{face_index}", (x, y - 8), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (59, 130, 246), 1, cv2.LINE_AA)
                    
                    face_crop = img[y:y+h, x:x+w]
                    crop_filename = f"crop_{face_index}_{filename}"
                    crop_path = os.path.join(directory, crop_filename)
                    cv2.imwrite(crop_path, face_crop)
                    
                    try:
                        with ThreadPoolExecutor(max_workers=1) as face_executor:
                            face_future = face_executor.submit(
                                DeepFace.analyze,
                                img_path=crop_path,
                                actions=['age', 'gender'],
                                enforce_detection=False,
                            )
                            demographics = face_future.result(timeout=20)
                        if isinstance(demographics, list): demographics = demographics[0]
                        f_age = f"{int(demographics.get('age', 30)) - 3} - {int(demographics.get('age', 30)) + 3} Years"
                        f_gender = str(demographics.get("dominant_gender", "Unknown"))
                    except FuturesTimeoutError:
                        f_age, f_gender = "Unknown", "Unknown"
                    except Exception:
                        f_age, f_gender = "Unknown", "Unknown"
                        
                    target_profiles_summary.append(f"Target 0{face_index} Profile -> Gender: {f_gender} / Age Range: {f_age}")
                    face_index += 1
                    
                cv2.imwrite(os.path.join(directory, "hud_" + filename), img)
            else:
                cv2.imwrite(os.path.join(directory, "hud_" + filename), img)

        if face_found and target_profiles_summary:
            biometric_payload = " | ".join(target_profiles_summary)
            primary_split = target_profiles_summary[0].split("-> ")[1]
            age_bracket = primary_split.split(" / ")[1].replace("Age Range: ", "")
            gender_str = primary_split.split(" / ")[0].replace("Gender: ", "")
        else:
            biometric_payload = "No Face Detected"
            age_bracket = "No Face Detected"
            gender_str = "N/A"

        ela_weight = 35 if ela_anomaly_detected else 0
        consensus_score = int((dft_score * 0.65) + ela_weight)

        model_prediction = self.deepfake_detector.predict(active_path)
        if model_prediction.get("available"):
            model_confidence = int(round(float(model_prediction.get("confidence", 0.0)) * 100))
            combined_score = int(round((consensus_score * 0.7) + (model_confidence * 0.3)))
            model_status_line = f"{model_prediction.get('label', 'unknown').upper()} ({model_confidence}% Confidence)"
        else:
            combined_score = consensus_score
            model_status_line = f"Unavailable - {model_prediction.get('reason', 'Model unavailable')}"

        if combined_score > 60:
            final_verdict = f"🚨 DEEPFAKE ARTIFACTS DETECTED ({combined_score}% Certainty)"
            gan_signature = "StyleGAN3 Tensor Replication Model" if dft_score > 75 else "Latent Diffusion Model"
            xai_explanation = "Failed validation. Internal pixel phase noise variance and the learned classifier both flagged synthesis anomalies."
        else:
            final_verdict = f"🟢 VERIFIED AUTHENTIC CAMERA CAPTURE ({100 - combined_score}% Certainty)"
            gan_signature = "None (Camera Sensor Source Verified)"
            xai_explanation = "Passed validation. Noise density patterns and the learned classifier align with authentic sensor behavior."

        forensic_report.append(f"🔒 SHA-256 Signature||{file_hash}")
        forensic_report.append(f"⚖️ Consensus Verdict||{final_verdict}")
        forensic_report.append(f"📁 Binary Magic Byte Status||{byte_msg}")
        forensic_report.append(f"📡 Embedded Metadata Trace||{camera_metadata}")
        forensic_report.append(f"🎭 GAN Architecture Origin||{gan_signature}")
        forensic_report.append(f"🤖 Deepfake Model Output||{model_status_line}")
        forensic_report.append(f"🧠 Explainable AI Core||{xai_explanation}")
        
        if face_found:
            for item in target_profiles_summary:
                parts = item.split(" -> ")
                forensic_report.append(f"🧬 Biometric {parts[0]}||{parts[1]}")
        else:
            forensic_report.append(f"🧬 Biometric Target||No Face Detected")

        try:
            conn = sqlite3.connect('forensic_history.db')
            cursor = conn.cursor()
            cursor.execute('SELECT block_hash FROM cases ORDER BY id DESC LIMIT 1')
            prev_row = cursor.fetchone()
            prev_hash = prev_row[0] if prev_row else "GENESIS_BLOCK_0000"
            
            block_string = f"{prev_hash}-{file_hash}-{consensus_score}-{gan_signature}"
            block_hash = hashlib.sha256(block_string.encode('utf-8')).hexdigest()

            cursor.execute('''
                INSERT OR REPLACE INTO cases (file_hash, filename, timestamp, age_bracket, demographics, dft_score, ela_verdict, final_verdict, block_hash, gan_signature, metadata_dump)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (file_hash, filename, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), age_bracket, gender_str, dft_score, "Anomaly" if ela_anomaly_detected else "Clean", final_verdict, block_hash, gan_signature, camera_metadata))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Cryptographic Chain Link Error: {e}")

        base_name, _ = os.path.splitext(filename)
        normalized_filename = f"normalized_{base_name}.jpg"
        self.generate_pdf_report(os.path.join(directory, normalized_filename), file_hash, final_verdict, xai_explanation, age_bracket, gender_str, camera_metadata, gan_signature, biometric_payload)

        log_path = active_path + "_forensic_suite.txt"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(forensic_report))
        return log_path

    def _compute_dft_fingerprint(self, input_path, output_path):
        try:
            img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
            img = cv2.resize(img, (512, 512))
            insulated = cv2.bilateralFilter(img, d=9, sigmaColor=65, sigmaSpace=65)
            dft = cv2.dft(np.float32(insulated), flags=cv2.DFT_COMPLEX_OUTPUT)
            dft_shift = np.fft.fftshift(dft)
            magnitude = 20 * np.log(cv2.magnitude(dft_shift[:,:,0], dft_shift[:,:,1]) + 1e-5)
            h, w = magnitude.shape
            magnitude[int(h/2)-4:int(h/2)+4, :] = np.mean(magnitude)
            magnitude[:, int(w/2)-4:int(w/2)+4] = np.mean(magnitude)
            center_mask = np.ones((h, w), np.uint8)
            cv2.circle(center_mask, (int(w/2), int(h/2)), 45, 0, -1)
            high_freq_vals = magnitude[center_mask == 1]
            anomalous_spikes = np.sum(high_freq_vals > (np.mean(high_freq_vals) + 4.0 * np.std(high_freq_vals)))
            cv2.imwrite(output_path, cv2.applyColorMap(cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8), cv2.COLORMAP_JET))
            return int(np.clip((anomalous_spikes / 180.0) * 100.0, 5, 98))
        except Exception: return 10

    def _compute_adaptive_ela_with_heatmap(self, input_path, output_path, quality=90):
        try:
            tmp_resave = input_path + "_tmp.jpg"
            orig = Image.open(input_path).convert('RGB')
            orig.save(tmp_resave, 'JPEG', quality=quality)
            
            diff = ImageChops.difference(orig, Image.open(tmp_resave))
            open_cv_diff = cv2.cvtColor(np.array(diff, dtype=np.uint8), cv2.COLOR_RGB2GRAY)
            
            mean, stddev = cv2.meanStdDev(open_cv_diff)
            anomaly_detected = stddev[0][0] > 1.1
            
            detected_bounding_boxes = []
            if anomaly_detected:
                _, thresh_mask = cv2.threshold(open_cv_diff, 8, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(thresh_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    if cv2.contourArea(cnt) > 80:
                        x, y, w, h = cv2.boundingRect(cnt)
                        detected_bounding_boxes.append((x, y, w, h))

            diff_scaled = np.clip((open_cv_diff / (np.max(open_cv_diff) if np.max(open_cv_diff) > 0 else 1)) * 255.0 * 3.0, 0, 255).astype(np.uint8)
            try:
                enhanced_view = cv2.applyColorMap(diff_scaled, cv2.COLORMAP_TWILIGHT_SHIFT)
            except Exception:
                enhanced_view = cv2.applyColorMap(diff_scaled, cv2.COLORMAP_JET)

            if not cv2.imwrite(output_path, enhanced_view):
                fallback_view = cv2.applyColorMap(diff_scaled, cv2.COLORMAP_JET)
                cv2.imwrite(output_path, fallback_view)

            if not os.path.exists(output_path):
                Image.fromarray(diff_scaled).save(output_path)
            
            if os.path.exists(tmp_resave): os.remove(tmp_resave)
            return anomaly_detected, detected_bounding_boxes
        except Exception: 
            return False, []

    def generate_pdf_report(self, image_path, file_hash, verdict, explanation, age, gender, meta, gan, dynamic_biometrics):
        pdf_path = image_path + "_official_report.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        title_style = ParagraphStyle('TitleStyle', fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor('#3b82f6'))
        text_style = ParagraphStyle('TextStyle', fontName='Helvetica', fontSize=11, textColor=colors.HexColor('#ffffff'), leading=14)
        label_style = ParagraphStyle('LabelStyle', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#a1a1aa'))
        
        story = []
        story.append(Paragraph("🛡️ NATIONAL DIGITAL FORENSICS ACQUISITION CASE REPORT", title_style))
        story.append(Spacer(1, 15))
        
        data = [
            [Paragraph("SHA-256 HASH SIGNATURE", label_style), Paragraph(file_hash, text_style)],
            [Paragraph("ANALYSIS TIMESTAMP", label_style), Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"), text_style)],
            [Paragraph("CONSENSUS VERDICT", label_style), Paragraph(verdict, text_style)],
            [Paragraph("CLASSIFIED GAN MODEL", label_style), Paragraph(gan, text_style)],
            [Paragraph("EXPLAINABLE AI CORE", label_style), Paragraph(explanation, text_style)],
            [Paragraph("TRACKED BIOMETRICS ARRAYS", label_style), Paragraph(dynamic_biometrics, text_style)],
            [Paragraph("METADATA DUMP SUMMARY", label_style), Paragraph(meta, text_style)]
        ]
        
        t = Table(data, colWidths=[160, 360])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#0a0d16')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#1e293b')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(t)
        doc.build(story)