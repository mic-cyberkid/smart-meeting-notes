import sys, os, json, markdown, webbrowser, subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout,
    QWidget, QLabel, QTextEdit, QFileDialog, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from .recorder import Recorder
from jinja2 import Template

class Worker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str, str)  # transcript, summary

    def run(self):
        # Step 1: Transcribe (runs locally cached Whisper)
        self.progress.emit(30)
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe("recording.wav")
        transcript = result["text"]

        # Step 2: Summarize (local BART or use Colab artifact)
        self.progress.emit(70)
        if os.path.exists("models/summary.txt"):
            with open("models/summary.txt") as f:
                summary = f.read()
        else:
            # Fallback: use transformers
            from transformers import pipeline
            summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
            summary = summarizer(transcript, max_length=150, min_length=30, do_sample=False)[0]['summary_text']

        self.progress.emit(100)
        self.finished.emit(transcript, summary)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Meeting Notes")
        self.setFixedSize(500, 600)
        self.recorder = Recorder()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.status = QLabel("Ready")
        self.btn_record = QPushButton("Start Recording")
        self.btn_record.clicked.connect(self.toggle_record)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.btn_export = QPushButton("Export to Markdown")
        self.btn_export.clicked.connect(self.export)

        layout.addWidget(self.status)
        layout.addWidget(self.btn_record)
        layout.addWidget(self.progress)
        layout.addWidget(self.result)
        layout.addWidget(self.btn_export)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.recording = False
        self.worker = None

    def toggle_record(self):
        if not self.recording:
            self.recorder.start()
            self.btn_record.setText("Stop Recording")
            self.status.setText("Recording...")
            self.recording = True
        else:
            path = self.recorder.stop()
            self.btn_record.setText("Processing...")
            self.btn_record.setEnabled(False)
            self.progress.setVisible(True)
            self.progress.setValue(0)

            self.worker = Worker()
            self.worker.progress.connect(self.progress.setValue)
            self.worker.finished.connect(self.on_done)
            self.worker.start()

            self.recording = False

    def on_done(self, transcript, summary):
        self.progress.setVisible(False)
        self.btn_record.setText("Start Recording")
        self.btn_record.setEnabled(True)
        self.status.setText("Done! Exported below.")

        html = f"""
        <h3>Transcript</h3>
        <pre>{transcript}</pre>
        <h3>AI Summary</h3>
        <p>{summary}</p>
        """
        self.result.setHtml(html)

        # Save artifacts
        os.makedirs("output", exist_ok=True)
        with open("output/transcript.txt", "w") as f:
            f.write(transcript)
        with open("output/summary.txt", "w") as f:
            f.write(summary)

        # Auto-export Markdown
        self.export_to_md(transcript, summary)

    def export_to_md(self, transcript, summary):
        template = Template("""
# Meeting Notes

**Recorded:** {{ now }}

## Summary
{{ summary }}

## Full Transcript
