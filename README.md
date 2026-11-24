# Aurora para Telegram

Aurora analiza selfies, estima la forma del rostro y la paleta de color, y conversa sobre estilo. Usa el bot que ya creaste con BotFather. La aplicación se ejecuta en tu equipo y consulta Telegram mediante polling.

## Iniciar desde Visual Studio en Windows

1. Instala Python 3.12 de 64 bits. Descomprime el ZIP y abre la carpeta `aurora-telegram` en Visual Studio con **Archivo → Abrir → Carpeta**.
2. Abre una terminal PowerShell en esa carpeta y ejecuta:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   Copy-Item .env.example .env
   notepad .env
   ```

3. En `.env`, reemplaza `REEMPLAZA_CON_TU_TOKEN` por el token que te dio **@BotFather**. Guárdalo en tu equipo y conserva el archivo privado.
4. Inicia Aurora:

   ```powershell
   .\.venv\Scripts\python.exe bot.py
   ```

5. Abre **el chat de tu bot** en Telegram y envíale `/start`. Elige modo y envía una selfie de frente. Puedes preguntarle «¿Qué corte me recomiendas para una entrevista?».

Deja el programa en ejecución mientras quieras que Aurora responda. Usa una sola instancia con ese token. Si el mismo bot estaba conectado a otro programa, detenlo antes de iniciar Aurora.

## Perfil del bot

En **@BotFather** puedes usar `/setuserpic` para cargar `foto-perfil-aurora.png` y `/setdescription` para cambiar su descripción.

> ¡Hola! Soy Aurora, tu asistente de imagen personal. Envíame una selfie y te ayudaré a explorar la forma de tu rostro, tu paleta de colores y opciones de estilo que vayan contigo. ✨

## Uso y datos

- `/modo` cambia el tipo de recomendaciones. `/informe` vuelve a mostrar el análisis y `/borrar` elimina el informe de la memoria de Aurora.
- Envía JPEG, PNG o WebP de hasta 8 MB, como foto o archivo. Si Telegram comprime demasiado la foto, envíala como archivo.
- Aurora procesa la imagen en memoria. Los informes se conservan hasta una hora y se pierden al detener el proceso. Los mensajes y fotos que ves en Telegram se pueden eliminar desde el chat.
- Los modelos de MediaPipe vienen incluidos en `models/`. Si necesitas restaurarlos, ejecuta `download_models.py` con el intérprete del entorno virtual.
- La forma facial y la estación son estimaciones por reglas. La calidad de la foto, la iluminación y el maquillaje pueden cambiar el resultado.
