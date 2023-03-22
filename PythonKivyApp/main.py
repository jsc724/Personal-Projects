import os
import io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE
from email import encoders
import tempfile

import tkinter as tk
from tkinter import filedialog

import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import ObjectProperty
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture
from PIL import Image
import cv2
from io import BytesIO
import datetime

class UploadApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical')
        self.bill_of_lading_label = Label(text='Bill of Lading:')
        self.camera = Camera(play=True, resolution=(640, 480), index=0)
        self.capture_button = Button(text='Capture Bill of Lading', on_press=self.capture_image)
        self.fuel_receipts_label = Label(text='Fuel Receipts:')
        self.fuel_receipts_chooser = Button(text='Select Fuel Receipts', on_press=self.select_fuel_receipts)
        self.repair_receipts_label = Label(text='Repair Receipts:')
        self.repair_receipts_chooser = Button(text='Select Repair Receipts', on_press=self.select_repair_receipts)
        self.upload_button = Button(text='Upload', on_press=self.upload_files)
        layout.add_widget(self.bill_of_lading_label)
        layout.add_widget(self.camera)
        layout.add_widget(self.capture_button)
        layout.add_widget(self.fuel_receipts_label)
        layout.add_widget(self.fuel_receipts_chooser)
        layout.add_widget(self.repair_receipts_label)
        layout.add_widget(self.repair_receipts_chooser)
        layout.add_widget(self.upload_button)
        return layout

    def capture_image(self, instance):
        camera = self.camera
        camera.export_to_png("temp.png")
        image = Image.open("temp.png").convert("1")
        buf = BytesIO()
        image.save(buf, format="PDF")
        buf.seek(0)
        with open("bill_of_lading.pdf", "wb") as f:
            f.write(buf.getvalue())
        self.bill_of_lading_image_path = "bill_of_lading.pdf"
        self.capture_button.text = "Captured Bill of Lading"
        os.remove("temp.png")

    def select_fuel_receipts(self, instance):
        root = tk.Tk()
        root.withdraw()
        paths = filedialog.askopenfilenames(filetypes=[('Image files', '*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.heic')])
        self.fuel_receipts_chooser.text = ', '.join([os.path.basename(path) for path in paths])
        self.fuel_receipt_paths = paths

    def select_repair_receipts(self, instance):
        root = tk.Tk()
        root.withdraw()
        paths = filedialog.askopenfilenames(filetypes=[('Image files', '*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.heic')])
        self.repair_receipts_chooser.text = ', '.join([os.path.basename(path) for path in paths])
        self.repair_receipt_paths = paths

    def upload_files(self, instance):
        folder_name = 'Uploaded Files ' + str(datetime.datetime.now())
        folder_id = create_drive_folder(folder_name)

        if hasattr(self, 'bill_of_lading_image_path') and self.bill_of_lading_image_path:
            bill_of_lading_pdf_path = 'bill_of_lading.pdf'
            bol_link = f'https://drive.google.com/file/d/{upload_to_drive(bill_of_lading_pdf_path, folder_id)}'
            bol_subject = 'BOL Link'
            bol_email_body = f"BOL Link: {bol_link}"
            send_email(bol_subject,bol_email_body)
            os.remove(bill_of_lading_pdf_path)
        
        if hasattr(self, 'repair_receipt_paths') and self.repair_receipt_paths and hasattr(self, 'fuel_receipt_paths') and self.fuel_receipt_paths:
            fuel_links = [f'https://drive.google.com/file/d/{upload_to_drive(path, folder_id)}' for path in self.fuel_receipt_paths]
            repair_links = [f'https://drive.google.com/file/d/{upload_to_drive(path, folder_id)}' for path in self.repair_receipt_paths]
            receipts_subject = 'Fuel and Repair Receipt Links'
            fuel_email_body = "Fuel Receipt Links:\n" + "\n".join(fuel_links)
            repair_email_body = "Repair Receipt Links:\n" + "\n".join(repair_links)
            send_email(receipts_subject,fuel_email_body+'\n'+repair_email_body)
        elif hasattr(self, 'repair_receipt_paths') and self.repair_receipt_paths:
            repair_links = [f'https://drive.google.com/file/d/{upload_to_drive(path, folder_id)}' for path in self.repair_receipt_paths]
            repair_subject = 'Repair Receipt Links'
            repair_email_body = "Repair Receipt Links:\n" + "\n".join(repair_links)
            send_email(repair_subject,repair_email_body)
        elif hasattr(self, 'fuel_receipt_paths') and self.fuel_receipt_paths:
            fuel_links = [f'https://drive.google.com/file/d/{upload_to_drive(path, folder_id)}' for path in self.fuel_receipt_paths]
            fuel_subject = 'Fuel Receipt Links'
            fuel_email_body = "Fuel Receipt Links:\n" + "\n".join(fuel_links)
            send_email(fuel_subject,fuel_email_body+'\n'+repair_email_body)

        self.capture_button.text = 'Capture Bill of Lading'
        self.fuel_receipts_chooser.text = 'Select Fuel Receipts'
        self.repair_receipts_chooser.text = 'Select Repair Receipts'
        self.bill_of_lading_image_path = None
        self.fuel_receipt_paths = None
        self.repair_receipt_paths = None

def send_email(subject, body):
    sender_email = ''
    receiver_email = ''
    password = ''

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = COMMASPACE.join([receiver_email])
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp_server:
            smtp_server.ehlo()
            smtp_server.starttls()
            smtp_server.login(sender_email, password)
            smtp_server.sendmail(sender_email, receiver_email, msg.as_string())
        print(f'Email sent: {subject}')
    except Exception as e:
        print(f'Error occurred while sending email: {str(e)}')

def create_drive_folder(folder_name):
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive'])
    service = build('drive', 'v3', credentials=creds)

    folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
    folder = service.files().create(body=folder_metadata, fields='id').execute()

    folder_id = folder.get('id')
    print(f'Folder created with name "{folder_name}" and URL: "https://drive.google.com/drive/folders/{folder_id}"')
    return folder_id

def upload_to_drive(file_path, folder_id):
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive'])
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)

    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    file_id = file.get('id')
    print(f'{os.path.basename(file_path)} uploaded to Google Drive with URL: "https://drive.google.com/file/d/{file_id}"')
    return file_id

if __name__ == '__main__':
    UploadApp().run()
