from flask import Flask
from flask import render_template
import os

def runWeb(ENVIRON):

    #print(ENVIRON['topdir'])
    imagepath = os.path.join(ENVIRON['topdir'], 'static/web')
    #print(imagepath)
    #app = Flask(__name__, static_url_path=imagepath)
    app = Flask(__name__)

    #Display list of images
    #==========================================================================================
    @app.route('/', methods=['GET'])
    def home():
        image_names = os.listdir(imagepath)
        images = ''
        for name in image_names:
            images += '<div style="text-align: center;"><img src="static/web/' + name + '" > <br><br></div>'
            html = '<HTML><HEAD></HEAD><BODY><meta http-equiv="refresh" content="1" />' + images + '</BODY></HTML>'
        return html
       
    app.run()

