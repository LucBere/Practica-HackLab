import socket
import time
import re

SERVER = 'tetris-server.shared.softwareseguro.com.ar'
PORT = 15452
NAME = 'lucas'

def main():
    print("[*] Conectando...")
    s = socket.create_connection((SERVER, PORT))
    
    name_bytes = NAME.encode('utf-8')[:30].ljust(30, b'\x00')
    s.sendall(name_bytes)
    print(f"[*] Nombre enviado: {name_bytes}")
    
    s.settimeout(0.5)
    
    points_sent = 0
    target_points = 40000
    
    print("[*] El servidor es MUY estricto con el limitador (detectó una pequeña ráfaga por latencia de red).")
    print("[*] Vamos a enviar los 400 paquetes de 100 puntos de forma más relajada.")
    print("[*] 1 paquete cada 0.35 segundos (Tardará unos 140 segundos). ¡Paciencia!")
    
    for i in range(400):
        try:
            s.sendall(bytes([100]))
            # Imprimir progreso cada 20 paquetes (5%)
            if (i + 1) % 20 == 0:
                print(f"[*] Progreso: {((i+1)//4)*100} / 40000 puntos...")
            time.sleep(0.35)
        except Exception as e:
            print(f"[!] Error enviando en paquete {i}: {e}")
            break
        
    print("[*] Esperando respuesta del servidor...")
    buf = b""
    start = time.time()
    
    while time.time() - start < 10:
        try:
            data = s.recv(1024)
            if not data:
                break
            buf += data
            print(f"Recibido: {data}")
            if b"GANASTE" in buf:
                print("\n[+] FLAG ENCONTRADA!")
                m = re.search(b'\\b[a-fA-F0-9]{32}\\b', buf)
                if m:
                    print("MD5:", m.group(0).decode())
                break
        except socket.timeout:
            pass
            
    print("[*] Cerrando socket.")
    s.close()

if __name__ == '__main__':
    main()
