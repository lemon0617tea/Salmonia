Skip to content
Search or jump to…
Pull requests
Issues
Marketplace
Explore
 
@lemon0617tea 
tkgstrator
/
Salmonia
Public
2
69
Code
Issues
Pull requests
Actions
Projects
Wiki
Security
Insights
Salmonia/Salmonia.py /
@PapaSpiff
PapaSpiff keep only one version
Latest commit cca53d8 2 days ago
 History
 5 contributors
@PapaSpiff@tkgstrator@GungeeSpla@sasagar@yukidaruma
239 lines (208 sloc)  8.11 KB
   
# -*- coding: utf-8 -*-
import sys
import json
import os
import webbrowser
import re
import requests
from datetime import datetime
from time import sleep
from more_itertools import chunked
import iksm
import glob

LANG = "en-US"
URL = "https://salmon-stats.yuki.games/"


# 時刻付きでログを表示する
def Log(str):
    print(f'{datetime.now().strftime("%H:%M:%S")} {str}')


def CLog(str):
    print(f'\r{datetime.now().strftime("%H:%M:%S")} {str}', end="")


# ファイルまでのパスを返す
def FilePath(file):
    return f"{os.path.dirname(os.path.abspath(sys.argv[0]))}/{file}"


def JsonPath(file):
    return f"{os.path.dirname(os.path.abspath(sys.argv[0]))}/json/{file}.json"


