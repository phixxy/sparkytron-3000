from sys import argv
import os
import time
import subprocess
#usage python3 youtubedl.py <url> <video|audio>

def download(url, video_or_audio):
    if video_or_audio == "video":
        process = subprocess.Popen(["yt-dlp", "-o", "%(playlist|)s/%(playlist_index)s - %(title)s.%(ext)s", "--yes-playlist", f"{url}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(process.stdout.read())
        process.wait()
        return True
    elif video_or_audio == "audio":
        process = subprocess.Popen(["yt-dlp", "-o", "%(playlist|)s/%(playlist_index)s - %(title)s.%(ext)s", "-x", "--yes-playlist", f"{url}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(process.stdout.read())
        process.wait()
        return True
    else:
        print("Invalid argument")
        return False
    
def zip_all_files():
    #zip all files
    current_epoch = time.time()
    output_file = f"{current_epoch}.zip"
    os.system(f"zip -r data/ytdl/{output_file} data/ytdl/*")
    return output_file
    
def upload_to_litterbox(input_file):
    '''    If you want to make curl requests to the API, here is an example. Allowed values for "time" are 1h, 12h, 24h, and 72h.
    curl -F "reqtype=fileupload" -F "time=1h" -F "fileToUpload=@cutie.png" https://litterbox.catbox.moe/resources/internals/api.php'''
    command = f"curl -F 'reqtype=fileupload' -F 'time=1h' -F 'fileToUpload=@{input_file}' https://litterbox.catbox.moe/resources/internals/api.php"
    output_url = os.popen(command).read()
    #delete all files in current directory except this script
    file_types = ["zip", "mp4", "mp3", "webm", "wav", "m4a", "flac", "ogg", "opus", "wma", "aac", "m4p", "m4b", "m4r", "m4v", "mp2", "mp3", "mp4", "mpa", "mpeg", "mpg", "mpv", "mxf", "ogg", "oga", "ogv", "ogx", "spx", "wav", "webm", "wma", "wv", "wvx", "weba", "webm", "webp", "wmv"]
    for file in os.listdir():
        if file.split(".")[-1] in file_types:
            os.remove(file)
    return output_url

def main():
    url, video_or_audio = argv[1], argv[2]
    print(url, video_or_audio)
    if download(url, video_or_audio):
        zip_file = zip_all_files()
        output_url = upload_to_litterbox(zip_file)
        print(output_url)
        with open(f"{time.time()}.txt", "w") as output_file:
            output_file.write(output_url)
            output_file.close()
    else:
        print("Invalid argument")

if __name__ == "__main__":
    main()
