from time import time
from math import floor as math_floor
import json
import getpass
from sys import exit as exit
import os
workdir = os.path.dirname(__file__)

# Load config file
config_filename = workdir+'\\'+'.env'
config_default = {
    'meta': {
        'ctime': {
            'by': getpass.getuser(),
            'at': math_floor(time()),
        },
    },
    'locale': {
        'lang': 'en',
        'en': {
            'scene-list': 'Scene List',
            'scene-name': 'Scene Name',
            'source-list': 'Source List',
            'source-name': 'Source Name',
        },
        'ja': {
            'scene-list': 'シーン一覧',
            'scene-name': 'シーン名',
            'source-list': 'ソース一覧',
            'source-name': 'ソース名',
        },
    },
    'connect': {
        'host': 'localhost',
        'port': 4455,
        'password': '',
    },
    'SaveSourceScreenshot': {
        'imageFormat': 'webp',
        'imageFilePath': 'C:/Screenshot_${source_name}_${time}_.webp',
    },
}

config_runningdata = config_default
host = config_default['connect']['host']
port = config_default['connect']['port']
password = config_default['connect']['password']
try:
    with open(config_filename,encoding='utf8',mode='r') as fp:
        config_filedata = json.load(fp)
        host = config_filedata['connect']['host']
        port = config_filedata['connect']['port']
        password = config_filedata['connect']['password']
        config_runningdata = config_filedata
except FileNotFoundError as err:
    with open(config_filename,encoding='utf8',mode='w') as fp:
        json.dump(config_default, fp)

# OBSに接続
from obswebsocket import obsws, requests
ws = obsws(host, port, password)
try:
    ws.connect()
except Exception as err:
    print(err)
    exit()
time_connect = math_floor(time())

version = ws.call(requests.GetVersion())
if version.status:
    version = version.getObsVersion()

scenes = ws.call(requests.GetSceneList())
if scenes.status:
    active_scene = scenes.getcurrentProgramSceneName()

    for scene in scenes.getScenes():
        print(f""+config_runningdata['locale'][config_runningdata['locale']['lang']]['scene-name']+": "+scene['sceneName'])
        scene_name=scene['sceneName']

        sources = ws.call(requests.GetSceneItemList(sceneName=scene_name))
        for source in sources.getSceneItems():
            for i in range(0,len(config_runningdata['locale'][config_runningdata['locale']['lang']]['scene-list'])):
                print(' ', end='')
            print(f"- "+config_runningdata['locale'][config_runningdata['locale']['lang']]['source-name']+": "+source['sourceName'])
            source_name=source['sourceName']

            if active_scene == scene_name and source['sceneItemEnabled']:
                # https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#getsourcescreenshot
                screenshot = ws.call(requests.SaveSourceScreenshot(
                    sourceName=source_name,
                    imageFormat=config_runningdata['SaveSourceScreenshot']['imageFormat'],
                    imageFilePath=config_runningdata['SaveSourceScreenshot']['imageFilePath'].replace(
                        '${source_name}', source_name
                    ).replace(
                        '${time}', str(time())
                    ),
                ))
                if screenshot.status:
                    try:
                        screenshot = screenshot.getSourceName()
                    except Exception as err:
                        for i in range(0,len(config_runningdata['locale'][config_runningdata['locale']['lang']]['scene-list'])+2):
                            print(' ', end='')
                        print(type(err))
                        for i in range(0,len(config_runningdata['locale'][config_runningdata['locale']['lang']]['scene-list'])+2):
                            print(' ', end='')
                        print(f"{screenshot}")

ws.disconnect()
