import os
import time
import cv2
import numpy as np
import hashlib
from PyQt6 import QtWidgets, QtGui, QtCore

try:
    import mediapipe as mp
except Exception:
    mp = None


class CameraWorker(QtCore.QThread):
    frame_signal = QtCore.pyqtSignal(QtGui.QImage)
    fingerprint_signal = QtCore.pyqtSignal(str)
    expression_signal = QtCore.pyqtSignal(str)

    def __init__(self, camera_index=0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self._running = False
        self.cap = None
        self.mp_face = mp.solutions.face_mesh if mp else None

    def run(self):
        self._running = True
        self.cap = cv2.VideoCapture(self.camera_index)
        face_mesh = None
        if self.mp_face:
            face_mesh = self.mp_face.FaceMesh(static_image_mode=False, max_num_faces=1)

        while self._running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            landmarks = None
            if face_mesh:
                results = face_mesh.process(rgb)
                if results.multi_face_landmarks:
                    lm = results.multi_face_landmarks[0]
                    h, w, _ = frame.shape
                    landmarks = [(int(p.x * w), int(p.y * h)) for p in lm.landmark]
                    mood = self._detect_expression(landmarks)
                    self.expression_signal.emit(mood)

            # convert frame to QImage
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QtGui.QImage(frame.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_BGR888)
            self.frame_signal.emit(qt_image.copy())

            # keep a small sleep to be cooperative
            QtCore.QThread.msleep(15)

        if self.cap:
            self.cap.release()

    def stop(self):
        self._running = False
        self.wait(1000)

    def capture_fingerprint(self, landmarks):
        """Compute a fingerprint from landmarks and save it locally. Returns id."""
        if not landmarks:
            return ""
        arr = np.asarray(landmarks).astype(np.float32).flatten()
        # normalize
        arr = (arr - arr.mean()) / (arr.std() + 1e-9)
        # compress to 256-d by hashing blocks
        vec = []
        block_size = max(1, len(arr) // 256)
        for i in range(0, len(arr), block_size):
            block = arr[i : i + block_size]
            vec.append(float(np.mean(block)))
        vec = np.asarray(vec[:256], dtype=np.float32)
        # create id
        h = hashlib.sha256(vec.tobytes()).hexdigest()[:16]
        path = os.path.join("ui", "fingerprints")
        os.makedirs(path, exist_ok=True)
        np.save(os.path.join(path, f"{h}.npy"), vec)
        self.fingerprint_signal.emit(h)
        return h

    def _detect_expression(self, landmarks):
        # crude smile detection using lip corners and mouth center
        if len(landmarks) < 10:
            return "neutral"
        # indices approximated from MediaPipe face mesh: left/right mouth corners
        left = landmarks[61]
        right = landmarks[291]
        top = landmarks[13]
        bottom = landmarks[14]
        mouth_width = np.linalg.norm(np.array(right) - np.array(left))
        mouth_height = np.linalg.norm(np.array(bottom) - np.array(top))
        mar = mouth_height / (mouth_width + 1e-9)
        if mar > 0.35:
            return "excited"
        if mar < 0.12:
            return "calm"
        return "neutral"


class DesktopUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BLACK JARVIS — Hologram Camera")
        self.setFixedSize(960, 640)
        self.video_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.video_label.setFixedSize(920, 520)
        self.start_btn = QtWidgets.QPushButton("Start Camera")
        self.stop_btn = QtWidgets.QPushButton("Stop Camera")
        self.save_btn = QtWidgets.QPushButton("Save Face Fingerprint")
        self.status_label = QtWidgets.QLabel("Status: idle")

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.save_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.video_label)
        layout.addLayout(btn_layout)
        layout.addWidget(self.status_label)

        self.cam = CameraWorker()
        self.cam.frame_signal.connect(self._update_frame)
        self.cam.fingerprint_signal.connect(self._on_fingerprint_saved)
        self.cam.expression_signal.connect(self._on_expression)

        self.start_btn.clicked.connect(self.start_camera)
        self.stop_btn.clicked.connect(self.stop_camera)
        self.save_btn.clicked.connect(self.save_fingerprint)

        self.latest_landmarks = None

    def start_camera(self):
        if not self.cam.isRunning():
            self.cam.start()
            self.status_label.setText("Status: camera started")

    def stop_camera(self):
        if self.cam.isRunning():
            self.cam.stop()
            self.status_label.setText("Status: camera stopped")

    def _update_frame(self, qimage: QtGui.QImage):
        pix = QtGui.QPixmap.fromImage(qimage).scaled(self.video_label.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self.video_label.setPixmap(pix)

    def save_fingerprint(self):
        # Attempt to get last frame landmarks by a short run of face mesh on current frame
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            self.status_label.setText("Status: camera capture failed")
            return
        if not mp:
            self.status_label.setText("Status: MediaPipe not installed")
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1)
        res = face_mesh.process(rgb)
        landmarks = None
        if res.multi_face_landmarks:
            lm = res.multi_face_landmarks[0]
            h, w, _ = frame.shape
            landmarks = [(int(p.x * w), int(p.y * h)) for p in lm.landmark]
        fid = self.cam.capture_fingerprint(landmarks)
        if fid:
            self.status_label.setText(f"Status: fingerprint saved ({fid})")

    def _on_fingerprint_saved(self, fid: str):
        self.status_label.setText(f"Status: fingerprint saved ({fid})")

    def _on_expression(self, mood: str):
        self.status_label.setText(f"Status: detected mood: {mood}")


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    win = DesktopUI()
    win.show()
    sys.exit(app.exec())
