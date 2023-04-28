import json
import boto3
import openai
import os

on_response = False

def lambda_handler(event, context):
    # OpenAI APIキーを環境変数から取得
    openai.api_key = os.environ["OPENAI_API_KEY"]

    # 入力メッセージおよびconnection識別のための情報を取得
    data_str = json.loads(event.get('body', '{}')).get('data')
    data = json.loads(data_str)
    number_of_paragraphs = data.get('number_of_paragraphs')
    text_range_minimum = data.get('text_range_minimum')
    text_range_maximum = data.get('text_range_maximum')
    instruction = data.get('instruction')
    msg = "According to the format above, Describe topic `{}` in {} paragraphs with a total of {}-{} characters.".format(instruction,number_of_paragraphs, text_range_minimum, text_range_maximum)
    final_msg = "answer in japanese.don't miss end of input `|`"
    domain_name = event.get('requestContext', {}).get('domainName')
    stage = event.get('requestContext', {}).get('stage')
    connectionId = event.get('requestContext', {}).get('connectionId')
    apigw_management = boto3.client(
        'apigatewaymanagementapi', endpoint_url=F"https://{domain_name}/{stage}")

    # Request ChatGPT API
    with open('instructor.txt', 'r') as f:
        assist_msg = f.read()
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You will strictly follow the instructions below and respond in the prescribed format,and write a paragraph and an argument."},
            {"role": "assistant", "content": assist_msg},
            {"role": "user", "content": msg},
            {"role": "user", "content": final_msg},
        ],
        stream=True
    )
        # メッセージ送信元クライアントに逐次メッセージ送信
    # グローバルでやる
    def change_state():
        global on_response
        on_response = on_response ^ True

    for partial_message in response:
        content = partial_message['choices'][0]['delta'].get('content')
        if content:
            if "|" in content:
                if on_response:
                    apigw_management.post_to_connection(
                        ConnectionId=connectionId, Data="|")
                    apigw_management.delete_connection(ConnectionId=connectionId)
                else:
                    change_state()

            try:
                if on_response:
                    apigw_management.post_to_connection(
                        ConnectionId=connectionId, Data=content)
            except Exception as  e:
                raise e
    try:
        apigw_management.delete_connection(ConnectionId=connectionId)
    except Exception as  e:
        raise e
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "data sent.",
        }),
    }