class Salmonia():
    # クラス変数を初期化
    # nsa_id = None
    iksm_session = None
    session_token = None
    api_token = None
    job_num = {"splatnet2": 0, "salmonstats": 0}
    api_errors = 0

    def __init__(self):
        Log(f"Salmonia version {iksm.version}")
        Log("Thanks @Yukinkling and @barley_ural!")
        self.initConfig()
        
    def initConfig(self):
        try:
            with open(FilePath("config.json"), mode="r") as f:  # 設定ファイルがある場合
                params = json.load(f)
                # Log(params)
                self.iksm_session = params["iksm_session"]
                self.session_token = params["session_token"]
                self.api_token = params["api-token"]
                self.job_num = params["job_num"]
                if "json" not in os.listdir():
                    Log("Make JSON Directory")
                    os.mkdir("json")
                return
        except FileNotFoundError:  # 設定ファイルがない場合
            Log("config.json is not found")
            self.login()
        except json.decoder.JSONDecodeError:  # 設定ファイルのフォーマットがおかしい場合
            Log("config.json is broken")
            self.login()
        except Exception as error:
            Log(f"Fatal Error {error}")

    # ログインと設定ファイル生成
    def login(self):
        Log("Log in, right click the \"Select this account\" button, copy the link address, and paste it below:")
        webbrowser.open(iksm.log_in())
        while True:
            try:
                url_scheme = input("")
                session_token_code = re.search("de=(.*)&", url_scheme).group(1)
                self.session_token = iksm.get_session_token(session_token_code)
                self.iksm_session = iksm.get_cookie(self.session_token)
                Log("Success")
                break
            except KeyboardInterrupt:
                CLog("Keyboard Interrupt")
                sys.exit(1)
            except AttributeError:
                CLog("Invalid URL")
            except KeyError:
                CLog("Invalid URL")
            except ValueError as error:
                CLog(f"{error}")
                sys.exit(1)
        webbrowser.open(URL)
        Log("Login and Paste API token")
        while True:
            try:
                api_token = input("")
                if len(api_token) == 64:
                    try:
                        int(api_token, 16)
                        self.api_token = api_token
                        Log("Success")
                        break
                    except ValueError:
                        Log("Paste API token again")
                else:
                    Log("Paste API token again")
            except KeyboardInterrupt:
                Log("Bye Bye")
                sys.exit(1)
            except Exception as error:
                Log(f"{error}")
                sys.exit(1)
        self.output()  # 設定ファイル書き込み

    # 設定ファイル書き込み
    def output(self):
        with open("config.json", mode="w") as f:
            data = {
                "iksm_session": self.iksm_session,
                "session_token": self.session_token,
                "api-token": self.api_token,
                "job_num": self.job_num,
                "api_errors": self.api_errors
            }
            json.dump(data, f, indent=4)

    def update(self):
        try:
            Log("Iksm Session regenerating")
            self.iksm_session = iksm.get_cookie(self.session_token)
            self.output()
        except Exception as ex:
            Log("Session Cookie Error")
            for i in range(5):
                try:
                    sleep(120)
                    Salmonia.initConfig(self)
                    self.iksm_session = iksm.get_cookie(self.session_token)
                    self.output()
                    return
                except Exception as nex:
                    Log(f"Session Cookie Error (try {i})")
            raise ValueError("Invalid session_token")

    def getJobId(self):
        url = "https://app.splatoon2.nintendo.net/api/coop_results"
        response = requests.get(url, cookies=dict(
            iksm_session=self.iksm_session)).json()
        return int(response["summary"]["card"]["job_num"])

    def getResultFromSplatNet2(self):
        try:
            present = self.getJobId()
        except Exception as error:
            self.update()
            return

        preview = max(self.job_num["splatnet2"], present - 49, int(self.job_num["salmonstats"]))

        if present == preview:
            return

        try:
            for job_num in range(preview + 1, present + 1):
                Log(f"Result {job_num} downloading")
                url = f"https://app.splatoon2.nintendo.net/api/coop_results/{job_num}"
                response = requests.get(url, cookies=dict(
                    iksm_session=self.iksm_session)).text
                with open(JsonPath(job_num), mode="w") as f:
                    f.write(response)
        except Exception as error:
            self.update()
            return
         
        upload_error = False
        for i in range(5):            
            try:
                self.allResultToSalmonStats(range(preview + 1, present + 1))
                upload_error = False
                break
            except Exception as error:
                CLog(f"Upload error")
                upload_error = True
                sleep(5)
        if upload_error:
            return
        
        self.job_num["splatnet2"] = present


    # 起動時にJSONフォルダ内の未アップロードのリザルトを全てアップロード

    def allResultToSalmonStats(self, local=None):
        url = "https://salmon-stats-api.yuki.games/api/results"
        header = {"Content-type": "application/json",
                  "Authorization": "Bearer " + self.api_token}

        # Salmon Statsの最新アップロード以上のIDのリザルトを取得
        if local == None:
            path = "json/*.json"
            lists = glob.glob(path, recursive=True)
            results = list(chunked(filter(lambda f: int(f) > self.job_num["salmonstats"], list(map(lambda f: f[5:-5], lists))), 10))
        else:
            results = list(chunked(local, 10))

        for result in results:
            data = list(filter(lambda fe: "message" not in fe, list(
                map(lambda f: json.load(open(JsonPath(f), mode="r")), result))))
            if len(data) == 0:
                continue
            response = requests.post(url, data=json.dumps(
                {"results": data}), headers=header)

            # ログを表示
            for response in json.loads(response.text):
                try:
                    Log(f"{response['job_id']} -> {response['salmon_id']} uploading")
                except Exception as error:
                    Log(f"Error: {error}")
                # アップロードした最後のIDを更新
                self.job_num["salmonstats"] = int(max(result))
            sleep(5)


if __name__ == "__main__":
    try:
        user = Salmonia()
        user.allResultToSalmonStats()
        while True:
            CLog("Waiting New Results")
            user.getResultFromSplatNet2()
            user.output()  # 設定ファイルを更新
            sleep(5)
    except KeyboardInterrupt:
        CLog("Keyboard Interrupt")
    except Exception as error:
        Log(error)
© 2021 GitHub, Inc.
Terms
Privacy
Security
Status
Docs
Contact GitHub
Pricing
API
Training
Blog
About
Loading complete
