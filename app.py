from flask import Flask, request, render_template, send_from_directory, send_file, jsonify
from moviepy.editor import VideoFileClip
import yt_dlp, os, re
from threading import Thread
from datetime import datetime
from zipfile import ZipFile

app = Flask(__name__)
SAIDA = "output"
THUMBS = "output/thumbs"
PREVIEWS = "output/previews"

os.makedirs(SAIDA, exist_ok=True)
os.makedirs(THUMBS, exist_ok=True)
os.makedirs(PREVIEWS, exist_ok=True)

progress = {"total_videos":0, "videos_done":0, "total_cortes":0, "cortes_done":0}

def process_links(links, duracao, quantidade):
    progress["total_videos"] = len(links)
    progress["videos_done"] = 0
    progress["total_cortes"] = len(links) * quantidade
    progress["cortes_done"] = 0

    for idx_link, link in enumerate(links, start=1):
        yt_dlp.YoutubeDL({'outtmpl':'live.mp4'}).download([link])
        video = VideoFileClip("live.mp4")
        video_duracao = int(video.duration)
        match = re.search(r"twitch.tv/([\w\d_]+)", link)
        streamer = match.group(1) if match else f"TwitchLive{idx_link}"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        for i in range(quantidade):
            start = i * duracao
            end = min(start + duracao, video_duracao)
            if start >= video_duracao:
                break
            clip = video.subclip(start, end)
            clip = clip.resize(height=1920)

            filename = f"{SAIDA}/{streamer}_{timestamp}_{i+1}.mp4"
            clip.write_videofile(filename, codec="libx264", audio_codec="aac")
            progress["cortes_done"] += 1

            # thumbnail
            thumb_filename = f"{THUMBS}/{streamer}_{timestamp}_{i+1}.png"
            clip.save_frame(thumb_filename, t=0)

            # mini preview 3s
            preview_clip = clip.subclip(0, min(3, clip.duration)).without_audio()
            preview_filename = f"{PREVIEWS}/{streamer}_{timestamp}_{i+1}.mp4"
            preview_clip.write_videofile(preview_filename, codec="libx264", audio=False)

        if os.path.exists("live.mp4"):
            os.remove("live.mp4")
        progress["videos_done"] += 1

@app.route("/", methods=["GET","POST"])
def home():
    files = sorted([f for f in os.listdir(SAIDA) if f.endswith(".mp4")])
    thumbs = {}
    previews = {}
    for f in files:
        thumb_file = f"thumbs/{f.replace('.mp4','.png')}"
        preview_file = f"previews/{f}"
        thumbs[f] = thumb_file if os.path.exists(os.path.join(THUMBS, f.replace('.mp4','.png'))) else None
        previews[f] = preview_file if os.path.exists(os.path.join(PREVIEWS, f)) else None

    if request.method=="POST":
        links = request.form.get("links","")
        links = [l.strip() for l in links.split(",") if l.strip()]
        duracao = int(request.form.get("duracao",25))
        quantidade = int(request.form.get("quantidade",5))
        thread = Thread(target=process_links, args=(links,duracao,quantidade))
        thread.start()

    return render_template("index.html", files=files, thumbs=thumbs, previews=previews)

@app.route("/progress")
def get_progress():
    return jsonify(progress)

@app.route("/output/<filename>")
def download_file(filename):
    return send_from_directory(SAIDA, filename)

@app.route("/output/thumbs/<filename>")
def download_thumb(filename):
    return send_from_directory(THUMBS, filename)

@app.route("/output/previews/<filename>")
def download_preview(filename):
    return send_from_directory(PREVIEWS, filename)

@app.route("/download_all")
def download_all():
    zip_path = "output/all_clips.zip"
    with ZipFile(zip_path,"w") as zipf:
        for f in os.listdir(SAIDA):
            if f.endswith(".mp4"):
                zipf.write(os.path.join(SAIDA,f), arcname=f)
    return send_file(zip_path, as_attachment=True)

if __name__=="__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)
    flask
moviepy
yt-dlp
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AutoClip Twitch → TikTok</title>
<style>
body {font-family:Arial,sans-serif;background:#1e1e2f;color:#fff;padding:20px;}
h2{text-align:center;color:#4CAF50;}
form{background:#2c2c3f;padding:15px;border-radius:10px;margin-bottom:20px;}
input[type="text"],input[type="number"]{width:100%;padding:8px;margin:5px 0 10px 0;border-radius:5px;border:none;}
input[type="submit"]{width:100%;padding:10px;background:#4CAF50;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer;}
input[type="submit"]:hover{background:#45a049;}
.progress-container{width:100%;background:#333;border-radius:10px;overflow:hidden;margin:15px 0;}
.progress-bar{width:0%;height:25px;background:#4CAF50;}
#status{text-align:center;margin-bottom:10px;}
#notification{text-align:center;font-weight:bold;color:#4CAF50;display:none;margin-bottom:10px;}
ul{list-style:none;padding:0;}
li{margin-bottom:15px;display:flex;flex-direction:column;align-items:center;}
li img{width:120px;border-radius:5px;}
li video{width:240px;border-radius:5px;margin-top:5px;}
li a{margin-top:5px;color:#4CAF50;font-weight:bold;text-decoration:none;}
li a:hover{text-decoration:underline;}
</style>
<script>
let finished=false;
function updateProgress(){
    fetch('/progress').then(res=>res.json()).then(data=>{
        let total_cortes = data.total_cortes || 1;
        let cortes_done = data.cortes_done;
        let perc = (cortes_done/total_cortes)*100;
        document.getElementById("progress").style.width = perc+"%";
        document.getElementById("status").innerText = `Vídeos processados: ${data.videos_done}/${data.total_videos} | Cortes feitos: ${cortes_done}/${total_cortes}`;
        if(cortes_done>=total_cortes && !finished){
            finished=true;
            document.getElementById("notification").style.display="block";
            alert("🎉 Todos os cortes foram gerados!");
        }
    });
}
setInterval(updateProgress,2000);
</script>
</head>
<body>
<h2>AutoClip Twitch → TikTok</h2>
<form method="post">
<label>Links da Twitch (separados por vírgula):</label>
<input type="text" name="links" placeholder="https://twitch.tv/streamer1, https://twitch.tv/streamer2">
<label>Duração de cada clipe (s):</label>
<input type="number" name="duracao" value="25">
<label>Quantidade de cortes:</label>
<input type="number" name="quantidade" value="5">
<input type="submit" value="Gerar Cortes">
</form>

<div class="progress-container">
<div id="progress" class="progress-bar"></div>
</div>
<p id="status">Aguardando...</p>
<p id="notification">✅ Todos os cortes foram gerados!</p>

<hr>
<h3>Clipes gerados:</h3>
<ul>
{% for f in files %}
<li>
    {% if thumbs[f] %}
    <img src="/output/{{thumbs[f].split('/')[-1]}}" alt="Thumb">
    {% endif %}
    {% if previews[f] %}
    <video src="/output/{{previews[f].split('/')[-1]}}" muted loop autoplay playsinline></video>
    {% endif %}
    <a href="/output/{{f}}" target="_blank">{{f}}</a>
</li>
{% endfor %}
</ul>

<a href="/download_all" style="display:inline-block;padding:10px 20px;background:#4CAF50;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold;">📥 Baixar Todos</a>
</body>

</html>
