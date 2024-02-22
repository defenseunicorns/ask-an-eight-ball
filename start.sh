
# python -m venv venv  
rm -f log.txt 2> /dev/null
source venv/bin/activate > /dev/null && pip install -r requirements.txt > /dev/null
python main.py 
