from flask import Flask
from flask import render_template
import os

def runWeb(ENVIRON):


    imagepath = os.path.join(ENVIRON['topdir'], 'static/motionImages')
    app = Flask(__name__)


    #Display list of images
    #==========================================================================================
    @app.route('/', methods=['GET'])
    def home():
        image_names = os.listdir(imagepath)
        images = ''
        for name in image_names:
            images += '<div style="text-align: center;"><img src="static/motionImages/' + name + '" > <br><br></div>'
            html = '<HTML><HEAD></HEAD><BODY><meta http-equiv="refresh" content="3" />' + images + '</BODY></HTML>'
        return html

    @app.after_request
    def add_header(r):
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        r.headers["Pragma"] = "no-cache"
        r.headers["Expires"] = "0"
        r.headers['Cache-Control'] = 'public, max-age=0'
        return r
       

    app.run(host= '0.0.0.0')



# **************************************************************************
# This will only be executed when we run the sensor on its own for debugging
# **************************************************************************
if __name__ == "__main__":
    import os
    
    ENVIRON = {}
    ENVIRON["topdir"] = os.path.dirname(__file__)

    runWeb(ENVIRON)


