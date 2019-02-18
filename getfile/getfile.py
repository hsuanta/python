#!/usr/bin/env python
# coding: utf-8

import os
import json
import time
from flask import Flask,jsonify,request

path = '/root'
app = Flask(__name__)

# index package
@app.route('/')
def index():
    return "WELCOME!!!"

# get all files info
@app.route('/filesInfo', methods=['GET'])
def getFilesPath():
    return jsonify({'data': getAllFilesInfo(path)})

# convert time tuple to string according to format specification
def convertTime(timestamp):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

def getFileInfo(file):
    list = []
    fileStats = os.stat(file)
    fileInfo = {
    'Size': fileStats.st_size,
    'LastModified': convertTime(fileStats.st_mtime),
    'LastAccessed': convertTime(fileStats.st_atime),
    'CreationTime': convertTime(fileStats.st_ctime),
    'Mode': fileStats.st_mode
    }
    list.append( fileInfo )
    return list

def getAllFilesInfo(Path):
    if not os.path.exists(Path):
        return('no such file or directory.')
    list = []
    for f in os.listdir(path):
        list.append({'name': f, 'fileInfo': getFileInfo(os.path.abspath(f))})
    return list

@app.route("/filesInfo/<Path>",methods=['GET'])
def getSubDirFilesInfo(Path):
    if not os.path.exists(Path):
        return jsonify({'error':'no such file or directory.'})
    return jsonify({'data': getFileInfo(Path)})

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=1080,debug=True)

