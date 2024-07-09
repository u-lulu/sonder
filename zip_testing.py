import zipfile
import os
from io import BytesIO

data_dir = 'playerdata'
zip_buffer = BytesIO()

with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root,dirs,files in os.walk(data_dir):
        for file in files:
            relative_path = os.path.relpath(os.path.join(root, file), data_dir)
            zipf.write(os.path.join(root, file), arcname=relative_path)

zip_buffer.seek(0)

print(zip_buffer)