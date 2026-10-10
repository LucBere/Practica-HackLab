# 🕵️‍♂️ Repo Filtrado - Write-up

## 🎯 Objetivo
El objetivo del desafío es analizar un volcado (dump) del repositorio de código backend del sistema `InventApp`, recuperado tras una filtración de datos (data breach) a un proveedor de backups. Aunque los desarrolladores declararon haber eliminado las credenciales, debemos encontrar el `ACCESS_TOKEN` original para obtener la flag.

## 🔍 Análisis y Reconocimiento
Al descargar el archivo `inventapp-backend_BACKUP-OCT2026.zip` y descomprimirlo, nos encontramos con un repositorio de código que incluye su respectiva carpeta oculta `.git`.

Esto es fundamental: en los sistemas de control de versiones como Git, **borrar un archivo en un commit nuevo no elimina su contenido del historial**.

Para rastrear todas las modificaciones y parches aplicados al código, nos situamos en la raíz del repositorio y ejecutamos el siguiente comando para ver el historial de cambios en formato de diferencias (patch):

```bash
git log -p
```

## 🐛 Vulnerabilidad: Information Disclosure (Fuga de Información)
Al revisar el historial de commits, localizamos el error exacto:

1. **El Error (`commit 781c6986...`)**:
   La desarrolladora Sofía Ruiz agregó soporte para variables de entorno usando `dotenv`, pero cometió el error de comitear el archivo `.env` completo, exponiendo las credenciales de producción.
   ```diff
   +# Configuración local
   +PORT=3000
   +NODE_ENV=development
   +DB_PATH=data/db.json
   +ADMIN_TOKEN=c856b38c728fc37cbb376bfe4c58d028
   ```

2. **El (Falso) Arreglo (`commit 3c9c33ae...`)**:
   Días después, Lucía Fernández notó el problema, eliminó el archivo `.env` del repositorio y lo reemplazó con un `.env.example`. Además, dejó un aviso en el archivo `README.md` pidiendo al equipo que soliciten las credenciales por fuera.
   ```diff
   -ADMIN_TOKEN=c856b38c728fc37cbb376bfe4c58d028
   ```

Sin embargo, como el historial no fue purgado ni reescrito, el token original quedó guardado para siempre en la base de datos de Git.

## 🚩 Flag Obtenida
La flag corresponde al token recuperado del historial:

**`c856b38c728fc37cbb376bfe4c58d028`**

## 🛡️ Remediación (Defensa)
Para evitar y corregir verdaderamente este tipo de fugas de información:
1. **Prevención**: Siempre agregar los archivos sensibles (como `.env`, `.pem`, `.key`, `.json` con credenciales) al archivo `.gitignore` **antes** de hacer el primer commit. Utilizar herramientas como `git-secrets` o `trufflehog` en las pipelines de CI/CD para bloquear commits que contengan secretos.
2. **Corrección adecuada**: Si un secreto se sube por error, **borrarlo en el siguiente commit no sirve de nada**. Se debe:
   - **Invalidar/Rotar el secreto inmediatamente** en la plataforma correspondiente (AWS, base de datos, etc.) ya que se considera comprometido.
   - Purgar el secreto del historial de Git reescribiendo el árbol con herramientas especializadas como `git filter-repo` o `BFG Repo-Cleaner`.
