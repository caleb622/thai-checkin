"""
本地瓦片代理服务器
用途：在国内网络环境下代理 CartoDB / OpenStreetMap 瓦片，前端将瓦片 URL 指向本机 localhost:8765
启动方式：python tileserver_proxy.py
前端用法：在 Settings 中将瓦片源选为"本地代理"后，地图瓦片改为 http://localhost:8765/{z}/{x}/{y}
"""
import http.server
import urllib.request
import urllib.error
import ssl
import os

PORT = 8765
TILE_URL = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
SUBDOMAINS = ["a", "b", "c", "d"]
MAX_RETRIES = 3

class TileProxy(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # 解析路径: /z/x/y 或 /z/x/y.png
        path = self.path.lstrip("/").replace(".png", "")
        parts = path.split("/")
        if len(parts) != 3:
            self.send_error(404)
            return
        try:
            z, x, y = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            self.send_error(400)
            return

        for attempt in range(MAX_RETRIES):
            s = SUBDOMAINS[attempt % len(SUBDOMAINS)]
            url = TILE_URL.replace("{s}", s).replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y)).replace("{r}", "")
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TileProxy/1.0"
                })
                ctx = ssl.create_default_context()
                with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                    data = resp.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    print(f"  OK  {url}")
                    return
            except Exception as e:
                print(f"  RETRY {attempt+1}/{MAX_RETRIES} {url}: {e}")
        self.send_error(502)

    def log_message(self, format, *args):
        pass  # 抑制默认日志

if __name__ == "__main__":
    print(f"瓦片代理启动 → http://localhost:{PORT}")
    print("前端地图瓦片源 URL: http://localhost:{0}/{{z}}/{{x}}/{{y}}".format(PORT))
    print("按 Ctrl+C 停止")
    server = http.server.HTTPServer(("0.0.0.0", PORT), TileProxy)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        server.server_close()
