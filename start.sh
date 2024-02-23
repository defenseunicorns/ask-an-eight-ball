
# python -m venv venv  
rm -rf db xx.log
source venv/bin/activate > /dev/null && pip install -r requirements.txt > /dev/null
python main.py > xx.log
