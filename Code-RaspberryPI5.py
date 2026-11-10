#Ce code a été codé dans un premier temps sans IA puis avec pour l'optimisation du threading, gestion des queues.


#!/usr/bin/env python3

time.sleep(10)  #Attente que la Raspberry PI soit bien démarré 

import serial
import time
import threading
from queue import Queue
import os
import datetime as dt
import glob
import shutil
import csv


#Variables partagées protégées
lock = threading.Lock()

current_weight = 0.0
current_name = ""
current_uid = ""
last_rfid_time = 0
wght_name = ""
data_queue = Queue()

LOCAL_FILE = "/home/ouistiti/poids_local.csv"

# CONFIGURATION PORTS
reader_port = '/dev/serial/by-id/usb-Microchip_Technology_Inc._MCP2200_USB_Serial_Port_Emulator_0012594550-if00'
arduino_port = '/dev/serial/by-id/usb-Arduino__www.arduino.cc__0043_95730333837351F03170-if00'
HC05_port = '/dev/rfcomm0'

reader = serial.Serial(reader_port, 9600, timeout=0.1)
arduino = serial.Serial(arduino_port, 9600, timeout=0)
bt = serial.Serial(HC05_port, 9600)

time.sleep(2)
bt.reset_input_buffer()

print("Système démarré")

#DICTIONNAIRE RFID
rfid_dict = {
    "900046000308136": "Test",
    "XXXXXXXXXXXXXXX": "Leni",
    "YYYYYYYYYYYYYYY": "Jobert",
    "ZZZZZZZZZZZZZZZ": "Ocarina",
	...
    
}

#SAUVEGARDE LOCALE CSV
def save_local(name, weight, date, uid):
    try:
        file_exists = os.path.exists(LOCAL_FILE)
        with open(LOCAL_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Nom", "Poids", "Heure", "RFID"])
            writer.writerow([name, weight, date, uid])
    except Exception as e:
        print("Erreur sauvegarde locale:", e)

#COPIE USB : Recherche si une clé USB est branché
usb_path = None
try:
    possible_paths = glob.glob("/media/*/*")
    for path in possible_paths:
        if os.path.isdir(path) and os.access(path, os.W_OK):
            usb_path = path
            print("USB détectée :", usb_path)
except:
    usb_path = None

def copy_to_usb():
    if usb_path is None:
        return
    try:
        usb_file = os.path.join(usb_path, "poids.csv")
        temp_file = usb_file + ".tmp"
        shutil.copy2(LOCAL_FILE, temp_file)
        os.rename(temp_file, usb_file)
        os.sync()
    except Exception as e:
        print("Erreur copie USB:", e)

#THREAD LECTURE POIDS: Lecture des données envoyées par la carte Arduino via la module HC-05 en Bluetooth
#Un petit peu instable
def serial_reader():
    global current_weight

    while True:
        try:
            bt.reset_input_buffer()
            line = bt.readline().decode().strip()

            if line:
                weight = float(line)

                with lock:
                    current_weight = weight
                    name = current_name
                    uid = current_uid

                # Sauvegarde uniquement si poids valide
                if weight > 0:
                    now = dt.datetime.now()
                    if wght_name != "Inconnu" : 
                        save_local(wght_name, weight, now, uid)
                        copy_to_usb()

        except ValueError:
            pass

        time.sleep(0.05)

#THREAD RFID : Récupération des numéros de puces
def uid_reader():
    global current_name, current_uid, last_rfid_time,wght_name

    buffer = ""

    while True:
        if reader.in_waiting:
            data = reader.read(reader.in_waiting).decode('utf-8', errors='ignore')
            buffer += data

            for sep in [';', '\r', '\n']:
                buffer = buffer.replace(sep, '\n')

            parts = buffer.split('\n')

            if not buffer.endswith('\n'):
                buffer = parts.pop(-1)
            else:
                buffer = ""

            for part in parts:
                part = part.strip()

                if len(part) == 15 and part.isdigit():
                    uid = part
                    name = rfid_dict.get(uid, "Inconnu")
                    if name != "Inconnu":
                        wght_name = name
                    elif name == "Inconnu":
                        wght_name = "Inconnu"

                    with lock:
                        current_name = name
                        current_uid = uid
                        last_rfid_time = time.time()

                    print(f"RFID détecté : {name}")

        time.sleep(0.05)


#THREAD ENVOI ARDUINO LCD
def sender_thread():
    global current_name

    while True:

        with lock:
            weight = current_weight
            name = current_name
            last_time = last_rfid_time

        # Gestion timeout 4 secondes
        if name != "" and (time.time() - last_time > 4):
            with lock:
                current_name = ""
            name = ""

        # Envoi cohérent via Queue
        if data_queue.qsize() < 2:
            data_queue.put((weight, name))

        if not data_queue.empty():
            weight_send, name_send = data_queue.get()
            msg = f"{weight_send};{name_send}\n"
            arduino.write(msg.encode())

        time.sleep(0.2)

#LANCEMENT THREADS
threading.Thread(target=serial_reader, daemon=True).start()
threading.Thread(target=uid_reader, daemon=True).start()
threading.Thread(target=sender_thread, daemon=True).start()


#BOUCLE PRINCIPALE
while True:
    time.sleep(1)
