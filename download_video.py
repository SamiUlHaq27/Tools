import requests

def download(link, file_name):
    r = requests.get(link, stream = True)
    with open(BASE_DIR/'media'/'output'/file_name, 'wb') as f: 
        for chunk in r.iter_content(chunk_size = 1024*1024): 
            if chunk: 
                f.write(chunk) 
    return "/media/output/"+file_name
