import base64
import json
import random
import uuid
from datetime import datetime
from typing import Dict , Union , List

import websocket

from util.charts import Charts , decode_NDArray
from util.logs import Logs

PREVIOUS_MSG_TYPE = None
CHART_DATA = None
TICKER_ID = None
Window_ID = None
ButtonClick_ID = None
Variable_Data: Dict = {}
Ws: websocket.WebSocketApp = None

LIST_WANT_WINDOW = ["1D" , "1W" , "12W" , "26W" , "1Y" , "3Y"]
GRAPH_COLOR: Dict[str , str] = {
    "all orders": "BLUE" ,
    "$100 < i < $1k": "ORANGE" ,
    "$1k < i < $10k": "GREEN" ,
    "$10k < i < $100k": "RED" ,
    "$100k < i < $1M": "PURPLE" ,
    "$1M < i < $10M": "BROWN" ,
}
LIST_WANT_COLOR = ["BLUE" , "ORANGE" , "GREEN" , "RED" , "PURPLE" , "BROWN"]

# 여기서 원하는 입력값을 사용하면 됩니다.
WANT_TICKER = "BTC_USDT"
WANT_WINDOW = "1D"
WANT_COLOR = ["BLUE" , "ORANGE"]

assert WANT_WINDOW in LIST_WANT_WINDOW , f"{LIST_WANT_WINDOW} 내에서만 Window를 설정할 수 있습니다."
assert all(color in LIST_WANT_COLOR for color in WANT_COLOR) , f"{LIST_WANT_COLOR} 내에서만 Color 설정을 할 수 있습니다."
log = Logs(__file__)


class MessageHandler:
    chart_data: Dict[str , List[Dict[str , float]]]


