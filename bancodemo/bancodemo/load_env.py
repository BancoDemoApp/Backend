import os

def load_env_file(filepath=".env"):
    if not os.path.exists(filepath):
        return
    
    with open(filepath) as f:
        for line in f:
            if line.strip() == "" or line.strip().startswith("#"):
                continue
            key, value = line.strip().split("=",1)
            os.environ.setdefault(key, value)