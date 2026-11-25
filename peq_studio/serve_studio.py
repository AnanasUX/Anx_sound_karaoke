import http.server
import socketserver
import socket
import webbrowser
import os
import sys

PORT = 8080

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        directory = os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format, *args):
        # Clean logging
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

def run():
    local_ip = get_local_ip()
    url_local = f"http://localhost:{PORT}"
    url_network = f"http://{local_ip}:{PORT}"

    print("=" * 70)
    print("   ACOUSTIC PARAMETRIC EQ (PEQ) & RTA CALIBRATION STUDIO")
    print("   Chạy hiệu chuẩn âm học loa & Xuất cấu hình MVSilicon DSP")
    print("=" * 70)
    print(f"[*] Máy tính (Desktop/Laptop):   {url_local}")
    print(f"[*] Điện thoại (Phone / Wi-Fi):  {url_network}")
    print("=" * 70)
    print(">>> Bạn có thể mở link trên điện thoại (cùng mạng Wi-Fi) để cân chỉnh!")
    print(">>> Nhấn Ctrl+C để dừng máy chủ.")
    print("=" * 70)

    try:
        webbrowser.open(url_local)
    except Exception:
        pass

    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nĐã tắt máy chủ PEQ Studio.")

if __name__ == "__main__":
    run()
