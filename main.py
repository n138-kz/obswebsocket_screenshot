import time
import json
import logging
import getpass
from sys import exit
import os
from datetime import datetime, timedelta, timezone
import pytest

if __name__ == "__main__":
    # workdir: set to current dir
    workdir = os.path.dirname(__file__).replace('\\', '/')

    # Loggerの生成（__name__を入れることで、現在のファイル名が記録される）
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # logger制御変数(Dict)
    logger_config = { 'format': {}, 'handler': {} }

    # ログフォーマット
    logger_config['format']['console'] = logging.Formatter('%(asctime)s[%(levelname)-8s]| %(message)s')
    logger_config['format']['file']    = logging.Formatter('%(asctime)s | %(levelname)-8s| %(filename)s:%(lineno)03d | %(name)s | %(message)s')
    logger_config['format']['file2']   = logging.Formatter('%(asctime)s | %(levelname)-8s| %(filename)s:%(lineno)03d | %(name)s | %(message)s')

    # ハンドラー（出力先）を作成してフォーマッターをセット
    logger_config['handler']['console'] = logging.StreamHandler()
    logger_config['handler']['console'].setFormatter(fmt=logger_config['format']['console'])
    logger_config['handler']['console'].setLevel(logging.INFO)
    logger_config['handler']['file'] = logging.FileHandler(f'{workdir}/outputlog({int(time.time())}).log', encoding='utf-8')
    logger_config['handler']['file'].setFormatter(fmt=logger_config['format']['file'])
    logger_config['handler']['file'].setLevel(logging.DEBUG)
    logger_config['handler']['file2'] = logging.FileHandler(f'{workdir}/outputlog(latest).log', encoding='utf-8', mode='w')
    logger_config['handler']['file2'].setFormatter(fmt=logger_config['format']['file2'])
    logger_config['handler']['file2'].setLevel(logging.DEBUG)

    # ハンドラー（出力先）の設定：コンソールに出力
    logger.addHandler(logger_config['handler']['console'])
    logger.addHandler(logger_config['handler']['file'])
    logger.addHandler(logger_config['handler']['file2'])

    # 起動
    logger.debug(f'Working dir: {workdir}')

    # GitHub Actions の時は何もしない（インポートチェックのみで終了）
    if os.getenv('GITHUB_ACTIONS') == 'true':
        logger.info(f'GitHub Actions detected: Skipping execution logic.')
        exit(0)

    # Load config file
    config_filename = f'{workdir}/config.json'
    config_default = {
        'meta': {
            'ctime': {
                'by': getpass.getuser(),
                'at': int(time.time()),
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
            'password': 'password',
        },
        'SaveSourceScreenshot': {
            'imageFormat': 'webp',
            'imageFilePath': f'{workdir}/Screenshot_${{source_name}}_${{time}}_.webp',
        },
    }
    logger.debug(f'Load config: {workdir}/config.json')

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
        logger.debug(f'Config loaded: {workdir}/config.json')
    except (FileNotFoundError,json.decoder.JSONDecodeError,KeyError) as err:
        logger.error(f'Config load failure: {workdir}/config.json')
        if os.path.exists(config_filename):
            logger.error(f'Config KeyError: {err}')
            import shutil
            shutil.move(
                config_filename,
                f'{config_filename}.orginal({int(time.time())}).{config_filename.split('.')[len(config_filename.split('.'))-1]}'
            )
            logger.info(f'Config Backuped: {config_filename} --> {config_filename}.orginal({int(time.time())}).{config_filename.split('.')[len(config_filename.split('.'))-1]}')
        else:
            logger.error(f'Config NotFound: {err}')
        with open(config_filename,encoding='utf8',mode='w') as fp:
            json.dump(config_default, fp, indent=4, ensure_ascii=False)
            logger.info(f'Config created: {config_filename}')
        time.sleep(1)
        exit(1)

    # OBSに接続
    from obswebsocket import obsws, requests
    ws = obsws(host, port, password)
    try:
        logger.info(f'Connecting to OBS: {host}:{port}')
        ws.connect()
    except Exception as err:
        logger.error(f'Connect Failure: {err}')
        time.sleep(1)
        exit(1)
    time_connect = int(time.time())
    logger.debug(f'Connected to OBS: at {time_connect}({datetime.fromtimestamp(time_connect, tz=timezone(timedelta(hours=9))).isoformat()})')

    version = ws.call(requests.GetVersion())
    if version.status:
        version = version.getObsVersion()
        logger.debug(f'OBS version: {version}')

    scenes = ws.call(requests.GetSceneList())
    if scenes.status:
        active_scene = scenes.getcurrentProgramSceneName()
        logger.debug(f'Active Scene: {active_scene}')

        screenshot = ws.call(requests.SaveSourceScreenshot(
            sourceName=active_scene,
            imageFormat=config_runningdata['SaveSourceScreenshot']['imageFormat'],
            imageFilePath=config_runningdata['SaveSourceScreenshot']['imageFilePath']
            .replace( '${source_name}', active_scene )
            .replace( '${time}', str(int(time.time())) )
        ))


        for scene in scenes.getScenes():
            logger.info(f'{config_runningdata['locale'][config_runningdata['locale']['lang']]['scene-name']}: {scene['sceneName']}')
            scene_name=scene['sceneName']

            sources = ws.call(requests.GetSceneItemList(sceneName=scene_name))
            for source in sources.getSceneItems():
                for i in range(0,len(config_runningdata['locale'][config_runningdata['locale']['lang']]['scene-list'])):
                    print(' ', end='')
                logger.info(f'- {config_runningdata['locale'][config_runningdata['locale']['lang']]['source-name']}: {source['sourceName']}')
                source_name=source['sourceName']

                if active_scene == scene_name and source['sceneItemEnabled']:
                    # https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#getsourcescreenshot
                    screenshot = ws.call(requests.SaveSourceScreenshot(
                        sourceName=source_name,
                        imageFormat=config_runningdata['SaveSourceScreenshot']['imageFormat'],
                        imageFilePath=config_runningdata['SaveSourceScreenshot']['imageFilePath']
                        .replace( '${source_name}', source_name )
                        .replace( '${time}', str(int(time.time())) )
                    ))
                    if screenshot.status:
                        try:
                            logger.debug(f'Caputured: {screenshot}')
                        except Exception as err:
                            for i in range(0,len(config_runningdata['locale'][config_runningdata['locale']['lang']]['scene-list'])+2):
                                print(' ', end='')
                            logger.error(f'Error: {err}')
                            for i in range(0,len(config_runningdata['locale'][config_runningdata['locale']['lang']]['scene-list'])+2):
                                print(' ', end='')
                            logger.error(f'Error: {screenshot}')

    ws.disconnect()
    logger.debug(f'Disconnected from OBS')

    time.sleep(1)
    exit(0)
