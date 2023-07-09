import requests
from PIL import Image, PngImagePlugin
import io
import base64
from ftplib import FTP
import os

ftp_server = "themis.feralhosting.com"
ftp_username = "bottlecap"
ftp_password = "UjSKCglyT5YlHMml"
ftp_ai_webpage = "/media/sdq1/bottlecap/www/phixxy.com/public_html/ai-webpage/"
ftp_ai_webpage_archive = "/media/sdq1/bottlecap/www/phixxy.com/public_html/webpage-archive/"
    
def upload_html_and_imgs():
    with FTP(ftp_server) as ftp:
        ftp.login(ftp_username, ftp_password)
        ftp.cwd(ftp_ai_webpage)
        for filename in os.listdir("webpage/"):
            if ".png" in filename:
                ftp.storbinary("STOR " + filename, open("webpage/" + filename, "rb"))
        #explicitly upload html files last!
        for filename in os.listdir("webpage/"):
            if ".html" in filename:
                ftp.storbinary("STOR " + filename, open("webpage/" + filename, "rb"))
                
def upload_websites():
    with FTP(ftp_server) as ftp:
        ftp.login(ftp_username, ftp_password)
        for foldername in os.listdir("websites/"):
            ftp.cwd(ftp_ai_webpage_archive)
            if "archived.txt" not in os.listdir("websites/" +foldername):
                ftp.mkd(foldername)
                ftp.cwd(ftp_ai_webpage_archive + foldername)
                for filename in os.listdir("websites/" +foldername):
                    if ".png" in filename:
                        ftp.storbinary("STOR " + filename, open("websites/" + foldername + "/" + filename, "rb"))
                        print("Uploaded websites/" + foldername + "/" + filename)
                #explicitly upload html files last!
                for filename in os.listdir("websites/" +foldername):
                    if ".html" in filename:
                        ftp.storbinary("STOR " + filename, open("websites/" + foldername + "/" + filename, "rb"))
                        print("Uploaded websites/" + foldername + "/" + filename)
                with open("websites/" + foldername + "/" + "archived.txt","w") as f:
                    f.write("True")
                    f.close()
                    

                    
def generate_website_archive_html():
    html1 = '''<!DOCTYPE html>
<html>

<head>
	<title>webpage-archive</title>
	<style>
		body {
			background-color: #222;
			color: #fff;
			font-family: sans-serif;
			line-height: 1.6;
		}

		h1 {
			font-size: 4em;
			text-align: center;
			margin-top: 0;
		}

		p {
			font-size: 1.2em;
			text-align: justify;
			max-width: 800px;
			margin: 0 auto;
			padding: 20px;
			background: rgba(255, 255, 255, 0.1);
			border-radius: 8px;
			box-shadow: 0 0 10px rgba(0, 0, 0, 0.3);
		}

		ul {
			list-style: none;
			padding: 0;
			margin: 0;
			max-width: 800px;
			margin: 20px auto;
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
			grid-gap: 20px;
		}

		li {
			background: #444;
			padding: 10px;
			border-radius: 5px;
			box-shadow: 0 0 5px rgba(0, 0, 0, 0.3);
			transition: all 0.3s ease;
		}

		li:hover {
			transform: scale(1.1);
			box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
		}

		a {
			color: #fff;
			text-decoration: none;
		}
	</style>
</head>

<body>
	<h1>webpage-archive</h1>
	<p>This is a list of saved websites that AI generated.</p>
	<ul>\n'''
    html2 = '''	</ul>
</body>

</html>'''
    with FTP(ftp_server) as ftp:
        ftp.login(ftp_username, ftp_password)
        ftp.cwd(ftp_ai_webpage_archive)
        file_list = ftp.nlst()
        dir_list = ""
        for folder in file_list:
            if folder != "index.html":
                dir_list += "<a href=\"" + folder + "\"><li>" + folder + "</li></a>\n"
        html = html1 + dir_list + html2
        with open("index.html","w") as f:
            f.write(html)
            f.close()
        ftp.storbinary("STOR " + "index.html", open("index.html", "rb"))
        

def combine_dicts(dict1, dict2): #prioritizes dict2 args
    combined_dict = {}
    for key in dict1:
        combined_dict[key] = dict1[key]
    for key in dict2:
        combined_dict[key] = dict2[key]
    return combined_dict

def extract_image_tags(code):
    count = code.count("<img")
    tags = []
    for x in range(0,count):
        index1 = code.find("<img")
        index2 = code[index1:].find(">") + index1 + 1
        img_tag = code[index1:index2]
        tags.append(img_tag)
        code = code[index2:]
    return tags
    
def extract_image_alt_text(tags):
    alt_texts = []
    for tag in tags:
        index1 = tag.find("alt") + 5
        index2 = tag[index1:].find("\"") + index1
        alt_text = tag[index1:index2]
        alt_texts.append(alt_text)
    return alt_texts
    

def generate_images(image_list):
    file_list = []
    for image in image_list:
        filename = image.replace(" ", "").lower() + ".png"
        url = "http://127.0.0.1:7861"
        payload = {"prompt": image,"steps": 25}
        response = requests.post(url=f'{url}/sdapi/v1/txt2img', json=payload)
        r = response.json()
        for i in r['images']:
            image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[0])))
            png_payload = {"image": "data:image/png;base64," + i}
            response2 = requests.post(url=f'{url}/sdapi/v1/png-info', json=png_payload)
            pnginfo = PngImagePlugin.PngInfo()
            pnginfo.add_text("parameters", response2.json().get("info"))
            image.save("webpage/" + filename, pnginfo=pnginfo)
            file_list.append(filename)
    return file_list

def add_image_filenames(code, file_list):
    for filename in file_list:
        code = code.replace("src=\"\"", "src=\""+ filename + "\"", 1)
    return code
    
def delete_local_pngs():
    for filename in os.listdir("webpage/"):
        if ".png" in filename:
            os.remove("webpage/" + filename)
            
def delete_ftp_pngs():
    with FTP(ftp_server) as ftp:
        ftp.login(ftp_username, ftp_password)
        ftp.cwd(ftp_ai_webpage)
        file_list = ftp.nlst()
        for filename in file_list:
            if ".png" in filename:
                print("Deleting", filename)
                ftp.delete(filename)

delete_local_pngs()
delete_ftp_pngs()

    
with open("webpage/index.html", 'r') as f:
    code = f.read()
    f.close()    
        
tags = extract_image_tags(code)
alt_texts = extract_image_alt_text(tags)
file_list = generate_images(alt_texts)
code = add_image_filenames(code, file_list)
with open("webpage/index.html", 'w') as f:
    f.write(code)
    f.close()
upload_html_and_imgs()
upload_websites()
generate_website_archive_html()
print("Success")

