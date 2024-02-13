import os

async def folder_setup() -> None:
    folder_names = ["tmp", "extensions", "data", "logs"]
    for folder_name in folder_names:
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)

async def delete_all_files(path: str) -> None:
    for filename in os.listdir(path):
        if os.path.isfile(path+filename):
            os.remove(path+filename)