class WebsocketHandler:
    def generate_websocket_key(self) -> str:
        websocket_key = uuid.uuid4().bytes
        return base64.b64encode(websocket_key).decode('utf-8')

    def generate_msgid(self):
        t = [""] * 32
        for e in range(32):
            t[e] = "0123456789ABCDEF"[random.randint(0 , 15)]
        t[12] = "4"
        t[16] = "0123456789ABCDEF"[(int(t[16] , 16) & 0x3) | 0x8]
        return "".join(t)

    def on_ping(self , message: str):
        log.info(msg=f'on_ping({message})')

    def on_pong(self , message: str):
        log.info(msg=f'on_pong({message})')

    def on_message(self , ws: websocket.WebSocketApp , message: str):
        global PREVIOUS_MSG_TYPE , TICKER_ID , Window_ID , CHART_DATA , ButtonClick_ID , Ws , Variable_Data
        data: Union[Dict , None] = self.parse_message(data=message)

        if data is not None:
            if data.get("msgtype" , None) == 'ACK':
                PREVIOUS_MSG_TYPE = data['msgtype']

                msgid: str = data['msgid']
                doc_req: Dict[str , str] = {
                    "msgid": self.generate_msgid() ,
                    "msgtype": "PULL-DOC-REQ"
                }
                ws.send(data=json.dumps(doc_req))
                [ws.send(data=json.dumps({})) for _ in range(2)]

            elif data.get("msgtype" , None) == "PULL-DOC-REPLY" or PREVIOUS_MSG_TYPE == 'PULL-DOC-REPLY':
                if data.get('msgtype') is not None:
                    PREVIOUS_MSG_TYPE = data['msgtype']

                else:
                    if data.get('doc') is not None:
                        CHART_DATA = data
                        for reference in data['doc']['roots']['references']:

                            if reference['attributes'].get('title') == 'Ticker':
                                TICKER_ID = reference['id']

                            elif reference['attributes'].get('title') == 'Window':
                                Window_ID = reference['id']

                            elif reference['attributes'].get('label' , None) == 'Load / Reload':
                                ButtonClick_ID = reference['id']

                            if TICKER_ID is not None and Window_ID is not None and ButtonClick_ID is not None:
                                Ws = ws

                                print(f"모델 데이터를 전송합니다 Ticker_ID: {TICKER_ID}, Window_ID: {Window_ID}, ")

                                # 티커 변경
                                data: Dict = {
                                    "events": [
                                        {
                                            "kind": "ModelChanged" ,
                                            "model": {
                                                "id": f"{TICKER_ID}"
                                            } ,
                                            "attr": "value_input" ,
                                            "new": f"{WANT_TICKER}"
                                        }
                                    ] ,
                                    "references": []
                                }
                                ws_handler.patch_message_sent(ws=ws)
                                ws_handler.general_message_sent(ws=ws , data={})
                                ws_handler.general_message_sent(ws=ws , data=data)

                                # Window 변경
                                data: Dict = {
                                    "events": [
                                        {
                                            "kind": "ModelChanged" ,
                                            "model": {
                                                "id": f"{Window_ID}"
                                            } ,
                                            "attr": "value" ,
                                            "new": f"{WANT_WINDOW}"
                                        }
                                    ] ,
                                    "references": []
                                }
                                ws_handler.patch_message_sent(ws=ws)
                                ws_handler.general_message_sent(ws=ws , data={})
                                ws_handler.general_message_sent(ws=ws , data=data)

                                # 버튼 클릭
                                ws_handler.patch_message_sent(ws=ws)
                                ws_handler.general_message_sent(ws=ws , data={})
                                ws_handler.general_message_sent(ws=ws , data={
                                    "events": [
                                        {
                                            "kind": "MessageSent" ,
                                            "msg_type": "bokeh_event" ,
                                            "msg_data": {
                                                "event_name": "button_click" ,
                                                "event_values": {
                                                    "model": {
                                                        "id": f"{ButtonClick_ID}"
                                                    }
                                                }
                                            }
                                        }
                                    ] ,
                                    "references": []
                                })
                                print("전송 완료했습니다.")
                                TICKER_ID = None
                                Window_ID = None
                                ButtonClick_ID = None
                                return

            elif data.get('events') is not None and len(data['events']) > 0 and data['events'][0].get('attr') == 'children':
                # CHART_DATA = data
                Variable_Data = {}
                for reference in data['references']:
                    if reference['attributes'].get('data') is not None:
                        chart_data: Dict[str , Union[Dict , List]] = reference['attributes']['data']
                        if chart_data.get('Variable') is None:
                            continue

                        Variable: List[str] = chart_data['Variable']

                        # 사용자가 원하는 그래프 라인일 경우에만 뽑아낸다.
                        TickName: str = Variable[0]
                        if TickName in GRAPH_COLOR and GRAPH_COLOR[TickName] in WANT_COLOR:
                            date: Dict = chart_data['date']
                            value: Dict = chart_data['value']

                            price = decode_NDArray(obj=value)
                            date = decode_NDArray(obj=date)

                            i = WANT_COLOR.index(GRAPH_COLOR[TickName])
                            if Variable_Data.get(WANT_COLOR[i]) is None:
                                Variable_Data[WANT_COLOR[i]] = []

                            for (_tick_time , _tick_price) in zip(date , price):
                                # 시간 데이터를 저장하기 위해선 아래 3줄의 코드를 주석 해제 하시고 사용하시면 됩니다.
                                # dt = datetime.fromtimestamp(int(_tick_time) / 1000)
                                # formatted_date = dt.strftime("%Y-%m-%dT%H:%M:%S")
                                # Variable_Data[WANT_COLOR[i]].append((formatted_date , _tick_price))

                                Variable_Data[WANT_COLOR[i]].append(_tick_price , )

                if len(Variable_Data) > 0:
                    print(f"데이터 수신완료 / {json.dumps(Variable_Data)}")
                    MessageHandler.chart_data = Variable_Data
                    ws.close()

        else:
            log.info(msg=f"on_message에 들어온 데이터가 없습니다.")

    def on_error(self , ws: websocket.WebSocketApp , error):
        log.error(msg=f'on_error({error})')

    def on_close(self , ws: websocket.WebSocketApp , close_status_code , close_msg):
        log.info(msg=f'on_close({close_status_code}, {close_msg})')

    def on_open(self , ws: websocket.WebSocketApp):
        log.info(msg=f'정상적으로 웹소켓 서버에 접근했습니다. {ws.header}')
        print("정상적으로 데이터를 전송했습니다.")

    def parse_message(self , data: str = None):
        if data is not None and isinstance(data , str):
            return json.loads(data)
        return None

    def patch_message_sent(self , ws: websocket.WebSocketApp):
        data = {
            "msgid": self.generate_msgid() ,
            "msgtype": "PATCH-DOC"
        }
        log.info(msg=f"{data}를 전송합니다")
        ws.send(data=json.dumps(data))

    def general_message_sent(self , ws: websocket.WebSocketApp , data: Dict):
        ws.send(data=json.dumps(data))


ws_handler: WebsocketHandler = WebsocketHandler()


def run_chart_websocket():
    charts: Charts = Charts()

    if charts.get_bokeh_token():
        log.info(msg=f"bokeh 세션을 가져왔습니다.")

        headers: Dict[str , str] = {
            "Pragma": "no-cache" ,
            "Cache-Control": "no-cache" ,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36" ,
            "Accept-Encoding": "gzip, deflate, br" ,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7" ,
            "Connection": "Upgrade" ,
            "Upgrade": "websocket" ,
            "Sec-WebSocket-Version": "13" ,
            "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits" ,
            "Sec-WebSocket-Key": ws_handler.generate_websocket_key() ,
            "Sec-WebSocket-Protocol": f"bokeh, {charts.getBokehSession}" ,
            "Cookie": 'user="\"Min_Soo_Lee\""'
        }

        ws = websocket.WebSocketApp(
            f"wss://app.materialindicators.com/FireCharts/ws" ,
            on_open=ws_handler.on_open ,
            on_message=ws_handler.on_message ,
            on_error=ws_handler.on_error ,
            on_close=ws_handler.on_close ,
            header=headers ,
        )
        ws.run_forever(ping_interval=20 , ping_timeout=10 , origin="https://app.materialindicators.com")

    else:
        log.error(msg=f"bokehSession을 가져오는데 실패하였습니다.")
