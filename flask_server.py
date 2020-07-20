from PIL import Image
from flask import Flask,render_template,request,abort,Response
import TempleImagesNN
import json
import os
import sys
import base64
import traceback
from io import BytesIO
import cv2
import numpy as np


app = Flask(__name__)



@app.route('/training', methods=['GET','POST'])
def get_training_data():
    if (request.method=='GET'):
        return render_template("training_form.html")

    elif (request.method == 'POST'):
        form=request.form

        print(form['config_file'])
        trainer=TempleImagesNN.TempleNNTrainer(str(form['config_file']))

        return render_template("training_done.html",trainer=trainer)


@app.route('/prediction',methods=['GET','POST'])
def prediction():
    if (request.method=='GET'):
        return render_template("get_query.html")

    elif (request.method=='POST'):
        form=request.form

        print("Query file is",form['query_file'])
        predictor=TempleImagesNN.TempleImagesPredictor()
        predictor.parse_query_file(str(form['query_file']))
        response=predictor.predict()

        return render_template('prediction_done.html',classes=response)


@app.route('/api/save_data',methods=['POST'])
def add_data():
    response={"error_msg":"All OK"}
    try:
        global config
        if (request.method=='POST'):
            request_json=request.get_json()
            temple_id = str(request_json["temple_id"])
            train_test=str(request_json["train_test"])
            category=str(request_json["category"])

            imgdata = base64.b64decode(request_json["image"])
            filetype_str = request_json["image_type"].strip('.')
            image_name=str(request_json["image_name"])
            filename = image_name + '.' + filetype_str

            base=config["training_data_path"] if train_test.lower()=="train" else config["testing_data_path"]
            wd = os.path.join(base, temple_id, category)
            if(not os.path.isdir(wd)):
                os.makedirs(wd)
            filepath=os.path.join(wd,filename)

            with open(filepath, 'wb') as f:
                f.write(imgdata)

        return(Response(response=json.dumps(response),status=200))
    except Exception as e:
        error_traceback=traceback.format_exc()
        print(error_traceback)
        response["error_msg"]=str(e)
        return(Response(response=json.dumps(response),status=500))



    pass

@app.route('/api/make_model',methods=['POST'])
def train_model():
    global config
    if (request.method == 'POST'):
        response={"error_msg":["All OK"],
                  "got_training_data_flag" : False,
        "made_model_architecture_flag" : False,
        "trained_model_flag" : False,
        "got_testing_data_flag" : False,
        "tested_model_flag" : False,
        "saved_model_flag" : False
        }
        try:
            request_json=request.get_json()
            trainer=TempleImagesNN.TempleNNTrainer()
            trainer.set_paths(temple_id=request_json["temple_id"],
                              model_path=config["models_path"],
                              training_data_path=config["training_data_path"],
                              testing_data_path=config["testing_data_path"],
                              log_path=config["logs_path"],
                              forceful=request_json["forceful"])

        except Exception as e:
            print("Exception occured",e)
            return(Response(response=json.dumps(response),status=400))

        trainer.start_training()
        response["error_msg"]=[str(error) for error in trainer.last_error]
        response["got_training_data_flag"]=trainer.got_training_data_flag
        response["made_model_architecture_flag"]=trainer.made_model_architecture_flag
        response["trained_model_flag"]=trainer.trained_model_flag
        response["got_testing_data_flag"]=trainer.got_testing_data_flag
        response["tested_model_flag"]=trainer.tested_model_flag
        response["saved_model_flag"]=trainer.saved_model_flag

        return(Response(response=json.dumps(response),status=200 if len(response["error_msg"])==0 else 500))






@app.route('/api/predict',methods=['GET','POST'])
def predict_json_request():
    global config
    if(request.method=='POST'):
        request_json=request.get_json()

        temple_id = request_json["temple id"]
        bbuf = BytesIO()
        bbuf.write(base64.b64decode(request_json["image"]))
        pimg = Image.open(bbuf)
        image_name = request_json["image_name"]
        image = cv2.cvtColor(np.array(pimg), cv2.COLOR_RGB2BGR)
        data = []
        image_names=[]
        image_names.append(image_name)
        data.append(image)


        predictor=TempleImagesNN.TempleImagesPredictor()
        predictor.set_paths(path_to_models=config["models_path"],log_path=config["logs_path"],image_names=image_names,images=data,temple_id=temple_id)
        #predictor.parse_query_json(request.get_json())
        response=predictor.predict()
        if len(response["error_msg"])!=0:
            return(Response(response=json.dumps(str(response)),status=400))
        else:
            return(Response(response=json.dumps(str(response)),status=200))


config={}

def parse_config_json(config_file_path):
    global config
    # Opening and reading contents of file as json
    with open(config_file_path, 'r') as config_file:
        config_json = json.load(config_file)

    # Now we have the json file. We'll set the attributes accordingly
    config["training_data_path"]=config_json["training_data_path"]
    config["testing_data_path"]=config_json["testing_data_path"]
    config["models_path"]=config_json["models_path"]
    config["logs_path"]=config_json["logs_path"]

def check_directories():
    global config

    check=True
    for paths in config:
        if not os.path.isdir(config[paths]):
            check=False
            break

    return(check)

if __name__=='__main__':

    path_to_config="E:\\PS1 SMARTi electronics\\Programs and Data\\DockerDirectoryStructure\\config\\config.txt"
    #Check if config file exists in specified path
    if not os.path.isfile(path_to_config):
        print("Config file doesnt exist. Exiting")
        sys.exit()

    else:
        parse_config_json(path_to_config)

    #Checking for presence of directories
    check=check_directories()
    if check==False:
        print("All directories not present. Exiting")
        sys.exit()

    app.run(debug=True)